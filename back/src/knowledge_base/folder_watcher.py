
import json
from pathlib import Path
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import fnmatch
def file_hash(path: Path) -> str:
    """Small fast hash (mtime + size). Extend if you want stronger hash."""
    st = path.stat()
    return f"{st.st_mtime_ns}-{st.st_size}"


def fnmatch_any(path: str, patterns: list[str]) -> bool:
    return bool(any(fnmatch.fnmatch(path, pattern) for pattern in patterns))


def scan_folder(folder: Path, ignore_patterns: list[str] = []):
    """Return mapping path -> hash."""
    data: dict[str, str] = {}
    for f in folder.rglob("*"):
        if not f.is_file():
            continue
        if fnmatch_any(str(f), ignore_patterns):
            continue
        data[f.relative_to(folder).as_posix()] = file_hash(f)
    return data
    

class FolderWatcher:
    '''
    Watch a folder and call callbacks when files are added, removed, or renamed.
    When it starts, it also detect changes in the folder since last time it was run.
    '''
    def __init__(self, target_folder: Path, snapshot_path: Path, ignore_patterns: list[str] = []):
        self.target_folder = target_folder
        self.snapshot_path = snapshot_path
        self.ignore_patterns = ignore_patterns

        ignore_patterns.append(str(snapshot_path))
        
        self.on_add = None
        self.on_remove = None
        self.on_rename = None

        self.observer = None
        self.last_snapshot: dict[str, str] = {} # path -> hash

    # ---------------------------
    # Handler registration
    # ---------------------------

    def set_handlers(self, on_add=None, on_remove=None, on_rename=None):
        self.on_add = on_add
        self.on_remove = on_remove
        self.on_rename = on_rename

    # ---------------------------
    # Snapshot load/save
    # ---------------------------

    def load_snapshot(self):
        try:
            return json.loads(self.snapshot_path.read_text())
        except FileNotFoundError:
            return {}

    def save_snapshot(self, snap: dict[str, str]):
        self.snapshot_path.write_text(json.dumps(snap))

    # ---------------------------
    # Initial diff
    # ---------------------------

    def _get_relative_path(self, path: str) -> str:
        return Path(path).relative_to(self.target_folder).as_posix()

    def _initial_diff(self):
        old = self.last_snapshot
        new = scan_folder(self.target_folder, self.ignore_patterns)

        old_paths = set(old.keys())
        new_paths = set(new.keys())

        added = new_paths - old_paths
        removed = old_paths - new_paths
        

        # To grarantee no skipping files if this program is stopped abruptly, we need to save a snapshot here
        snap_keys = list(old_paths - removed)
        snap_values = [old[k] for k in snap_keys]
        self.save_snapshot(dict(zip(snap_keys, snap_values)))

        # Fire callbacks
        for p in added:
            if self.on_add:
                self.on_add(p)

        for p in removed:
            if self.on_remove:
                self.on_remove(p)

        # Save new snapshot
        self.last_snapshot = new
        self.save_snapshot(new)

    # ---------------------------
    # Watchdog runtime
    # ---------------------------

    def _build_watchdog_handler(self):
        outer = self

        class Handler(FileSystemEventHandler):
            # def on_any_event(self, event) -> None:
            #     print(f"Event: {event.event_type} {event.src_path} {event.dest_path}")
            #     return super().on_any_event(event)
            def on_created(self, event):
                assert isinstance(event.src_path, str)
                src = outer._get_relative_path(event.src_path)
                if event.is_directory:
                    return
                if fnmatch_any(event.src_path, outer.ignore_patterns):
                    return
                outer.on_add(src)
                outer._add_to_snapshot(src)

            def on_deleted(self, event):
                assert isinstance(event.src_path, str)
                src = outer._get_relative_path(event.src_path)
                if event.is_directory:
                    return
                if fnmatch_any(event.src_path, outer.ignore_patterns):
                    return
                outer._remove_from_snapshot(src)
                outer.on_remove(src)

            def on_moved(self, event):
                assert isinstance(event.src_path, str)
                assert isinstance(event.dest_path, str)
                src = outer._get_relative_path(event.src_path)
                dest = outer._get_relative_path(event.dest_path)
                if event.is_directory:
                    return
                src_ignored = fnmatch_any(event.src_path, outer.ignore_patterns)
                dest_ignored = fnmatch_any(event.dest_path, outer.ignore_patterns)
                if src_ignored and dest_ignored:
                    return
                if src_ignored:
                    outer._remove_from_snapshot(src)
                    outer.on_remove(src)
                if dest_ignored:
                    outer.on_add(dest)
                    outer._add_to_snapshot(dest)
                    
                outer._remove_from_snapshot(src)
                outer.on_rename(src, dest)
                outer._add_to_snapshot(dest)

            def on_modified(self, event):
                assert isinstance(event.src_path, str)
                src = outer._get_relative_path(event.src_path)
                if event.is_directory:
                    return
                if fnmatch_any(event.src_path, outer.ignore_patterns):
                    return

                old_hash = outer.last_snapshot[src]
                new_hash = file_hash(outer.target_folder / src)
                if old_hash == new_hash:
                    print(f"File {src} has not changed")
                    return
                outer._remove_from_snapshot(src)
                outer.on_remove(src)
                outer.on_add(src)
                outer._add_to_snapshot(src)

        return Handler()

    # Update snapshot entries
    def _add_to_snapshot(self, path: str):
        self.last_snapshot[path] = file_hash(self.target_folder / path)
        self.save_snapshot(self.last_snapshot)


    def _remove_from_snapshot(self, path: str):
        del self.last_snapshot[path]
        self.save_snapshot(self.last_snapshot)

    # ---------------------------
    # Start/Stop
    # ---------------------------

    def start(self):
        # load snapshot
        self.last_snapshot = self.load_snapshot()

        # 1. Initial diff
        self._initial_diff()

        # 2. Start watchdog
        handler = self._build_watchdog_handler()
        self.observer = Observer()
        self.observer.schedule(handler, str(self.target_folder), recursive=True)
        self.observer.start()

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()

if __name__ == "__main__":

    def add(p):
        print("ADD:", p)

    def remove(p):
        print("REMOVE:", p)

    def rename(old, new):
        print("RENAME:", old, "→", new)

    w = FolderWatcher(Path("./documents"), Path("./snapshot.json"))
    w.set_handlers(on_add=add, on_remove=remove, on_rename=rename)
    w.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        w.stop()
