
import math


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
        return result
    except Exception as e:
        return f"Error calculating {expression}: {str(e)}"  