from typing import NotRequired, Any
from typing_extensions import TypedDict

class Thread(TypedDict):
    """
    Represents a chat thread
    """
    
    id: str
    title: str
    created_at: str
    state: NotRequired[Any]  # This will store the agent's state
