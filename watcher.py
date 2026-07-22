import time
import os
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Import core pipeline configurations and logic
try:
    from pipeline import run_ingestion_pipeline, SOURCE_DIR
except ImportError as e:
    print(f"[ERROR] Failed to import pipeline logic. Ensure pipeline.py is in the same directory. Context: {e}")
    sys.exit(1)

class DocumentHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.last_triggered = 0.0
        self.debounce_seconds = 2.0  # Time window to filter rapid duplicate events

    def trigger_pipeline(self, event_path):
        # Only process PDF files
        if not event_path.endswith('.pdf'):
            return

        # Simple debounce to prevent duplicate processing for concurrent events
        now = time.time()
        if now - self.last_triggered < self.debounce_seconds:
            return
        self.last_triggered = now

        print(f"\n[WATCHER] New file event detected: {os.path.basename(event_path)}")
        print("[WATCHER] Waiting 1.5 seconds to ensure file write operations complete...")
        time.sleep(1.5)

        # Double check that the file still exists in the source directory before running
        if os.path.exists(event_path):
            try:
                run_ingestion_pipeline()
            except Exception as e:
                print(f"[WATCHER ERROR] Pipeline execution failed. Context: {e}")
        else:
            print(f"[WATCHER WARNING] File {os.path.basename(event_path)} was removed or renamed before processing.")

    def on_created(self, event):
        if not event.is_directory:
            self.trigger_pipeline(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            # We track moves specifically if files are moved into the source directory
            self.trigger_pipeline(event.dest_path)

def start_watcher():
    if not os.path.exists(SOURCE_DIR):
        print(f"[WATCHER ERROR] Monitored source directory '{SOURCE_DIR}' does not exist. Creating it...")
        os.makedirs(SOURCE_DIR, exist_ok=True)

    event_handler = DocumentHandler()
    observer = Observer()
    observer.schedule(event_handler, path=SOURCE_DIR, recursive=False)
    observer.start()
    
    print("=" * 60)
    print(f"BACKGROUND DAEMON: Monitoring '{SOURCE_DIR}' for incoming PDFs.")
    print("Press Ctrl+C to terminate the daemon safely.")
    print("=" * 60)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[WATCHER] Shutdown signal received. Terminating observer...")
        observer.stop()
    except Exception as e:
        print(f"\n[WATCHER ERROR] Daemon encountered an exception: {e}")
        observer.stop()
    observer.join()
    print("[WATCHER] Daemon stopped cleanly.")

if __name__ == "__main__":
    start_watcher()
