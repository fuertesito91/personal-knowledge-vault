"""Google Drive vault sync — one-way local → Drive.

All GCP imports are lazy. This module is only loaded when vault_sync=gdrive.
"""

import hashlib
import json
from pathlib import Path
from typing import Any


SYNC_STATE_FILE = ".gdrive_sync_state.json"


class GDriveSync:
    """Syncs local vault markdown files to a Google Drive folder."""

    def __init__(self, config: dict[str, Any]):
        gdrive_cfg = config.get("gdrive", {})
        self.vault_folder_id = gdrive_cfg.get("vault_folder_id", "")
        if not self.vault_folder_id:
            raise ValueError("gdrive.vault_folder_id must be set in config when vault_sync=gdrive")
        self.vault_path = Path(config["vault_path"])
        self.state_path = self.vault_path / SYNC_STATE_FILE
        self._service = None
        self._folder_cache: dict[str, str] = {}  # relative_path -> drive folder id

    @property
    def service(self):
        if self._service is None:
            from google.oauth2 import credentials as _  # noqa: ensure google-auth available
            import google.auth
            from googleapiclient.discovery import build

            creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/drive.file"])
            self._service = build("drive", "v3", credentials=creds)
        return self._service

    def _load_state(self) -> dict[str, str]:
        """Load sync state: {relative_path: content_hash}."""
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_state(self, state: dict[str, str]):
        self.state_path.write_text(json.dumps(state, indent=2))

    @staticmethod
    def _file_hash(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _get_or_create_folder(self, name: str, parent_id: str) -> str:
        """Get or create a folder in Drive."""
        cache_key = f"{parent_id}/{name}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]

        # Search for existing
        query = (
            f"name='{name}' and '{parent_id}' in parents "
            f"and mimeType='application/vnd.google-apps.folder' and trashed=false"
        )
        results = self.service.files().list(q=query, fields="files(id)").execute()
        files = results.get("files", [])

        if files:
            folder_id = files[0]["id"]
        else:
            metadata = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            }
            folder = self.service.files().create(body=metadata, fields="id").execute()
            folder_id = folder["id"]

        self._folder_cache[cache_key] = folder_id
        return folder_id

    def _ensure_folder_path(self, relative_dir: Path) -> str:
        """Create nested folder structure in Drive, returns final folder ID."""
        current_id = self.vault_folder_id
        for part in relative_dir.parts:
            current_id = self._get_or_create_folder(part, current_id)
        return current_id

    def _upload_file(self, local_path: Path, parent_folder_id: str):
        """Upload or update a file in Drive."""
        from googleapiclient.http import MediaFileUpload

        name = local_path.name
        # Check if file exists
        query = f"name='{name}' and '{parent_folder_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, fields="files(id)").execute()
        existing = results.get("files", [])

        media = MediaFileUpload(str(local_path), mimetype="text/markdown")

        if existing:
            # Update
            self.service.files().update(
                fileId=existing[0]["id"], media_body=media
            ).execute()
        else:
            # Create
            metadata = {"name": name, "parents": [parent_folder_id]}
            self.service.files().create(
                body=metadata, media_body=media, fields="id"
            ).execute()

    def sync(self) -> dict[str, int]:
        """Sync vault to Drive. Returns stats."""
        if not self.vault_path.exists():
            return {"uploaded": 0, "skipped": 0, "errors": 0}

        state = self._load_state()
        new_state = {}
        stats = {"uploaded": 0, "skipped": 0, "errors": 0}

        for md_file in sorted(self.vault_path.rglob("*.md")):
            if md_file.name.startswith("."):
                continue

            rel = md_file.relative_to(self.vault_path)
            rel_str = str(rel)
            content_hash = self._file_hash(md_file)
            new_state[rel_str] = content_hash

            # Skip if unchanged
            if state.get(rel_str) == content_hash:
                stats["skipped"] += 1
                continue

            try:
                parent_id = self._ensure_folder_path(rel.parent) if rel.parent != Path(".") else self.vault_folder_id
                self._upload_file(md_file, parent_id)
                stats["uploaded"] += 1
            except Exception as e:
                stats["errors"] += 1
                if stats["errors"] <= 3:  # Print first 3 errors
                    import sys
                    print(f"  ✗ {rel_str}: {e}", file=sys.stderr)
                elif stats["errors"] == 4:
                    print("  ... (suppressing further errors)", file=sys.stderr)
                # Don't save hash so it retries next time
                new_state[rel_str] = ""

        self._save_state(new_state)
        return stats
