import logging
import os
import time

import requests
from sqlalchemy import create_engine, text
from db import get_engine

API_KEY = os.getenv("COMTRADE_KEY")
BASE_URL = "https://comtradeapi.un.org/data/v1/get/C/M/HS"
DB_URL = "sqlite:///trade.db"

REPORTERS = {156: "China", 392: "Japan", 410: "Rep. of Korea", 699: "India", 724: "Spain"}
CMD_CODE = "260300"
FLOW_CODE = "M"
PARTNER_CODE = 0
START_YEAR, END_YEAR = 2022, 2025

PAUSE_SECONDS = 2
MAX_RETRIES = 4

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ingest")

def fetch_year(reporter_code, year):
    params = {
        "reporterCode": reporter_code,
        "period": ",".join(f"{year}{m:02d}" for m in range(1, 13)),
        "cmdCode": CMD_CODE,
        "flowCode": FLOW_CODE,
        "partnerCode": PARTNER_CODE,
        "partner2Code": 0,
        "motCode": 0,
        "customsCode": "C00",
        "includeDesc": "true",
    }
    headers = {"Ocp-Apim-Subscription-Key": API_KEY}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(BASE_URL, params=params, headers=headers, timeout=60)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise requests.HTTPError(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            return resp.json().get("data") or []
        except (requests.RequestException, ValueError) as exc:
            wait = 5 * attempt
            log.warning("reporter=%s year=%s attempt %s/%s failed (%s); retrying in %ss",
                        reporter_code, year, attempt, MAX_RETRIES, exc, wait)
            time.sleep(wait)
    log.error("Giving up on reporter=%s year=%s", reporter_code, year)
    return []

def pick_weight(r):
    """Prefer netWgt; fall back to altQty only if its unit is kg."""
    net = r.get("netWgt")
    if net is not None:
        return net, "netWgt"
    alt = r.get("altQty")
    if r.get("altQtyUnitAbbr") == "kg" and alt:
        return alt, "altQty_kg"
    return None, "missing"

def to_rows(records):
    """Map raw API fields to our table columns and drop duplicate months."""
    unique = {}
    for r in records:
        weight, source = pick_weight(r)
        key = (r["reporterCode"], r["partnerCode"], r["flowCode"], str(r["cmdCode"]), int(r["period"]))
        unique[key] = {
            "reporter_code": r["reporterCode"],
            "reporter_name": r.get("reporterDesc"),
            "partner_code": r["partnerCode"],
            "flow_code": r["flowCode"],
            "cmd_code": str(r["cmdCode"]),
            "period": int(r["period"]),
            "net_wgt_kg": weight,
            "weight_source": source,
            "value_usd": r.get("primaryValue"),
        }
    dropped = len(records) - len(unique)
    if dropped:
        log.warning("Dropped %s duplicate rows returned by the API", dropped)
    return list(unique.values())


INSERT_SQL = text("""
    INSERT INTO trade_flows
        (weight_source, reporter_code, reporter_name, partner_code, flow_code, cmd_code,
         period, net_wgt_kg, value_usd)
    VALUES
        (:weight_source, :reporter_code, :reporter_name, :partner_code, :flow_code, :cmd_code,
         :period, :net_wgt_kg, :value_usd)
    ON CONFLICT (reporter_code, partner_code, flow_code, cmd_code, period)
    DO UPDATE SET
        weight_source = excluded.weight_source,
        reporter_name = excluded.reporter_name,
        net_wgt_kg    = excluded.net_wgt_kg,
        value_usd     = excluded.value_usd,
        loaded_at     = CURRENT_TIMESTAMP
""")


def load_rows(engine, rows):
    if not rows:
        return 0
    with engine.begin() as conn:
        conn.execute(INSERT_SQL, rows)
    return len(rows)

def main():
    if not API_KEY:
        raise SystemExit("Set COMTRADE_KEY first.")

    engine = get_engine()
    with open("schema.sql") as f:
        schema = f.read()
    with engine.begin() as conn:
        conn.execute(text(schema))

    total = 0
    for reporter_code, name in REPORTERS.items():
        for year in range(START_YEAR, END_YEAR + 1):
            records = fetch_year(reporter_code, year)
            n = load_rows(engine, to_rows(records))
            total += n
            log.info("%-14s %s -> %s rows loaded", name, year, n)
            time.sleep(PAUSE_SECONDS)
    log.info("Done. %s rows loaded in total.", total)


if __name__ == "__main__":
    main()