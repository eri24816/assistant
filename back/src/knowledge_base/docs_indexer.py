from pathlib import Path
import chromadb
from openai import OpenAI
import random
from folder_watcher import FolderWatcher
def split_text(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

class DocsIndexer:
    def __init__(self, document_root: Path, persist_directory: Path|None = None, embedding_model: str = "text-embedding-3-small"):

        if persist_directory is None:
            persist_directory = document_root / "_index"

        chroma_persist_directory = persist_directory / "chroma"
        document_snapshot_path = persist_directory / "document_snapshot.json"
        chroma_persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.document_root = document_root

        self.embedding_model = embedding_model
        self.openai_client = OpenAI()
        self.client = chromadb.PersistentClient(path=str(chroma_persist_directory))
        self.collection = self.client.get_or_create_collection("knowledge_base")

        self.folder_watcher = FolderWatcher(document_root, document_snapshot_path, ignore_patterns=[str(persist_directory / "**")])

        self.folder_watcher.set_handlers(on_add=self._on_add, on_remove=self._on_remove, on_rename=self._on_rename)
        self.folder_watcher.start()

    def _on_add(self, path: str):
        # Convert absolute path to a relative path before passing to _add_to_vector_db
        print(f"Adding {path}")
        self._add_to_vector_db(path)

    def _on_remove(self, path: str):
        print(f"Removing {path}")
        self._remove_from_vector_db(path)

    def _on_rename(self, old: str, new: str):
        print(f"Renaming {old} to {new}")
        self._rename_in_vector_db(old, new)


    def _read(self, path: str) -> str:
        abs_path = self.document_root / path
        if not abs_path.exists():
            raise FileNotFoundError(f"File {abs_path} not found")
        with open(abs_path, "r", encoding="utf-8") as file:
            return file.read()

    def _add_to_vector_db(self, id: str):
        self._remove_from_vector_db(id)
        content = self._read(id)
        if content == "":
            return
        chunks = split_text(content)
        embedding = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=chunks
        )
        self.collection.add(
            documents=chunks,
            embeddings= [e.embedding for e in embedding.data],
            ids=[f"{id}_{i}_{random.randint(0, 100000000)}" for i in range(len(chunks))],
            metadatas=[{"source_id": id, "chunk_id": i} for i in range(len(chunks))]
        )

    
    def search_from_vector_db(self, query: str, n_results: int = 10, source_id: str | None = None):
        embedding = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=query
        )
        where: chromadb.Where | None = {"source_id": source_id} if source_id else None
        results = self.collection.query(query_embeddings=[embedding.data[0].embedding], n_results=n_results, where=where)
        return results
    
    def _remove_from_vector_db(self, source_id: str):
        self.collection.delete(where={"source_id": source_id})

    def _rename_in_vector_db(self, old_id: str, new_id: str):
        # Query to get all document IDs with the old source_id
        results = self.collection.get(where={"source_id": old_id})
        
        if not results["ids"]:
            return
        # Update all documents with the new source_id
        old_metadatas = results.get("metadatas")
        assert old_metadatas is not None
        new_metadatas = []
        for metadata in old_metadatas:
            new_metadata = {key: value for key, value in metadata.items()}
            new_metadata["source_id"] = new_id
            old_chunk_id = metadata.get('chunk_id')
            assert old_chunk_id is not None
            new_metadatas.append(new_metadata)
        self.collection.update(
            ids=results["ids"],
            metadatas=new_metadatas
        )
        print("old metadata: ", old_metadatas)
        print("new metadata: ", new_metadatas)

if __name__ == "__main__":
    import sys
    indexer = DocsIndexer(Path(sys.argv[1]))
    try:
        while True:
            query = input("\nEnter search query (or type 'exit' to quit): ").strip()
            if query.lower() in ("exit", "quit"):
                break
            n_results = 5
            results = indexer.search_from_vector_db(query, n_results=n_results)
            print("Top results:")
            for i, (doc, metadata, score) in enumerate(zip(results["documents"][0], results["metadatas"][0], results["distances"][0])):
                print(f"\nResult {i+1}:")
                print(f"Score: {score:.4f}")
                print(f"Metadata: {metadata}")
                print(f"Content: {doc}")
    except KeyboardInterrupt:
        indexer.folder_watcher.stop()