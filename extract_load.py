#!/usr/bin/env python3
"""
Extraction DHIS2 -> fichiers Bronze (JSON/CSV) -> chargement BigQuery.

Projet : data mart vaccination (candidature Muso, Health Analytics Coordinator).

Ce que fait le script
---------------------
1. Extrait de l'API DHIS2 :
   - la hiérarchie des unités d'organisation (id, nom, niveau, parent, chemin)
   - la définition des indicateurs de vaccination retenus (numérateur,
     dénominateur, annualisation) : sert aux tests de qualité en couche Silver
   - les valeurs analytics (indicateur x unité d'org. x mois)
   - les informations du serveur (version, date), pour la reproductibilité
2. Sauvegarde le brut en JSON et en CSV dans data/bronze/<date>/
3. (option --load) charge le tout dans BigQuery, dataset Bronze.

Installation
------------
    pip install requests google-cloud-bigquery

Variables d'environnement
-------------------------
    DHIS2_URL        ex. https://play.im.dhis2.org/stable-2-42-x  (sans / final)
    DHIS2_USER       nom d'utilisateur DHIS2
    DHIS2_PASSWORD   mot de passe DHIS2
    BQ_PROJECT       identifiant du projet Google Cloud   (avec --load)
    BQ_DATASET       dataset Bronze, ex. vaccination_bronze (avec --load)
    BQ_LOCATION      ex. US ou EU (défaut : US)

Authentification BigQuery : `gcloud auth application-default login`
ou GOOGLE_APPLICATION_CREDENTIALS pointant vers une clé de compte de service.

Exemples
--------
    # Extraction locale seulement (aucun compte Google nécessaire)
    python extract_load.py

    # Extraction + chargement BigQuery, niveaux 2 et 3
    python extract_load.py --levels 2 3 --load
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger("dhis2-extract")

# --------------------------------------------------------------------------
# Indicateurs de vaccination retenus (identifiants issus de indicators.json)
# --------------------------------------------------------------------------
VACCINATION_INDICATORS = {
    "FnYCr2EAzWS": "BCG Coverage <1y",
    "iCBpPh3ehjg": "BCG Coverage - Adjusted for reporting",
    "i7WSgSJpnfu": "Penta 1 Coverage <1y",
    "Om2QoRtsncL": "Penta 2 Coverage <1y",
    "tUIlpyeeX9N": "Penta 3 Coverage <1y",
    "n5nS0SmkUpq": "OPV 0 Coverage <1y",
    "YlTWksXEhEO": "OPV 1 Coverage <1y",
    "QsuBK2pMfkk": "OPV 2 Coverage <1y",
    "JoEzWYGdX7s": "OPV 3 Coverage <1y",
    "FbKK4ofIv5R": "Measles Coverage <1y",
    "eTDtyyaSA7f": "FIC <1y",
    "IT8EAeFRAat": "FIC <1y - Adjusted for reporting",
    "EdN7qlmI5FS": "Dropout rate Penta 1 - 3",
    "d9thHOJMROr": "Dropout rate Penta 1 - Measles",
    "OEWO2PpiUKx": "BCG Stock PHU",
    "bASXd9ukRGD": "OPV Stock PHU",
    "loEBZlcsTlx": "Measles Stock End Balance",
}

DEFAULT_ROOT_OU = "ImspTQPwCqd"  # Sierra Leone (serveur de démo)
CHUNK_SIZE = 5  # nombre d'indicateurs par requête analytics


# --------------------------------------------------------------------------
# Client HTTP
# --------------------------------------------------------------------------
def make_session(user: str, password: str) -> requests.Session:
    s = requests.Session()
    s.auth = (user, password)
    s.headers.update({"Accept": "application/json"})
    retry = Retry(
        total=4,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s


def get_json(session: requests.Session, base: str, path: str, params=None) -> dict:
    url = f"{base}{path}"
    resp = session.get(url, params=params, timeout=120)
    if resp.status_code == 401:
        sys.exit("Erreur 401 : identifiants DHIS2 refusés (DHIS2_USER / DHIS2_PASSWORD).")
    if resp.status_code == 409:
        sys.exit(f"Erreur 409 (requête refusée par DHIS2) sur {path} : {resp.text[:500]}")
    resp.raise_for_status()
    return resp.json()


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------
def fetch_system_info(session, base) -> dict:
    info = get_json(session, base, "/api/system/info.json",
                    {"fields": "version,revision,serverDate,buildTime,systemName"})
    return info


def fetch_org_units(session, base) -> list[dict]:
    data = get_json(
        session, base, "/api/organisationUnits.json",
        {"paging": "false", "fields": "id,displayName,level,parent[id],path"},
    )
    rows = []
    for ou in data.get("organisationUnits", []):
        rows.append({
            "org_unit_id": ou["id"],
            "name": ou.get("displayName"),
            "level": ou.get("level"),
            "parent_id": (ou.get("parent") or {}).get("id"),
            "path": ou.get("path"),
        })
    log.info("Unités d'organisation : %d", len(rows))
    return rows


def fetch_indicator_definitions(session, base, ids: list[str]) -> list[dict]:
    data = get_json(
        session, base, "/api/indicators.json",
        {
            "paging": "false",
            "filter": f"id:in:[{','.join(ids)}]",
            "fields": "id,displayName,numerator,denominator,annualized,"
                      "indicatorType[displayName,factor]",
        },
    )
    rows = []
    for ind in data.get("indicators", []):
        itype = ind.get("indicatorType") or {}
        rows.append({
            "indicator_id": ind["id"],
            "name": ind.get("displayName"),
            "numerator": ind.get("numerator"),
            "denominator": ind.get("denominator"),
            "annualized": bool(ind.get("annualized")),
            "indicator_type": itype.get("displayName"),
            "factor": itype.get("factor"),
        })
    missing = set(ids) - {r["indicator_id"] for r in rows}
    if missing:
        log.warning("Indicateurs introuvables sur ce serveur : %s", sorted(missing))
    log.info("Définitions d'indicateurs : %d", len(rows))
    return rows


def fetch_analytics(session, base, indicator_ids, root_ou, levels, period) -> list[dict]:
    """Récupère indicateur x unité d'org. x période, par lots d'indicateurs."""
    ou_dim = ";".join([root_ou] + [f"LEVEL-{lv}" for lv in levels])
    out: list[dict] = []
    for i in range(0, len(indicator_ids), CHUNK_SIZE):
        chunk = indicator_ids[i:i + CHUNK_SIZE]
        params = [
            ("dimension", "dx:" + ";".join(chunk)),
            ("dimension", "pe:" + period),
            ("dimension", "ou:" + ou_dim),
            ("skipMeta", "true"),
            ("skipRounding", "false"),
        ]
        data = get_json(session, base, "/api/analytics.json", params)
        names = [h["name"] for h in data.get("headers", [])]
        try:
            ix = {k: names.index(k) for k in ("dx", "ou", "pe", "value")}
        except ValueError:
            sys.exit(f"En-têtes analytics inattendus : {names}")
        for row in data.get("rows", []):
            try:
                value = float(row[ix["value"]])
            except (TypeError, ValueError):
                value = None
            out.append({
                "indicator_id": row[ix["dx"]],
                "org_unit_id": row[ix["ou"]],
                "period": row[ix["pe"]],
                "value": value,
            })
        log.info("Analytics lot %d/%d : %d lignes cumulées",
                 i // CHUNK_SIZE + 1,
                 (len(indicator_ids) + CHUNK_SIZE - 1) // CHUNK_SIZE,
                 len(out))
    return out


# --------------------------------------------------------------------------
# Sauvegarde locale (Bronze fichiers)
# --------------------------------------------------------------------------
def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def sanity_report(analytics: list[dict]) -> None:
    """Petit contrôle visuel : min / max / nb de valeurs par indicateur."""
    by_ind: dict[str, list[float]] = {}
    for r in analytics:
        if r["value"] is not None:
            by_ind.setdefault(r["indicator_id"], []).append(r["value"])
    log.info("--- Contrôle rapide des valeurs (min / max / n) ---")
    for ind_id, vals in sorted(by_ind.items()):
        name = VACCINATION_INDICATORS.get(ind_id, ind_id)
        log.info("%-42s %8.2f %8.2f %6d", name, min(vals), max(vals), len(vals))
        if min(vals) < 0:
            log.warning("Valeur négative pour %s : à examiner en Silver", name)


# --------------------------------------------------------------------------
# Chargement BigQuery
# --------------------------------------------------------------------------
def load_to_bigquery(tables: dict[str, list[dict]], project: str, dataset: str,
                     location: str, extracted_at: str) -> None:
    from google.cloud import bigquery  # import tardif : optionnel sans --load

    S = bigquery.SchemaField
    schemas = {
        "bronze_org_units": [
            S("org_unit_id", "STRING"), S("name", "STRING"), S("level", "INT64"),
            S("parent_id", "STRING"), S("path", "STRING"), S("extracted_at", "TIMESTAMP"),
        ],
        "bronze_indicator_definitions": [
            S("indicator_id", "STRING"), S("name", "STRING"), S("numerator", "STRING"),
            S("denominator", "STRING"), S("annualized", "BOOL"),
            S("indicator_type", "STRING"), S("factor", "FLOAT64"),
            S("extracted_at", "TIMESTAMP"),
        ],
        "bronze_analytics": [
            S("indicator_id", "STRING"), S("org_unit_id", "STRING"),
            S("period", "STRING"), S("value", "FLOAT64"), S("extracted_at", "TIMESTAMP"),
        ],
        "bronze_extraction_log": [
            S("extracted_at", "TIMESTAMP"), S("dhis2_url", "STRING"),
            S("dhis2_version", "STRING"), S("dhis2_server_date", "STRING"),
            S("period", "STRING"), S("levels", "STRING"),
            S("n_org_units", "INT64"), S("n_indicators", "INT64"),
            S("n_analytics_rows", "INT64"),
        ],
    }

    client = bigquery.Client(project=project, location=location)
    ds = bigquery.Dataset(f"{project}.{dataset}")
    ds.location = location
    client.create_dataset(ds, exists_ok=True)

    for table, rows in tables.items():
        if not rows:
            log.warning("Table %s : aucune ligne, ignorée.", table)
            continue
        for r in rows:
            r["extracted_at"] = extracted_at
        disposition = (
            bigquery.WriteDisposition.WRITE_APPEND
            if table == "bronze_extraction_log"
            else bigquery.WriteDisposition.WRITE_TRUNCATE
        )
        job_config = bigquery.LoadJobConfig(
            schema=schemas[table], write_disposition=disposition,
        )
        # Chargement par "load job" (compatible avec le sandbox BigQuery gratuit)
        job = client.load_table_from_json(
            rows, f"{project}.{dataset}.{table}", job_config=job_config
        )
        job.result()
        log.info("BigQuery : %s.%s.%s chargée (%d lignes)", project, dataset, table, len(rows))


# --------------------------------------------------------------------------
# Programme principal
# --------------------------------------------------------------------------
def main() -> None:
    p = argparse.ArgumentParser(description="Extraction DHIS2 -> Bronze -> BigQuery")
    p.add_argument("--levels", nargs="+", type=int, default=[2],
                   help="niveaux d'unités d'org. à extraire (2 = districts). Défaut : 2")
    p.add_argument("--period", default="LAST_12_MONTHS",
                   help="période DHIS2 (défaut : LAST_12_MONTHS)")
    p.add_argument("--root", default=DEFAULT_ROOT_OU,
                   help="unité d'org. racine (défaut : Sierra Leone de la démo)")
    p.add_argument("--out", default="data/bronze", help="dossier de sortie local")
    p.add_argument("--load", action="store_true", help="charger dans BigQuery")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    base = os.environ.get("DHIS2_URL", "").rstrip("/")
    user = os.environ.get("DHIS2_USER")
    password = os.environ.get("DHIS2_PASSWORD")
    if not (base and user and password):
        sys.exit("Définis DHIS2_URL, DHIS2_USER et DHIS2_PASSWORD (voir l'en-tête du script).")

    session = make_session(user, password)
    now = datetime.now(timezone.utc)
    extracted_at = now.strftime("%Y-%m-%d %H:%M:%S")
    out_dir = Path(args.out) / now.strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)

    info = fetch_system_info(session, base)
    log.info("Serveur DHIS2 : version %s, date serveur %s",
             info.get("version"), info.get("serverDate"))

    ids = list(VACCINATION_INDICATORS.keys())
    org_units = fetch_org_units(session, base)
    definitions = fetch_indicator_definitions(session, base, ids)
    analytics = fetch_analytics(session, base, ids, args.root, args.levels, args.period)

    log_row = {
        "extracted_at": extracted_at,
        "dhis2_url": base,
        "dhis2_version": str(info.get("version")),
        "dhis2_server_date": str(info.get("serverDate")),
        "period": args.period,
        "levels": ",".join(str(x) for x in args.levels),
        "n_org_units": len(org_units),
        "n_indicators": len(definitions),
        "n_analytics_rows": len(analytics),
    }

    # Fichiers bruts (utiles pour GitHub et pour la reproductibilité)
    write_json(out_dir / "system_info.json", info)
    write_json(out_dir / "org_units.json", org_units)
    write_json(out_dir / "indicator_definitions.json", definitions)
    write_json(out_dir / "analytics.json", analytics)
    write_csv(out_dir / "org_units.csv", org_units)
    write_csv(out_dir / "indicator_definitions.csv", definitions)
    write_csv(out_dir / "analytics.csv", analytics)
    log.info("Fichiers écrits dans %s", out_dir)

    sanity_report(analytics)

    if args.load:
        project = os.environ.get("BQ_PROJECT")
        dataset = os.environ.get("BQ_DATASET")
        location = os.environ.get("BQ_LOCATION", "US")
        if not (project and dataset):
            sys.exit("Définis BQ_PROJECT et BQ_DATASET pour utiliser --load.")
        load_to_bigquery(
            {
                "bronze_org_units": org_units,
                "bronze_indicator_definitions": definitions,
                "bronze_analytics": analytics,
                "bronze_extraction_log": [log_row],
            },
            project, dataset, location, extracted_at,
        )

    log.info("Terminé.")


if __name__ == "__main__":
    main()
