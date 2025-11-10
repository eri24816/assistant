from typing import Callable, Dict, Any, Tuple, List, Literal
import inspect
import re
import math
from datetime import datetime
from typing import get_type_hints, get_origin, get_args, Union


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
        "name": func_name,
        "description": description or f"Function: {func_name}",
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required
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

# Generate tools for OpenAI using generate_spec_from_function
tool_list = [
    get_weather, 
    calculate, 
    get_current_time, 
    search_web, 
    create_todo,
    list_todos
]

tools = {func.__name__: func for func in tool_list}

tool_specs = [generate_spec_from_function(func) for func in tool_list]