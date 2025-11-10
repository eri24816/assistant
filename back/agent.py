import os
import json
import math
import inspect
import re
from datetime import datetime
from typing import List, Dict, Any, cast, get_type_hints, get_origin, get_args, Union, Callable, Tuple, Literal
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionToolMessageParam,
)

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_spec_from_function(func: Callable) -> Dict[str, Any]:
    """Generate OpenAI tool spec from a function's signature and docstring.
    
    Args:
        func: The function to generate a spec for
    
    Returns:
        A dictionary containing the OpenAI tool specification
    """
    # Get function name
    func_name = func.__name__
    
    # Get function signature
    sig = inspect.signature(func)
    
    # Parse docstring
    docstring = inspect.getdoc(func) or ""
    
    # Extract description from docstring (first line or paragraph)
    description = ""
    if docstring:
        # Get the first paragraph as description
        description = docstring.split("\n\n")[0].strip()
        # Remove Args/Returns sections if they appear in first paragraph
        description = re.split(r"\n\s*(Args|Returns|Parameters):", description)[0].strip()
    
    # Parse parameter descriptions from docstring
    param_descriptions = {}
    if docstring:
        # Look for Args: or Parameters: section
        args_match = re.search(r"(?:Args|Parameters):\s*\n((?:\s+\w+:[^\n]+\n?)+)", docstring, re.MULTILINE)
        if args_match:
            args_text = args_match.group(1)
            # Extract parameter descriptions
            for line in args_text.split("\n"):
                line = line.strip()
                if ":" in line:
                    param_name, param_desc = line.split(":", 1)
                    param_name = param_name.strip()
                    param_desc = param_desc.strip()
                    param_descriptions[param_name] = param_desc
    
    # Get type hints
    type_hints = get_type_hints(func, include_extras=True)
    
    # Build parameters schema
    properties = {}
    required = []
    
    for param_name, param in sig.parameters.items():
        # Skip 'self' and 'cls' parameters
        if param_name in ("self", "cls"):
            continue
        
        # Get parameter type
        param_type = type_hints.get(param_name, str)
        
        # Check if parameter is optional (has default value)
        has_default = param.default != inspect.Parameter.empty
        
        # Convert Python type to JSON schema type
        json_type, enum_values = _python_type_to_json_schema(param_type)
        
        # Build parameter schema
        param_schema: Dict[str, Any] = {
            "type": json_type
        }
        
        # Add description from docstring
        if param_name in param_descriptions:
            param_schema["description"] = param_descriptions[param_name]
        elif has_default:
            # Try to extract description from default value if it's a string
            default_val = param.default
            if isinstance(default_val, str) and default_val:
                param_schema["description"] = f"Defaults to {default_val}."
        
        # Add enum if detected
        if enum_values:
            param_schema["enum"] = enum_values
        
        properties[param_name] = param_schema
        
        # Add to required if no default value
        if not has_default:
            required.append(param_name)
    
    # Build the tool spec
    tool_spec = {
        "type": "function",
        "function": {
            "name": func_name,
            "description": description or f"Function: {func_name}",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    }
    print(tool_spec)
    print("-" * 50)

    return tool_spec


def _python_type_to_json_schema(python_type: Any) -> Tuple[str, List[str] | None]:
    """Convert Python type to JSON schema type and extract enum if present.
    
    Args:
        python_type: The Python type annotation
    
    Returns:
        Tuple of (json_type, enum_values or None)
    """
    # Handle string literals and enum-like types
    if isinstance(python_type, str):
        return "string", None
    
    # Handle Optional/Union types
    origin = get_origin(python_type)
    if origin is Union or origin is type(Union):
        args = get_args(python_type)
        # Check if it's Optional (Union[T, None])
        if len(args) == 2 and type(None) in args:
            non_none_type = next(t for t in args if t is not type(None))
            return _python_type_to_json_schema(non_none_type)
        # For other unions, use the first non-None type
        non_none_types = [t for t in args if t is not type(None)]
        if non_none_types:
            return _python_type_to_json_schema(non_none_types[0])
    
    # Handle Literal types (for enums)
    if origin is Literal:
        args = get_args(python_type)
        if all(isinstance(arg, str) for arg in args):
            return "string", list(args)
        elif all(isinstance(arg, int) for arg in args):
            return "integer", [str(v) for v in args]
    
    # Handle basic types
    type_mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }
    
    # Check direct type match
    if python_type in type_mapping:
        return type_mapping[python_type], None
    
    # Check if it's a class instance
    if inspect.isclass(python_type):
        # Check for enum.Enum
        try:
            import enum
            if issubclass(python_type, enum.Enum):
                enum_values = [e.value for e in python_type]
                # Determine type based on first enum value
                if enum_values and isinstance(enum_values[0], str):
                    return "string", enum_values
                elif enum_values and isinstance(enum_values[0], int):
                    return "integer", [str(v) for v in enum_values]
        except (TypeError, AttributeError):
            pass
        
        # Default to string for unknown classes
        return "string", None
    
    # Default to string
    return "string", None


# Tool/Function definitions
def get_weather(location: str) -> str:
    """Get the current weather for a specific location.
    
    Args:
        location: The city or location name (e.g., "New York", "London")
    
    Returns:
        A string describing the weather conditions
    """
    # Mock implementation - replace with real API in production
    return f"The weather in {location} is sunny, 72°F with light winds."


def calculate(expression: str) -> str:
    """Perform mathematical calculations safely.
    
    Args:
        expression: A mathematical expression as a string (e.g., "15 * 23", "sqrt(16)")
    
    Returns:
        The result of the calculation as a string
    """
    try:
        # Safe evaluation using math functions
        allowed_names = {
            k: v for k, v in math.__dict__.items() if not k.startswith("__")
        }
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"The result of {expression} is {result}"
    except Exception as e:
        return f"Error calculating {expression}: {str(e)}"


def get_current_time() -> str:
    """Get the current date and time.
    
    Returns:
        Current date and time as a string
    """
    return f"Current date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


def search_web(query: str) -> str:
    """Search the web for information.
    
    Args:
        query: The search query string
    
    Returns:
        Search results as a string
    """
    # Mock implementation - replace with real search API in production
    return f"Search results for '{query}': Found relevant information about {query}."


def create_todo(task: str, priority: Literal["low", "medium", "high"] = "medium") -> str:
    """Create a new todo item.
    
    Args:
        task: The task description
        priority: Priority level (low, medium, high). Defaults to medium.
    
    Returns:
        Confirmation message
    """
    global todos
    todos.append({"task": task, "priority": priority})
    return f"Created todo: '{task}' with priority '{priority}'"


# Store todos in memory (in production, use a database)
todos: List[Dict[str, Any]] = []


def list_todos() -> str:
    """List all todo items.
    
    Returns:
        A formatted string listing all todos
    """
    global todos
    if not todos:
        return "No todos found."
    
    result = "Todo List:\n"
    for i, todo in enumerate(todos, 1):
        result += f"{i}. {todo.get('task', 'N/A')} (Priority: {todo.get('priority', 'N/A')})\n"
    return result.strip()


# Map function names to actual functions
function_map = {
    "get_weather": get_weather,
    "calculate": calculate,
    "get_current_time": get_current_time,
    "search_web": search_web,
    "create_todo": create_todo,
    "list_todos": list_todos,
}


# Generate tools for OpenAI using generate_spec_from_function
tools = [
    generate_spec_from_function(get_weather),
    generate_spec_from_function(calculate),
    generate_spec_from_function(get_current_time),
    generate_spec_from_function(search_web),
    generate_spec_from_function(create_todo),
    generate_spec_from_function(list_todos),
]


def run_conversation(user_message: str, messages: List[ChatCompletionMessageParam]) -> tuple[str, List[ChatCompletionMessageParam]]:
    """Run a conversation with tool calling support.
    
    Args:
        user_message: The user's message
        messages: Conversation history
    
    Returns:
        Tuple of (assistant_response, updated_messages)
    """
    # Add user message to history
    messages.append({"role": "user", "content": user_message})
    
    # Make initial API call
    # Cast tools to Any to avoid type checking issues with the OpenAI SDK
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=cast(Any, tools),
        tool_choice="auto"
    )
    
    response_message = response.choices[0].message
    
    # Convert response message to dict format for messages list
    assistant_message_dict: ChatCompletionMessageParam = {
        "role": "assistant",
        "content": response_message.content or "",
    }
    
    # Check if the model wants to call a function
    tool_calls = response_message.tool_calls
    
    if tool_calls:
        # Add tool calls to assistant message
        tool_calls_list = []
        for tool_call in tool_calls:
            # Only process function tool calls
            function_attr = getattr(tool_call, 'function', None)
            if function_attr and hasattr(function_attr, 'name'):
                tool_calls_list.append({
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": getattr(function_attr, 'name', ''),
                        "arguments": getattr(function_attr, 'arguments', '{}'),
                    }
                })
        
        if tool_calls_list:
            assistant_message_dict["tool_calls"] = tool_calls_list
            messages.append(assistant_message_dict)
        
        # Process each tool call
        for tool_call in tool_calls:
            # Runtime check: only process function tool calls
            function_attr = getattr(tool_call, 'function', None)
            if not function_attr or not hasattr(function_attr, 'name'):
                continue
                
            function_name = getattr(function_attr, 'name', '')
            function_args = json.loads(getattr(function_attr, 'arguments', '{}'))
            
            # Call the function
            function_to_call = function_map[function_name]
            function_response = function_to_call(**function_args)
            
            # Add function result to messages
            tool_message: ChatCompletionToolMessageParam = cast(
                ChatCompletionToolMessageParam,
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": function_response
                }
            )
            messages.append(tool_message)
        
        # Get final response from the model
        second_response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
        )
        
        assistant_message = second_response.choices[0].message.content or ""
        messages.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        return assistant_message, messages
    else:
        # No tool calls, return the response directly
        messages.append(assistant_message_dict)
        assistant_message = response_message.content or ""
        return assistant_message, messages


def main():
    """Main CLI loop for the agent."""
    print("🤖 Tool Calling LLM Agent")
    print("=" * 50)
    print("Type 'help' for available commands, 'exit' or 'quit' to end the session")
    print("=" * 50)
    print()
    
    messages: List[ChatCompletionMessageParam] = [
        {
            "role": "system",
            "content": "You are a helpful assistant that can call various tools to help users. "
                      "Use the available tools when appropriate to provide accurate and helpful responses."
        }
    ]
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break
            
            if user_input.lower() == "help":
                print("\nAvailable functions:")
                print("- get_weather: Get weather for a location")
                print("- calculate: Perform mathematical calculations")
                print("- get_current_time: Get current date and time")
                print("- search_web: Search the web")
                print("- create_todo: Create a todo item")
                print("- list_todos: List all todos")
                print("\nYou can ask natural language questions and the agent will use these functions as needed.")
                print()
                continue
            
            print("Agent: ", end="", flush=True)
            response, messages = run_conversation(user_input, messages)
            print(response)
            print()
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {str(e)}")
            print()


if __name__ == "__main__":
    main()

