import json
from pathlib import Path
from threading import Lock
from aplicacao.modelos.resumo import SummaryResponse


class SummaryHistoryRepository:
    """Stores recent summarization results on disk in a thread-safe JSON file."""

    def __init__(self, file_path: Path, max_items: int = 50) -> None:
        self._file_path = file_path
        self._max_items = max_items
        self._lock = Lock()

    def _ensure_storage(self) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._file_path.exists():
            self._file_path.write_text("[]", encoding="utf-8")

    def _read_all_unlocked(self) -> list[dict]:
        self._ensure_storage()
        raw = self._file_path.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

    def _write_all_unlocked(self, items: list[dict]) -> None:
        self._ensure_storage()
        self._file_path.write_text(
            json.dumps(items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add(self, entry: SummaryResponse) -> SummaryResponse:
        with self._lock:
            items = self._read_all_unlocked()
            items = [item for item in items if item.get("id") != entry.id]
            items.insert(0, entry.model_dump(mode="json"))
            trimmed = items[: self._max_items]
            self._write_all_unlocked(trimmed)
        return entry

    def list_recent(self, limit: int = 20) -> list[SummaryResponse]:
        with self._lock:
            items = self._read_all_unlocked()
        bounded = items[: max(1, min(limit, self._max_items))]
        return [SummaryResponse.model_validate(item) for item in bounded]

    def get_by_id(self, summary_id: str) -> SummaryResponse | None:
        with self._lock:
            items = self._read_all_unlocked()
        for item in items:
            if item.get("id") == summary_id:
                return SummaryResponse.model_validate(item)
        return None

    def delete_by_id(self, summary_id: str) -> bool:
        with self._lock:
            items = self._read_all_unlocked()
            remaining = [item for item in items if item.get("id") != summary_id]
            if len(remaining) == len(items):
                return False
            self._write_all_unlocked(remaining)
        return True

    def clear(self) -> None:
        with self._lock:
            self._write_all_unlocked([])
