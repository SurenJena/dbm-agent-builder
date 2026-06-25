#!/usr/bin/env python3
"""
analyze_dependencies.py — Oracle FK Dependency Analyzer
Reads schema_metadata.json produced by extract_schema.py and builds a
topologically-sorted table migration order that respects FK parent→child
dependencies.

Output: output/ddl/dependency_order.json
"""

import json
import logging
import os
import sys
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / "config" / ".env")

LOG_DIR    = Path(os.getenv("LOG_DIR", "./logs"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output")) / "ddl"
LOG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "analyze_dependencies.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_metadata(path: Path) -> dict:
    if not path.exists():
        log.error("Metadata file not found: %s  — run extract_schema.py first", path)
        sys.exit(1)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def build_dependency_graph(metadata: dict) -> dict:
    """
    Returns {table: set_of_parent_tables} derived from FK constraints.
    Only references *within* the same schema are considered.
    """
    schema = metadata["schema"]

    # Build constraint_name → table_name index
    con_to_table: dict[str, str] = {}
    for c in metadata["constraints"]:
        if c["constraint_type"] in ("P", "U"):
            con_to_table[c["constraint_name"]] = c["table_name"]

    deps: dict[str, set] = defaultdict(set)
    for table in metadata["tables"]:
        deps[table["table_name"]]  # ensure every table appears

    for c in metadata["constraints"]:
        if c["constraint_type"] != "R":
            continue
        child  = c["table_name"]
        r_con  = c.get("r_constraint_name")
        parent = con_to_table.get(r_con)
        if parent and parent != child:
            deps[child].add(parent)

    return {k: list(v) for k, v in deps.items()}


def topological_sort(deps: dict) -> list:
    """Kahn's algorithm — returns tables in safe migration order."""
    in_degree  = {t: 0 for t in deps}
    adj        = defaultdict(set)
    for child, parents in deps.items():
        for parent in parents:
            adj[parent].add(child)
            in_degree[child] += 1

    queue  = deque(sorted(t for t, d in in_degree.items() if d == 0))
    order  = []
    cycles = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for child in sorted(adj[node]):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    remaining = [t for t, d in in_degree.items() if d > 0]
    if remaining:
        log.warning("Circular FK dependencies detected: %s", remaining)
        log.warning("These tables will be appended at the end; FKs applied post-load.")
        cycles = remaining
        order.extend(sorted(remaining))

    return order, cycles


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    log.info("=" * 60)
    log.info("Dependency Analyzer")
    log.info("Started: %s", datetime.now().isoformat())
    log.info("=" * 60)

    metadata_path = OUTPUT_DIR / "schema_metadata.json"
    metadata      = load_metadata(metadata_path)

    dep_graph = build_dependency_graph(metadata)
    order, cycles = topological_sort(dep_graph)

    result = {
        "schema":          metadata["schema"],
        "analyzed_at":     datetime.now().isoformat(),
        "migration_order": order,
        "dependency_graph": dep_graph,
        "circular_dependencies": cycles,
        "total_tables":    len(order),
    }

    out_path = OUTPUT_DIR / "dependency_order.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)

    log.info("Migration order (%d tables):", len(order))
    for i, t in enumerate(order, 1):
        parents = dep_graph.get(t, [])
        dep_str = f"  ← depends on: {parents}" if parents else ""
        log.info("  %3d. %s%s", i, t, dep_str)

    if cycles:
        log.warning("Tables with circular FKs (%d): %s", len(cycles), cycles)

    log.info("Output: %s", out_path)


if __name__ == "__main__":
    main()
