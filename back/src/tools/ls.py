import os
from typing import List, Dict

def ls(path: str) -> Dict[str, List[str]]:
    """List the contents of a directory.
    
    Args:
        path: The path to the directory to list
    
    Returns:
        A dictionary with the contents of the directory
        "files": list of files in the directory
        "directories": list of directories in the directory
    """
    return {
        "files": os.listdir(path),
        "directories": [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
    }