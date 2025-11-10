import os
import json
from typing import AsyncIterator, Any, Iterable, cast, TypeVar
from openai import OpenAI
from dotenv import load_dotenv
from tools import tool_specs, tools
import queue
import threading
import asyncio
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputItemDoneEvent, ResponseOutputMessage, ResponseTextDeltaEvent, ResponseFunctionCallArgumentsDeltaEvent, ResponseOutputItemAddedEvent

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
    

class Agent:
    def __init__(self):
        self.state = {"messages": []}

    async def handle_user_message(self, message: str) -> AsyncIterator[dict]:
        """Handle a human message and stream responses with tool calling."""
        # Add user message
        self.state["messages"].append({"role": "user", "content": message})
        
        # Make initial API call
        # Cast tools to Any to avoid type checking issues with the OpenAI SDK
        stream = client.responses.create(
            model="gpt-4o",
            input=self.state["messages"],
            tools=cast(Any, tool_specs),
            stream=True
        )

# {'arguments': '{"sign":"Aquarius"}', 'call_id': 'call_AC38r1u1go6D5daXgjgWkEvi', 'name': 'get_horoscope', 'type': 'function_call', 'id': 'fc_0a839bcb432ca735006911c8df2c0481968b86df7c8bda3394', 'status': 'completed'}, {'type': 'function_call_output', 'call_id': 'call_AC38r1u1go6D5daXgjgWkEvi', 'output': '{"horoscope": "{\'sign\': \'Aquarius\'}: Next Tuesday you will befriend a baby otter."}'}
        async for e in async_generator(stream):

            if isinstance(e, ResponseTextDeltaEvent):
                yield {"type": "ai", "content": e.delta}
            elif isinstance(e, ResponseFunctionCallArgumentsDeltaEvent):
                yield {"type": "tool_call_delta", "content": e.delta}
            elif isinstance(e, ResponseOutputItemAddedEvent):
                if e.type == 'function_call':
                    yield {"type": "tool_call", "name": e.function_call.name, "args": e.function_call.arguments}
            elif isinstance(e, ResponseOutputItemDoneEvent):

                if isinstance(e.item, ResponseOutputMessage):
                    last_message = e.item.to_dict()
                    self.state["messages"].append(last_message)
                    print(last_message)
                    print('-' * 50)
                
                if isinstance(e.item, ResponseFunctionToolCall):
                    tool_result = tools[e.item.name](**json.loads(e.item.arguments))
                    tool_result_str = json.dumps(tool_result)
                    yield {"type": "tool_result", "content": tool_result_str}

                    self.state["messages"].append(e.item.to_dict())

                    self.state["messages"].append({
                        'type': 'function_call_output',
                        'call_id': e.item.call_id,
                        'output': tool_result_str
                    })

            print(self.state["messages"])
            print('-' * 50)




    def get_state(self) -> dict:
        return self.state

    def set_state(self, state: dict):
        self.state = state
