"""File watcher for automatic ingestion pipeline."""

import threading
import time
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from rich.console import Console

console = Console()

SUPPORTED_EXTENSIONS = {
    ".md", ".txt", ".pdf", ".docx", ".html", ".htm", ".json", ".log", ".csv"
}


class IngestHandler(FileSystemEventHandler):
    """Collects file events and debounces them."""

    def __init__(self, debounce: float = 5.0):
        super().__init__()
        self._pending: set[str] = set()
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._debounce = debounce
        self._callback = None

    def set_callback(self, callback):
        self._callback = callback

    def _is_supported(self, path: str) -> bool:
        return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS

    def on_created(self, event):
        if not event.is_directory and self._is_supported(event.src_path):
            self._add(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and self._is_supported(event.src_path):
            self._add(event.src_path)

    def _add(self, path: str):
        with self._lock:
            self._pending.add(path)
            console.print(f"  [dim]Detected: {Path(path).name}[/]")
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce, self._flush)
            self._timer.daemon = True
            self._timer.start()

    def _flush(self):
        with self._lock:
            paths = list(self._pending)
            self._pending.clear()
        if paths and self._callback:
            self._callback(paths)


class FileWatcher:
    """Watches ingest directory and runs pipeline on new files."""

    def __init__(self, config: dict, enrich: bool = False, debounce: float = 5.0):
        self.config = config
        self.enrich = enrich
        self.ingest_path = Path(config["ingest_path"])
        self.handler = IngestHandler(debounce=debounce)
        self.handler.set_callback(self._process_batch)
        self.observer = Observer()

    def _process_batch(self, paths: list[str]):
        """Run pipeline on a batch of detected files."""
        import sys
        import traceback
        try:
            self._process_batch_inner(paths)
        except Exception as e:
            console.print(f"  [red]✗ BATCH CRASHED: {e}[/]")
            console.print(f"  [red]{traceback.format_exc()}[/]")
            sys.stdout.flush()
            sys.stderr.flush()

    def _process_batch_inner(self, paths: list[str]):
        """Actual batch processing logic."""
        from .ingest.processor import process_file
        from .vault.writer import VaultWriter
        from .embeddings.embedder import Embedder
        from .clustering.cluster import run_clustering

        console.print(f"\n[bold blue]Processing {len(paths)} file(s)...[/]")

        # 1. Ingest
        docs = []
        for p in paths:
            try:
                doc = process_file(Path(p), self.config)
                if doc:
                    docs.append(doc)
                    console.print(f"  [green]✓ Ingested: {Path(p).name}[/]")
            except Exception as e:
                console.print(f"  [red]✗ Failed to ingest {Path(p).name}: {e}[/]")

        if not docs:
            console.print("[yellow]No documents to process.[/]")
            return

        # 2. Write to vault
        try:
            writer = VaultWriter(self.config["vault_path"])
            written = writer.write_many(docs)
            console.print(f"  [green]✓ Wrote {len(written)} document(s) to vault[/]")
        except Exception as e:
            console.print(f"  [red]✗ Vault write failed: {e}[/]")
            # Don't return — still try to embed existing vault files

        # 3. Embed
        try:
            from .ingest.processor import process_directory
            import traceback as _tb
            vault_path = Path(self.config["vault_path"])
            console.print("  [dim]Loading vault for embedding...[/]")
            all_docs = process_directory(vault_path, self.config)
            console.print(f"  [dim]Found {len(all_docs)} docs, embedding new chunks...[/]")
            if all_docs:
                embedder = Embedder(self.config)
                count = embedder.embed_documents(all_docs)
                console.print(f"  [green]✓ Embedded {count} new chunk(s)[/]")
            else:
                console.print("  [yellow]No documents found in vault to embed[/]")
        except Exception as e:
            console.print(f"  [red]✗ Embedding failed: {e}[/]")
            console.print(f"  [red]{_tb.format_exc()}[/]")

        # 4. Cluster
        try:
            clusters = run_clustering(self.config)
            if clusters:
                console.print(f"  [green]✓ Found {len(clusters)} cluster(s)[/]")
        except Exception as e:
            console.print(f"  [red]✗ Clustering failed: {e}[/]")
            import traceback as _tb2
            console.print(f"  [red]{_tb2.format_exc()}[/]")

        # 5. Enrich (optional)
        if self.enrich:
            try:
                from .enrichment.enricher import Enricher
                enricher = Enricher(self.config)
                if clusters:
                    results = enricher.enrich_clusters(clusters)
                    console.print(f"  [green]✓ Enriched {len(results)} cluster(s)[/]")
                else:
                    console.print("  [dim]No clusters to enrich[/]")
            except Exception as e:
                console.print(f"  [red]✗ Enrichment failed: {e}[/]")
                import traceback as _tb3
                console.print(f"  [red]{_tb3.format_exc()}[/]")

        # 6. Sync to Drive if enabled
        if self.config.get("vault_sync", "local") == "gdrive":
            try:
                from .sync.gdrive import GDriveSync
                syncer = GDriveSync(self.config)
                stats = syncer.sync()
                console.print(f"  [green]✓ Drive sync: {stats['uploaded']} uploaded[/]")
            except Exception as e:
                console.print(f"  [red]✗ Drive sync failed: {e}[/]")

        console.print("[bold green]✓ Batch complete![/]\n")
        console.print("[dim]👀 Watching for more files...[/]")
        import sys
        sys.stdout.flush()
        sys.stderr.flush()

    def run(self):
        """Start watching (blocks until Ctrl+C)."""
        self.ingest_path.mkdir(parents=True, exist_ok=True)
        self.observer.schedule(self.handler, str(self.ingest_path), recursive=True)
        self.observer.start()

        console.print(f"[bold]👀 Watching {self.ingest_path} for new files... (Ctrl+C to stop)[/]")
        if self.enrich:
            console.print("[dim]  Enrichment: enabled[/]")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping watcher...[/]")
            self.observer.stop()
        self.observer.join()
        console.print("[green]✓ Watcher stopped.[/]")
