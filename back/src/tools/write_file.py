def write_file(file_path: str, content: str) -> None:
    """Write to a file.
    
    Args:
        file_path: The path to the file to write to
        content: The content to write to the file
    """
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)