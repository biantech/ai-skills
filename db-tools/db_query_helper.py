#!/usr/bin/env python3
"""
db_query_helper.py
------------------
Multi-environment database query helper for yuanchuan projects.
Supports LOCAL (devdb/db191) and DEV001 (dev236) environments.

Usage:
    python3 db_query_helper.py --env local --sql "SELECT * FROM notification_message LIMIT 5"
    python3 db_query_helper.py --env dev001 --sql "SELECT id, user_id FROM notification_message WHERE id=1" --format json
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, date
from typing import Any

from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool


def _url(user: str, password: str, host: str, port: int, schema: str) -> str:
    """Build a SQLAlchemy URL with URL-encoded credentials."""
    return f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{schema}"


# ---------------------------------------------------------------------------
# Static environment configurations (no YAML parsing needed)
# ---------------------------------------------------------------------------
ENV_CONFIGS = {
    "local": {
        "url": _url("frchuser", "Frch2025@Dev", "57.155.71.191", 33336, "yuanchuan3"),
        "description": "LOCAL / devdb / db191",
    },
    "devdb": {"alias": "local"},
    "db191": {"alias": "local"},
    "dev001": {
        "url": _url("root", "goodall!", "192.168.110.236", 3306, "yuanchuan3"),
        "description": "DEV001 / dev236 / db236",
    },
    "dev236": {"alias": "dev001"},
    "db236":  {"alias": "dev001"},
}

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine factory with QueuePool
# ---------------------------------------------------------------------------
_engines: dict = {}


def get_engine(env: str):
    """Return a cached SQLAlchemy engine for the given environment."""
    cfg = ENV_CONFIGS.get(env.lower())
    if cfg is None:
        raise ValueError(f"Unknown environment: '{env}'. Valid options: {list(ENV_CONFIGS.keys())}")
    if "alias" in cfg:
        return get_engine(cfg["alias"])

    if env not in _engines:
        log.info("Creating connection pool for env=%s (%s)", env, cfg["description"])
        engine = create_engine(
            cfg["url"],
            poolclass=QueuePool,
            pool_size=3,
            max_overflow=5,
            pool_timeout=10,
            pool_recycle=1800,
            connect_args={
                "connect_timeout": 10,
                "charset": "utf8mb4",
                "ssl": {"verify_mode": False},  # SSL enabled, no cert verification
            },
        )
        _engines[env] = engine
    return _engines[env]

# ---------------------------------------------------------------------------
# Query executor
# ---------------------------------------------------------------------------

def run_query(env: str, sql: str) -> dict[str, Any]:
    """Execute SQL and return a result dict with columns, rows, and metadata."""
    engine = get_engine(env)
    log.info("Executing SQL on env=%s", env)
    start = time.monotonic()
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = [list(row) for row in result.fetchall()]
    elapsed = round(time.monotonic() - start, 3)
    log.info("Query completed in %.3fs, rows=%d", elapsed, len(rows))
    return {
        "env": env,
        "executed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_seconds": elapsed,
        "row_count": len(rows),
        "sql": sql.strip(),
        "columns": columns,
        "rows": rows,
    }

# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def _json_default(obj):
    if isinstance(obj, (datetime, date)):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def format_markdown(data: dict) -> str:
    """Render result as Markdown table with metadata header."""
    lines = [
        f"> **Env**: `{data['env']}` | **Rows**: {data['row_count']} "
        f"| **Time**: {data['elapsed_seconds']}s | **At**: {data['executed_at']}",
        f"```sql",
        data["sql"],
        "```",
        "",
    ]
    cols = data["columns"]
    rows = data["rows"]
    if not cols:
        lines.append("_No columns returned._")
    else:
        header = "| " + " | ".join(cols) + " |"
        sep    = "| " + " | ".join(["---"] * len(cols)) + " |"
        lines += [header, sep]
        for row in rows:
            lines.append("| " + " | ".join(str(v) if v is not None else "NULL" for v in row) + " |")
    return "\n".join(lines)


def format_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=_json_default)

# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="yuanchuan DB Query Helper")
    parser.add_argument("--env", "-e", default="local",
                        help="Target environment (local/devdb/db191/dev001/dev236/db236). Default: local")
    parser.add_argument("--sql", "-s", required=True,
                        help="SQL statement to execute")
    parser.add_argument("--format", "-f", choices=["markdown", "json"], default="markdown",
                        help="Output format. Default: markdown")
    args = parser.parse_args()

    try:
        data = run_query(args.env, args.sql)
        if args.format == "json":
            print(format_json(data))
        else:
            print(format_markdown(data))
    except Exception as exc:
        log.error("Query failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
