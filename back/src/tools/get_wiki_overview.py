import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
def get_wiki_overview():
    """Get an overview of the wiki.
    
    Returns:
        An overview of the wiki as a string
    """
    base_path = os.environ.get('WIKI_PATH')
    if not base_path:
        raise ValueError('WIKI_PATH environment variable is not set')

    def walk(path: str, depth_remaining: int, max_files: list[int], max_dirs: list[int]):
        path = str(Path(path))
        if depth_remaining == 0:
            return
        self_max_files = max_files[0]
        self_max_dirs = max_dirs[0]
        dirs = []
        files = []
        too_much_dirs = False
        too_much_files = False
        for item in os.listdir(path):
            if os.path.isfile(os.path.join(path, item)):
                if len(files) < self_max_files:
                    files.append(item)
                else:
                    too_much_files = True
            elif os.path.isdir(os.path.join(path, item)):
                if len(dirs) < self_max_dirs:
                    dirs.append([item+'/', walk(os.path.join(path, item), depth_remaining - 1, max_files[1:], max_dirs[1:])])
                else:
                    too_much_dirs = True
        result = []
        for file in files:
            result.append(file)
        if too_much_files:
            result.append('... more files')
        for dir in dirs:
            result.append(dir)
        if too_much_dirs:
            result.append('... more directories')
        return result
    return walk(base_path, 2, [10, 2], [10, 2])

print(get_wiki_overview())