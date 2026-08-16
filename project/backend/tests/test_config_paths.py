from __future__ import annotations

from pathlib import Path

from app.config import PROJECT_ROOT, Settings


def test_relative_knowledge_paths_resolve_from_project_root(monkeypatch) -> None:
    monkeypatch.setenv(
        "KB_DB_PATH",
        "database/transport-safety-kb/data/transport_safety_kb.sqlite3",
    )
    monkeypatch.setenv("CHROMA_DIR", "database/transport-safety-kb/data/rag_chroma")

    configured = Settings()

    assert Path(configured.kb_db_path) == (
        PROJECT_ROOT
        / "database"
        / "transport-safety-kb"
        / "data"
        / "transport_safety_kb.sqlite3"
    )
    assert Path(configured.chroma_dir) == (
        PROJECT_ROOT / "database" / "transport-safety-kb" / "data" / "rag_chroma"
    )


def test_relative_sqlite_url_resolves_from_project_root(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./backend/data/app.db")

    configured = Settings()

    expected = (PROJECT_ROOT / "backend" / "data" / "app.db").as_posix()
    assert configured.database_url == f"sqlite:///{expected}"
