import os


def cd(new_path):
    os.chdir(new_path)
    return os.getcwd()
