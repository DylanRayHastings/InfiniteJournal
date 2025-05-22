import json
from pathlib import Path
from urllib.parse import urlparse

class CanvasDatabase:
    """
    Simple file-backed storage for strokes. Supports SQLite-style file URLs and plain paths.
    """
    def __init__(self, database_url: str) -> None:
        # Parse URL: support sqlite:///path or file:///path
        parsed = urlparse(database_url)
        if parsed.scheme in ('sqlite', 'file'):
            raw = parsed.path
            # Normalize Windows drive-letter paths
            if raw.startswith('/') and len(raw) > 2 and raw[2] == ':' and raw[1].isalpha():
                raw = raw.lstrip('/')
            self.file_path = Path(raw)
        else:
            # Treat as direct filesystem path
            self.file_path = Path(database_url)

        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize storage file if missing
        if not self.file_path.exists():
            self._write([])

    def add_stroke(self, stroke) -> None:
        """
        Append a stroke object, then save entire list to disk.
        Converts stroke to JSON-serializable form automatically.
        """
        strokes = self._read()
        strokes.append(stroke)
        self._write(strokes)

    def save(self) -> None:
        """
        For backward compatibility: alias for _write.
        """
        # No-op; add_stroke handles writing
        pass

    def _read(self) -> list:
        try:
            with self.file_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write(self, data: list) -> None:
        """
        Write the full data list to disk as JSON, using a custom serializer.
        """
        def _serializer(obj):
            # If object has __dict__, use it
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            # Fallback to string
            return str(obj)

        temp = self.file_path.with_suffix(self.file_path.suffix + '.tmp')
        with temp.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=_serializer)
        temp.replace(self.file_path)
