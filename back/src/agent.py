import importlib
import os
import json
import traceback
from typing import AsyncIterator, Iterable, cast, TypeVar
from openai import OpenAI
from dotenv import load_dotenv
from knowledge_base.docs_indexer import DocsIndexer
from tools.ls import ls
from tools.util import generate_spec_from_function
from util import notNone
import tools
from prompts import system_prompt
import queue
import threading
import asyncio
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputItemDoneEvent, ResponseOutputMessage, ResponseTextDeltaEvent, ResponseFunctionCallArgumentsDeltaEvent, ResponseOutputItemAddedEvent
from openai.types.responses import ToolParam
from pathlib import Path


T = TypeVar('T')
async def async_generator(generator: Iterable[T]) -> AsyncIterator[T]:
    '''
    Convert a blocking iterable to an asynchronous iterable.
    '''
    q = queue.Queue()
    def enqueue():
        next_item_event = asyncio.Event()
        q.put(next_item_event)
        for i in generator:
            next_item_event.set()
            next_item_event = asyncio.Event()
            q.put(i)
            q.put(next_item_event)
        next_item_event.set()
        q.put(StopIteration)
    thr = threading.Thread(target=enqueue, daemon=True)
    thr.start()
    while True:
        next_item_event: asyncio.Event = q.get()
        await next_item_event.wait()
        item = q.get()
        if item is StopIteration:
            break
        yield item

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

working_dir = notNone(os.getenv("WORKING_DIR"))

docs_indexer = DocsIndexer(Path(working_dir), check_interval=60*5)
def search_from_memory(query: str) -> str:
    """Search for information in the memory"""
    search_results = docs_indexer.search_from_vector_db(query, n_results=5)
    result = ''
    assert search_results["documents"] is not None
    assert search_results["metadatas"] is not None
    for doc, metadata in zip(search_results["documents"][0], search_results["metadatas"][0]):
        result += f"File: {metadata['source_id']} (chunk {metadata['chunk_id']})\n"
        result += f"Content: {doc}\n\n"
    return result

def memorize(title: str, content: str) -> str:
    """Memorize information. You can later search for it using search_from_memory tool."""
    path = Path(working_dir) / "memory" / f"{title}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    docs_indexer.check()
    return f"Information {title} memorized at memory/{title}.md"

def reload_tools():
    'Reload tools. This will load the tools that are available to the model. Use this after you add or modify tool code'
    importlib.reload(tools)
    load_tools()

tool_specs = []

def load_tools():
    global tool_specs
    tools.tools['search_from_memory'] = search_from_memory
    tools.tools['memorize'] = memorize

    tools.tools['reload_tools'] = reload_tools
    
    tool_specs = [generate_spec_from_function(func) for func in tools.tools.values()]

    print(list(tools.tools.keys()))

load_tools()

class Agent:
    def __init__(self):
        self.state = {
            "messages": []
        }
        self.state["messages"].append({"role": "system", "content": system_prompt})

    async def handle_user_message(self, message: str) -> AsyncIterator[dict]:
        """Handle a human message and stream responses with tool calling."""
        # Add user message
        self.state["messages"].append({"role": "user", "content": message})
        while True:
            should_exit = True
            async for response in self.use_model():
                yield response
                if response['type'] == 'tool_call':
                    should_exit = False
            if should_exit:
                print("Exiting")
                break

    async def use_model(self):
        print('Using model')

        # context is only for this call and is not saved in the state
        context = [
            {"role": "system", "content": f"The current working directory is {os.getcwd()}. The contents of the directory are: {ls()}"},
        ]


        stream = client.responses.create(
            model="gpt-4o-mini",
            input=self.state["messages"] + context, # context must follow the state messages so the cache can hit
            tools=cast(Iterable[ToolParam], tool_specs),
            stream=True,
        )

        async for e in async_generator(stream):

            if isinstance(e, ResponseTextDeltaEvent):
                yield {"type": "ai", "content": e.delta}
            elif isinstance(e, ResponseFunctionCallArgumentsDeltaEvent):
                yield {"type": "tool_call_delta", "content": e.delta}
            elif isinstance(e, ResponseOutputItemAddedEvent):
                if e.item.type == 'function_call':
                    yield {"type": "tool_call", "name": e.item.name, "args": e.item.arguments}
            elif isinstance(e, ResponseOutputItemDoneEvent):

                if isinstance(e.item, ResponseOutputMessage):
                    last_message = e.item.to_dict()
                    self.state["messages"].append(last_message)
                
                if isinstance(e.item, ResponseFunctionToolCall):
                    try:
                        tool_result = self._call_tool(e.item.name, json.loads(e.item.arguments))
                        tool_result_str = json.dumps(tool_result)
                    except Exception:
                        tool_result_str = traceback.format_exc()
                    yield {"type": "tool_result", "content": tool_result_str}

                    self.state["messages"].append(e.item.to_dict())

                    self.state["messages"].append({
                        'type': 'function_call_output',
                        'call_id': e.item.call_id,
                        'output': tool_result_str
                    })


    def get_state(self) -> dict:
        return self.state

    def set_state(self, state: dict):
        self.state = state

    def _call_tool(self, tool_name: str, args: dict) -> dict:
        print(f"Calling tool {tool_name} with args {args}")
        return tools.tools[tool_name](**args)
