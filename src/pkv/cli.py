"""CLI entry point for Personal Knowledge Vault."""

import shutil
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .config import load_config, DEFAULT_CONFIG

console = Console()


@click.group()
@click.option("--config", "-c", "config_path", default=None, help="Path to config file")
@click.pass_context
def cli(ctx, config_path):
    """Personal Knowledge Vault - Ingest, organize, and query your knowledge."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path


def _get_config(ctx) -> dict:
    return load_config(ctx.obj.get("config_path"))


@cli.command()
@click.option("--path", default=None, help="Custom vault path")
@click.pass_context
def init(ctx, path):
    """Initialize a new PKV vault and configuration."""
    import yaml

    if path:
        vault_path = Path(path).expanduser().resolve()
    else:
        vault_path = Path("~/.pkv").expanduser()

    console.print(f"[bold green]Initializing PKV at {vault_path}[/]")

    # Create directories
    for d in ["vault/documents", "vault/conversations", "vault/meetings",
              "vault/decisions", "vault/entities/people", "vault/entities/projects",
              "vault/entities/topics", "ingest", "chroma"]:
        (vault_path / d).mkdir(parents=True, exist_ok=True)

    # Create config
    config_file = vault_path / "config.yaml"
    if not config_file.exists():
        cfg = dict(DEFAULT_CONFIG)
        cfg["vault_path"] = str(vault_path / "vault")
        cfg["ingest_path"] = str(vault_path / "ingest")
        cfg["chroma_path"] = str(vault_path / "chroma")
        config_text = yaml.dump(cfg, default_flow_style=False)
        # Add commented options at the top
        header = (
            "# Claude API key for enrichment (or set ANTHROPIC_API_KEY env var)\n"
            "# claude_api_key: sk-ant-your-key-here\n\n"
            "# Storage backend: chromadb (local) or bigquery (cloud)\n"
            "storage_backend: chromadb\n\n"
            "# BigQuery settings (when storage_backend: bigquery)\n"
            "# bigquery:\n"
            "#   project: ozpr-reporting-dev\n"
            "#   dataset: dbt_oriol\n"
            "#   table: pkv_oriol\n\n"
            "# Vault sync: local or gdrive\n"
            "vault_sync: local\n\n"
            "# Google Drive settings (when vault_sync: gdrive)\n"
            "# gdrive:\n"
            '#   vault_folder_id: "your-drive-folder-id"\n\n'
        )
        config_text = header + config_text
        config_file.write_text(config_text)
        console.print(f"  Created config: {config_file}")

    # Copy ontology
    ontology_src = Path(__file__).parent.parent.parent / "config" / "ontology.yaml"
    ontology_dst = vault_path / "ontology.yaml"
    if ontology_src.exists() and not ontology_dst.exists():
        shutil.copy2(ontology_src, ontology_dst)
        console.print(f"  Created ontology: {ontology_dst}")

    console.print("[bold green]✓ PKV initialized![/]")
    console.print(f"  Drop files in: {vault_path / 'ingest'}")
    console.print(f"  Run: pkv ingest")


@cli.command()
@click.argument("path", required=False)
@click.pass_context
def ingest(ctx, path):
    """Ingest files from the ingest directory or a specific path."""
    from .ingest.processor import process_file, process_directory
    from .vault.writer import VaultWriter

    config = _get_config(ctx)
    writer = VaultWriter(config["vault_path"])

    if path:
        file_path = Path(path)
        if file_path.is_file():
            docs = []
            doc = process_file(file_path, config)
            if doc:
                docs.append(doc)
        elif file_path.is_dir():
            docs = process_directory(file_path, config)
        else:
            console.print(f"[red]Path not found: {path}[/]")
            return
    else:
        ingest_path = Path(config["ingest_path"])
        if not ingest_path.exists():
            console.print(f"[yellow]Ingest directory not found: {ingest_path}[/]")
            return
        docs = process_directory(ingest_path, config)

    if not docs:
        console.print("[yellow]No files to process.[/]")
        return

    console.print(f"[blue]Processing {len(docs)} document(s)...[/]")
    paths = writer.write_many(docs)
    console.print(f"[green]✓ Wrote {len(paths)} new document(s) to vault[/]")
    for p in paths:
        console.print(f"  → {p}")

    skipped = len(docs) - len(paths)
    if skipped:
        console.print(f"  [dim]({skipped} duplicate(s) skipped)[/]")


@cli.command()
@click.pass_context
def embed(ctx):
    """Embed all unembedded documents in the vault."""
    from .ingest.processor import process_directory
    from .embeddings.embedder import Embedder

    config = _get_config(ctx)
    vault_path = Path(config["vault_path"])

    if not vault_path.exists():
        console.print("[red]Vault not found. Run 'pkv init' first.[/]")
        return

    console.print("[blue]Loading documents from vault...[/]")
    docs = process_directory(vault_path, config)

    if not docs:
        console.print("[yellow]No documents to embed.[/]")
        return

    console.print(f"[blue]Embedding {sum(len(d.chunks) for d in docs)} chunks from {len(docs)} documents...[/]")
    embedder = Embedder(config)
    count = embedder.embed_documents(docs)
    console.print(f"[green]✓ Embedded {count} new chunk(s)[/]")


@cli.command()
@click.argument("query")
@click.option("--n", "-n", default=5, help="Number of results")
@click.pass_context
def search(ctx, query, n):
    """Semantic search over the knowledge vault."""
    from .query.search import semantic_search

    config = _get_config(ctx)
    console.print(f"[blue]Searching for: '{query}'[/]\n")

    results = semantic_search(query, config, n_results=n)

    if not results:
        console.print("[yellow]No results found. Have you run 'pkv embed'?[/]")
        return

    table = Table(title="Search Results")
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="cyan")
    table.add_column("Score", justify="right", style="green")
    table.add_column("Preview", max_width=60)

    for i, r in enumerate(results, 1):
        title = r["metadata"].get("title", "Unknown")
        score = f"{1 - r['distance']:.3f}"
        preview = r["document"][:80].replace("\n", " ")
        table.add_row(str(i), title, score, preview)

    console.print(table)


@cli.command()
@click.pass_context
def cluster(ctx):
    """Run OPTICS clustering on embedded documents."""
    from .clustering.cluster import run_clustering
    from .clustering.relationships import extract_relationships

    config = _get_config(ctx)
    console.print("[blue]Running clustering...[/]")

    clusters = run_clustering(config)
    if not clusters:
        console.print("[yellow]No clusters found. Need more embedded documents.[/]")
        return

    console.print(f"[green]✓ Found {len(clusters)} cluster(s)[/]")
    for c in clusters:
        console.print(f"  Cluster {c.cluster_id}: {len(c.document_ids)} documents")

    relationships = extract_relationships(clusters, config)
    console.print(f"\n[green]✓ Found {len(relationships)} relationship(s)[/]")
    for r in relationships[:10]:
        console.print(f"  {r.doc_a} ↔ {r.doc_b} (score: {r.score:.3f})")


@cli.command()
@click.pass_context
def enrich(ctx):
    """Run Claude API enrichment on clusters."""
    from .clustering.cluster import run_clustering
    from .enrichment.enricher import Enricher

    config = _get_config(ctx)

    try:
        enricher = Enricher(config)
    except ValueError as e:
        console.print(f"[red]{e}[/]")
        return

    console.print("[blue]Running clustering...[/]")
    clusters = run_clustering(config)
    if not clusters:
        console.print("[yellow]No clusters to enrich.[/]")
        return

    console.print(f"[blue]Enriching {len(clusters)} cluster(s) with Claude...[/]")
    results = enricher.enrich_clusters(clusters)

    for r in results:
        if "error" in r:
            console.print(f"  [red]Cluster {r['cluster_id']}: {r['error']}[/]")
        else:
            console.print(f"  [green]Cluster {r['cluster_id']}: {r.get('label', 'N/A')}[/]")
            entities = r.get("entities", [])
            if entities:
                for e in entities:
                    console.print(f"    → {e['name']} ({e['type']})")


@cli.command()
@click.pass_context
def janitor(ctx):
    """Run maintenance: dedup, fix frontmatter."""
    from .maintenance.janitor import run_janitor

    config = _get_config(ctx)
    console.print("[blue]Running janitor...[/]")
    stats = run_janitor(config)

    console.print(f"[green]✓ Maintenance complete[/]")
    console.print(f"  Duplicates removed: {stats['duplicates_removed']}")
    console.print(f"  Frontmatter fixed: {stats['frontmatter_fixed']}")


@cli.command()
@click.pass_context
def stats(ctx):
    """Show vault statistics."""
    from .maintenance.heartbeat import vault_stats

    config = _get_config(ctx)
    s = vault_stats(config)

    console.print(f"\n[bold]📊 Vault Statistics[/]")
    console.print(f"  Total documents: {s['total_documents']}")
    console.print(f"  Embedded chunks: {s.get('embedded_chunks', 0)}")
    if s.get("folders"):
        console.print(f"\n  [bold]Folders:[/]")
        for folder, count in sorted(s["folders"].items()):
            console.print(f"    {folder}: {count}")


@cli.command()
@click.argument("question")
@click.option("--n", "-n", default=10, help="Number of context chunks to retrieve")
@click.pass_context
def ask(ctx, question, n):
    """Ask a question and get an AI-synthesized answer from your vault."""
    from .qa import ask_question
    from rich.markdown import Markdown
    from rich.panel import Panel

    config = _get_config(ctx)
    console.print(f"[blue]Searching vault for context...[/]\n")

    try:
        result = ask_question(question, config, n_chunks=n)
    except ValueError as e:
        console.print(f"[red]{e}[/]")
        return

    # Print answer
    console.print(Panel(Markdown(result["answer"]), title="Answer", border_style="green"))

    # Print sources
    if result["sources"]:
        console.print("\n[bold]📚 Sources:[/]")
        for title in result["sources"]:
            console.print(f"  • [[{title}]]")


@cli.command()
@click.pass_context
def pipeline(ctx):
    """Run full pipeline: ingest → embed → cluster → enrich."""
    console.print("[bold blue]Running full pipeline...[/]\n")
    ctx.invoke(ingest)
    console.print()
    ctx.invoke(embed)
    console.print()
    ctx.invoke(cluster)
    console.print()

    config = _get_config(ctx)
    if config.get("claude_api_key"):
        ctx.invoke(enrich)
    else:
        console.print("[dim]Skipping enrichment (no API key set)[/]")

    # Sync to Drive if enabled
    _run_sync_if_enabled(config)

    console.print("\n[bold green]✓ Pipeline complete![/]")


@cli.command()
@click.pass_context
def sync(ctx):
    """Sync vault to Google Drive (when vault_sync: gdrive)."""
    config = _get_config(ctx)
    if config.get("vault_sync", "local") != "gdrive":
        console.print("[yellow]vault_sync is not set to 'gdrive' in config. Nothing to do.[/]")
        return
    from .sync.gdrive import GDriveSync
    try:
        syncer = GDriveSync(config)
    except ValueError as e:
        console.print(f"[red]{e}[/]")
        return
    console.print("[blue]Syncing vault to Google Drive...[/]")
    stats = syncer.sync()
    console.print(f"[green]✓ Sync complete — uploaded: {stats['uploaded']}, skipped: {stats['skipped']}, errors: {stats['errors']}[/]")


def _run_sync_if_enabled(config: dict):
    """Run Drive sync if enabled in config."""
    if config.get("vault_sync", "local") == "gdrive":
        try:
            from .sync.gdrive import GDriveSync
            syncer = GDriveSync(config)
            stats = syncer.sync()
            console.print(f"  [green]✓ Drive sync: {stats['uploaded']} uploaded[/]")
        except Exception as e:
            console.print(f"  [red]✗ Drive sync failed: {e}[/]")


@cli.command("sync-chroma")
@click.option("--host", default=None, help="Remote host (user@hostname)")
@click.option("--dest", default=None, help="Remote PKV base path (default: ~/.pkv)")
@click.option("--dry-run", is_flag=True, help="Show what would be synced without copying")
@click.pass_context
def sync_chroma(ctx, host, dest, dry_run):
    """Push local PKV data (vault + chroma + config) to a remote machine via rsync over SSH."""
    import subprocess

    config = _get_config(ctx)

    # Get settings from config or CLI args
    remote_cfg = config.get("sync_chroma", {})
    remote_host = host or remote_cfg.get("host")
    remote_dest = dest or remote_cfg.get("dest", "~/.pkv")

    if not remote_host:
        console.print("[red]No remote host specified. Use --host or set sync_chroma.host in config.yaml[/]")
        console.print("[dim]Example: pkv sync-chroma --host fuertesito@Oriols-MacBook-Pro.local[/]")
        return

    # Resolve local PKV base (parent of chroma_path)
    local_chroma = Path(config["chroma_path"]).expanduser().resolve()
    local_pkv = local_chroma.parent  # ~/.pkv
    if not local_pkv.exists():
        console.print(f"[red]Local PKV directory not found: {local_pkv}[/]")
        return

    target = f"{remote_host}:{remote_dest}"
    cmd = [
        "rsync", "-az", "--delete",
        "--progress",
        "--exclude", "ingest/",  # no need to sync pending ingestion files
        str(local_pkv) + "/",
        target + "/",
    ]
    if dry_run:
        cmd.insert(1, "--dry-run")

    console.print(f"[blue]{'[DRY RUN] ' if dry_run else ''}Syncing PKV → {target}[/]")
    console.print(f"  Local:  {local_pkv}")
    console.print(f"  Remote: {target}\n")

    try:
        result = subprocess.run(cmd, check=True)
        if result.returncode == 0:
            console.print(f"\n[green]✓ {'Dry run complete' if dry_run else 'PKV synced successfully (vault + chroma + config)'}[/]")
    except subprocess.CalledProcessError as e:
        console.print(f"\n[red]✗ rsync failed (exit {e.returncode})[/]")
        console.print("[dim]Check SSH access: ssh {remote_host} echo ok[/]")
    except FileNotFoundError:
        console.print("[red]rsync not found. Install with: brew install rsync[/]")


@cli.command("sync-bq")
@click.option("--collection", default="documents", help="Collection name to sync")
@click.pass_context
def sync_bq(ctx, collection):
    """One-time full sync: push all ChromaDB vectors → BigQuery."""
    config = _get_config(ctx)

    from .storage.chromadb import ChromaVectorStore
    from .storage.bigquery import BigQueryVectorStore

    chroma = ChromaVectorStore(config["chroma_path"])
    bq_cfg = config.get("bigquery", {})
    bq = BigQueryVectorStore(
        project=bq_cfg.get("project", "ozpr-reporting-dev"),
        dataset=bq_cfg.get("dataset", "dbt_oriol"),
        table=bq_cfg.get("table", "pkv_oriol"),
    )

    console.print(f"[blue]Reading all documents from ChromaDB...[/]")
    data = chroma.get_all(collection)
    total = len(data["ids"])
    console.print(f"  Found {total} chunks")

    if total == 0:
        console.print("[yellow]Nothing to sync.[/]")
        return

    # Get embeddings too
    import numpy as np
    all_data = chroma.get_by_ids(collection, data["ids"], include=["documents", "metadatas", "embeddings"])
    # Convert numpy arrays to plain lists for JSON serialization
    if "embeddings" in all_data and len(all_data["embeddings"]) > 0:
        all_data["embeddings"] = [
            e.tolist() if isinstance(e, np.ndarray) else list(e)
            for e in all_data["embeddings"]
        ]

    batch_size = 500
    synced = 0
    for i in range(0, total, batch_size):
        batch_end = min(i + batch_size, total)
        bq.add_documents(
            collection_name=collection,
            ids=all_data["ids"][i:batch_end],
            embeddings=all_data["embeddings"][i:batch_end],
            documents=all_data["documents"][i:batch_end],
            metadatas=all_data["metadatas"][i:batch_end],
        )
        synced += batch_end - i
        console.print(f"  [green]Synced {synced}/{total}[/]")

    console.print(f"\n[green]✓ All {total} chunks synced to BigQuery ({bq.full_table})[/]")


@cli.command()
@click.option("--enrich/--no-enrich", default=True, help="Run enrichment (default: on, use --no-enrich to skip)")
@click.option("--debounce", default=5.0, help="Seconds to wait after last change before processing")
@click.pass_context
def watch(ctx, enrich, debounce):
    """Watch ~/.pkv/ingest/ for new files and auto-run pipeline."""
    from .watcher import FileWatcher

    config = _get_config(ctx)
    watcher = FileWatcher(config, enrich=enrich, debounce=debounce)
    watcher.run()


if __name__ == "__main__":
    cli()
