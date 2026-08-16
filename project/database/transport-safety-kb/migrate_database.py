from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from transport_kb.sqlite_store import migrate_database


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="将交通安全知识库 SQLite 从 v1 迁移到 v2")
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(__file__).resolve().parent / "data" / "transport_safety_kb.sqlite3",
    )
    args = parser.parse_args(argv)
    try:
        result = migrate_database(args.database)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"数据库迁移失败: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
