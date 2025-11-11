def read_file(file_path: str) -> str:
    """Read a file and return the content.
    
    Args:
        file_path: The path to the file to read
    
    Returns:
        The content of the file as a string
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()