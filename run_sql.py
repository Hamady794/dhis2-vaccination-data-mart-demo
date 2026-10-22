#!/usr/bin/env python3
"""
Exécute dans BigQuery les couches Silver et Gold, puis les tests SQL.

Prérequis : la couche Bronze est chargée (python extract_load.py --load).

    python run_sql.py --project mon-projet

Variables d'environnement acceptées : BQ_PROJECT, BQ_LOCATION.
Les fichiers SQL utilisent les jetons {project}, {bronze}, {silver}, {gold}.
Un test SQL réussit s'il retourne 0 ligne.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent
log = logging.getLogger("run-sql")


def render(sql: str, tokens: dict[str, str]) -> str:
    for key, value in tokens.items():
        sql = sql.replace("{" + key + "}", value)
    return sql


def main() -> None:
    p = argparse.ArgumentParser(description="Silver + Gold + tests dans BigQuery")
    p.add_argument("--project", default=os.environ.get("BQ_PROJECT"))
    p.add_argument("--location", default=os.environ.get("BQ_LOCATION", "US"))
    p.add_argument("--bronze", default="vaccination_bronze")
    p.add_argument("--silver", default="vaccination_silver")
    p.add_argument("--gold", default="vaccination_gold")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not args.project:
        sys.exit("Indique --project ou la variable BQ_PROJECT.")

    from google.cloud import bigquery

    client = bigquery.Client(project=args.project, location=args.location)
    tokens = {"project": args.project, "bronze": args.bronze,
              "silver": args.silver, "gold": args.gold}

    for ds_name in (args.silver, args.gold):
        ds = bigquery.Dataset(f"{args.project}.{ds_name}")
        ds.location = args.location
        client.create_dataset(ds, exists_ok=True)

    for folder in ("silver", "gold"):
        for f in sorted((ROOT / "sql" / folder).glob("*.sql")):
            log.info("Exécution : %s/%s", folder, f.name)
            client.query(render(f.read_text(encoding="utf-8"), tokens)).result()

    failures = 0
    for f in sorted((ROOT / "sql" / "tests").glob("*.sql")):
        rows = list(client.query(render(f.read_text(encoding="utf-8"), tokens)).result())
        if rows:
            failures += 1
            log.error("ÉCHEC %-40s %d ligne(s), exemple : %s", f.name, len(rows), dict(rows[0]))
        else:
            log.info("OK    %s", f.name)

    if failures:
        sys.exit(f"{failures} test(s) en échec.")
    log.info("Tous les tests SQL sont passés.")


if __name__ == "__main__":
    main()
