import importlib
import os
import json
import traceback
from typing import AsyncIterator, Iterable, cast, TypeVar
from openai import OpenAI
from dotenv import load_dotenv
import tools
from prompts import system_prompt
import queue
import threading
import asyncio
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputItemDoneEvent, ResponseOutputMessage, ResponseTextDeltaEvent, ResponseFunctionCallArgumentsDeltaEvent, ResponseOutputItemAddedEvent
from openai.types.responses import ToolParam
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

def load_tools():
    tools.tool_specs.append(
        {
            "type": "function",
            "name": "reload_tools",
            "description": "Reload tools. This will load the tools that are available to the model. Use this after you add or modify tool code",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    )
    
    def reload_tools():
        importlib.reload(tools)
        load_tools()

    tools.tools['reload_tools'] = reload_tools

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
        stream = client.responses.create(
            model="gpt-4o-mini",
            input=self.state["messages"],
            tools=cast(Iterable[ToolParam], tools.tool_specs),
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
