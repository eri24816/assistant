import os


def get_wiki_overview() -> str:
    """Get an overview of the wiki.
    
    Returns:
        An overview of the wiki as a string
    """
    base_path = os.environ.get('WIKI_PATH')
    if not base_path:
        raise ValueError('WIKI_PATH environment variable is not set')
        # INSERT_YOUR_CODE
    overview = []
    for dirpath, dirnames, filenames in os.walk(base_path):
        # Compute the current depth relative to the base path
        rel_path = os.path.relpath(dirpath, base_path)
        depth = 0 if rel_path == '.' else rel_path.count(os.sep) + 1

        # Only consider depth 1 and depth 2 (root and one subdir deep)
        if depth > 2:
            # Don't descend further (avoid >2 depth)
            dirnames[:] = []
            continue

        indent = '  ' * depth
        if depth == 0:
            overview.append(f"{os.path.basename(base_path) or base_path}/")
        else:
            overview.append(f"{indent}{os.path.basename(dirpath)}/")

        # Only show 3 items for 2nd-level content (depth==2)
        if depth == 2:
            shown_files = filenames[:3]
            for fname in shown_files:
                overview.append(f"{indent}  {fname}")
            # If there are more files, show "..."
            if len(filenames) > 3:
                overview.append(f"{indent}  ...")
            # Prevent going deeper
            dirnames[:] = []

    return '\n'.join(overview)