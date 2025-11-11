import os
import datetime

def add_note(relative_path, name, content):
    # Define the base wiki path
    base_path = os.environ.get('WIKI_PATH')
    if not base_path:
        raise ValueError('WIKI_PATH environment variable is not set')
    # Create the full path for the note
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    file_name = f'{date_str}-{name}.md'
    full_path = os.path.join(base_path, relative_path, file_name)
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    # Write the content to the file
    with open(full_path, 'w', encoding='utf-8') as file:
        file.write(content)
