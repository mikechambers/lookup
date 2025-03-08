import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

folder_to_watch = "/Users/mesh/tmp/lookup"
allowed_extensions = ["png", "jpg"]

def main():
    event_handler = FileSystemEventHandler()
    event_handler.on_created = on_created  # Assign our custom on_created function
    observer = Observer()
    observer.schedule(event_handler, folder_to_watch, recursive=False)
    observer.start()

    print(f"Watching folder: {folder_to_watch} for new PNGs ...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def on_created(event):
    if not event.is_directory:
        # Check if file ends with .png
        if any(event.src_path.lower().endswith(ext) for ext in allowed_extensions):
            print(f"New JPG detected: {event.src_path}")

if __name__ == "__main__":
    main()