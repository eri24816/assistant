
from chroma_util import search_chroma

def search_local_document(query: str, from_source: str | None = None):
    '''
    Search local documents using keyword search. Local documents includes wiki notes and 
    
    Args:
        query: The query to search for
        from_source: The source to search from. If None, search from all sources. For example, "wiki:2025-11-11-What is the meaning of life.md"
    
    Returns:
        The content and source of the notes
    '''
    search_results = search_chroma(query, n_results=10, from_source=from_source)
    n_results = len(search_results["documents"][0]) if search_results["documents"] is not None else 0
    documents = search_results["documents"]
    assert documents is not None
    metadatas = search_results["metadatas"]
    assert metadatas is not None
    results = []
    for i in range(n_results):
        content = documents[0][i]
        source = metadatas[0][i]["source"]
        chunk_id = metadatas[0][i]["chunk_id"]
        results.append({
            "content": content,
            "source": source,
            "chunk_id": chunk_id
        })
    return results
