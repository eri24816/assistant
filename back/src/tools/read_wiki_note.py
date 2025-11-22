import os

def read_wiki_note(relative_path):
    """Read a note from wiki.
    
    Args:
        relative_path: The relative path to the note, including the file name
    
    Returns:
        The content of the note as a string
    """
    # Define the base wiki path
    base_path = os.environ.get('WIKI_PATH')
    if not base_path:
        raise ValueError('WIKI_PATH environment variable is not set')
    full_path = os.path.join(base_path, relative_path)

    with open(full_path, 'r', encoding='utf-8') as file:
        content = file.read()
        if len(content) > 1000:
            content = content[:1000] + "... (truncated)"