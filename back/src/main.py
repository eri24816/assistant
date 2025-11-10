import datetime
import json
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, TypeVar, Generic, List
from agent import Agent
import uuid

from abstraction import Thread
from pathlib import Path
from typing import Iterator

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    content: str

T = TypeVar('T', bound=Thread)
class DiskStore(Generic[T]):
    '''
    Dict-like store that stores data on disk and provides a index of the data.
    _index.json
    key1.json
    key2.json
    ...
    '''
    def __init__(self, path: Path, index_fields: List[str]):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        self.index_file = self.path / "_index.json"
        if not self.index_file.exists():
            self.index_file.write_text(json.dumps({}))
            self.index = {}
        else:
            self.index = json.loads(self.index_file.read_text())
        self.index_fields = index_fields

    def __getitem__(self, key: str) -> T:
        with open(self.path / f"{key}.json", "r") as f:
            return json.load(f)

    def __setitem__(self, key: str, value: T):
        with open(self.path / f"{key}.json", "w") as f:
            json.dump(value, f)

        # save index to index file
        index_fields = {}
        for field in self.index_fields:
            index_fields[field] = value[field]
        self.index[key] = index_fields
        self.index_file.write_text(json.dumps(self.index))

    def __delitem__(self, key: str):
        if key not in self.index:
            raise KeyError(f"Key {key} not found in store")
        (self.path / f"{key}.json").unlink()
        del self.index[key]
        self.index_file.write_text(json.dumps(self.index))


    def __iter__(self) -> Iterator[str]:
        return iter(self.index.keys())
        
    def __len__(self) -> int:
        return len(self.index)

    def __contains__(self, key: str) -> bool:
        return key in self.index

        
        
# Store active threads and their agents
threads_store = DiskStore[Thread](Path("data/threads"), index_fields=['id','title','created_at'])

agents: Dict[str, Agent] = {}

@app.get("/api/chat/threads/")
async def get_threads() -> Dict[str, Thread]:
    return threads_store.index

@app.post("/api/chat/threads/")
async def create_thread() -> Thread:
    '''
    Create a new thread
    '''
    thread_id = str(uuid.uuid4())
    thread = Thread(
        id=thread_id,
        title="New Chat",
        created_at=datetime.datetime.now().isoformat(),
    )
    threads_store[thread_id] = thread
    
    return thread

@app.get("/api/chat/thread/{thread_id}/")
async def get_thread(thread_id: str):
    '''
    Get the info of a thread
    '''
    if thread_id not in threads_store:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    thread_data = threads_store[thread_id]
    
    return thread_data

@app.post("/api/chat/thread/{thread_id}/")
async def chat(thread_id: str, message: Message):
    '''
    Send a message to the thread. Will be handled by the agent of the thread.
    '''
    if thread_id not in threads_store:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    agent = agents.get(thread_id)
    if not agent:
        # Create agent if it doesn't exist
        agent = Agent()
        thread_info = threads_store[thread_id]
        if 'state' in thread_info:
            agent.set_state(thread_info['state'])
        agents[thread_id] = agent
    
    try:
        response_stream = agent.handle_user_message(message.content)
        async def stream_response():
            async for response in response_stream:
                
                yield json.dumps(response) + '\n'

            print('streaming done')
            thread_state = agent.get_state()
            thread = threads_store[thread_id]
            thread['state'] = thread_state
            threads_store[thread_id] = thread

        return StreamingResponse(stream_response(), media_type="text/event-stream")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/chat/thread/{thread_id}")
async def delete_thread(thread_id: str):
    '''
    Delete a thread and its associated data
    '''
    if thread_id not in threads_store:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Delete the thread
    del threads_store[thread_id]
    
    # Remove the agent if it exists
    if thread_id in agents:
        del agents[thread_id]
    
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
