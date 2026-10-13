# Copper concentrate trade flows: ingestions and data quality checks

## What I found

I ingested monthly copper ore and concentrate imports (HS 260300) for China, Japan, Korea, India and Spain, 2022-2025, from the UN Comtrade API (228 rows). Five SQL checks raised 32 flags. I investigated the ones below and separated what I verified from what I suspect.

1. China's 2025 monthly data is missing from the API.
China's series ends in December 2024; every other reporter runs to December 2025. For the three 2025 months I tested (January, June, December), the API returned status 200 with zero rows and no error.

2. Six months had no net weight, recovered from a second field.
Korea (May 2022, July 2025) and Spain (Feb 2022, Aug 2023, Jan 2025, May 2025) had a trade value but a null `netWgt`. The raw record held the weight in `altQty` (unit: kg). I used it as a fallback and recorded the source in a `weight_source` column. Sanity check: Spain Feb 2022 comes out at about $2,170 per tonne, in line with other months.

3. India's two double-flagged months were changes in supplier, not data errors.
- Mar 2025: weight fell to 40 kt and price per tonne rose. Chile (50.7 kt in February, 41.8 kt in April) was absent; the origins that month were Australia, Namibia, Tanzania and DRC.
- Sep 2022: weight more than doubled while price fell. Imports came from Chile, Panama, Peru and Brazil (all roughly $1,600-2,300 per tonne) instead of Indonesia and Australia (about $3,600-4,100 in August).
In both cases the origins add up to the World total, so nothing was missing. Unit values differ systematically by origin. 

4. Spain and Korea both dipped sharply in February 2025.
Spain imported 7.9 kt (a 92% drop against its trailing average); essentially all of it came from Portugal. The large lots from Peru, Chile and Brazil that appear in March were absent. Korea's imports from Peru were 0.09 kt in February and 54.7 kt in March. Peru's own export data shows exports to Korea falling from 57.0 kt in January to 11.5 kt in February, and no rows for Spain in January. This is consistent with a shipment-timing or supply effect, but it doesn't match one-for-one.

## Design choices

- Threshold: I counted weight flags at 40/50/60% deviation from the trailing 6-month average: 40, 28 and 18 flags in total. I chose 50% as the least noisy setting that still catches large drops.
- Why a trailing average: month-on-month change flagged most drops twice, once for the dip and once for the rebound.
- Price bounds: 1,000-8,000 USD/t, set from the observed range (about 1,560 to 4,870).
- Volatility differs by reporter (std/mean of monthly weight): China 0.09, Japan 0.17, Korea 0.30, India 0.37, Spain 0.43. Flag counts rise in the same order.

## Limitations and next steps

- One threshold fits all reporters poorly. A threshold scaled to each series' own volatility is the main next step.
- Checks at the total level can't tell a supplier change from a data fault. Partner-level checks, including a test that partner rows sum to the World total, would fix this.
- Raw tonnes ignore concentrate grade, so volumes aren't comparable across origins.
- A rolling average misses sustained shifts (for example Japan's late-2025 decline).
- Origin-level rows include trace volumes (a few kg) that would need a minimum-volume filter.

## Project structure

- `ingest.py`: pulls monthly data from the Comtrade API and loads it into the database
- `checks.sql`: the five SQL data quality checks
- `validate.py`: runs the checks, saves flags to a table and CSV, draws the chart
- `db.py`: chooses SQLite or PostgreSQL based on `DATABASE_URL`
- `schema.sql`: table definitions
- `run_sql.py`: small helper for running one SQL file
- `volatility.py`: variation in monthly weight per reporter
- `reports/`: output chart and CSV of flagged months
- `investigation/`: scripts used to inspect raw API records and origin-country breakdowns

## Run it

pip install -r requirements.txt
export COMTRADE_KEY=...          # free key from comtradedeveloper.un.org
export DATABASE_URL=postgresql+psycopg2://localhost:5432/trade   # optional; defaults to SQLite
python ingest.py
python validate.py