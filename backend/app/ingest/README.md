# Line ingestion (`app/ingest/`)

Loads one production line's daily station exports into the process model
(ADR-005) of a deployment database (ADR-004).

**Responsibility:** read station CSV files, keep in-scope pieces only, write
operations, recipes, part instances, step results and measurement results,
and record every file in the audit log with its row counts.

**Boundaries:**
- No customer names, folder names, part numbers or files in this repo. The
  real ingest config, specification file and station folders live outside
  it and are passed at run time (`--config`/`INGEST_CONFIG_PATH`,
  `--data-dir`/`LINE_DATA_DIR`, `--file`). `config.example.yaml` and
  `specs.example.yaml` show the format with fictitious values.
- Measurement rows are insert-only. A rerun skips files already loaded
  (same SHA-256), so an interrupted load resumes where it stopped.
- Daily statistics are derived. `build_daily_stats` rebuilds them at any time.

| Module | Role |
|---|---|
| `config.py` | Loads and validates the ingest YAML (plant, product, recipes in scope, stations in process order) |
| `stations.py` | Streams one station CSV (`;`, latin-1, `YYYYMMDD-HH:MM:SS`), flags bad rows |
| `setup.py` | Creates the catalog for the line: hierarchy, operations, programs, characteristics, recipes |
| `loader.py` | Loads files: recipe scope, quarantine, repeat attempts, COPY, one transaction and one audit entry per file |
| `specs.py` | Imports versioned drawing specifications |
| `stats.py` | Rebuilds the daily per-step and per-characteristic tables |

## Commands

All take `--config` (or `INGEST_CONFIG_PATH`). Run them in this order:

| Step | Command | Notes |
|---|---|---|
| 1 | `python -m app.cli.purge_domain_data --dry-run` then `--confirm` | Only on the first load. Removes all domain data, including demo data. Users, roles and the audit log stay. |
| 2 | `python -m app.cli.import_specifications --file specs.yaml --data-dir DIR` | Before the load, so each value gets its drawing verdict. |
| 3 | `python -m app.cli.ingest_line --data-dir DIR --dry-run` | Counts only. Check the recipe and program totals. |
| 4 | `python -m app.cli.ingest_line --data-dir DIR` | `--raw-store skip` when no object storage is configured. |
| 5 | `python -m app.cli.build_daily_stats` | After every load and every specification import. |
| 6 | `python -m app.cli.ingest_report` | Reconciliation: rows read = loaded + out of scope + quarantined, per station. |

Later, when the variant of a recipe is confirmed:

```bash
python -m app.cli.relabel_recipe --recipe 2 --variant-part MI-DEMO-2001-A
```

Relabelling changes only the label in the views. No reload is needed.

## Capacity

Per million in-scope pieces with seven stations, plan for about 42M result rows:

- About 13 GB of database disk with indexes.
- Disk headroom of twice that size for the load and for `VACUUM`.

The loader keeps memory flat because it looks up existing pieces per file
instead of holding them all in memory. The only line-wide structure is the
recipe of each piece id, stored at one byte per id.

## Run with Docker Compose (VPS)

1. Back up the database with `pg_dump`.
2. Put the station folders and `ingest.yaml` and `specs.yaml` in host folders
   outside the repo.
3. Use the `docker-compose.ingest.yml` overlay. It mounts both folders
   read-only.

```bash
export LINE_DATA_HOST_DIR=/srv/line-data INGEST_CONFIG_HOST_DIR=/srv/ingest-config
```

```bash
docker compose -f docker-compose.yml -f docker-compose.ingest.yml run --rm backend \
  python -m app.cli.ingest_line --dry-run
```

Do not merge to the deploy branch while a load runs: the deploy restarts
the backend. A restarted load resumes from the first file not yet loaded.

## Unattended run (scheduled job)

`python -m app.cli.load_line_bundle` runs steps 1–6 with no shell. Use it on a
platform that can run a scheduled job next to the database, for example a
Render cron job. It takes three environment variables, set on the job and
never committed:

- `LINE_BUNDLE_URL`: HTTPS URL of a zip with one folder per station.
- `LINE_INGEST_CONFIG_YAML`: the ingest config. Station `folder` values are
  the folder names inside the zip.
- `LINE_SPECS_YAML`: the specification file.

What the job does on each run:

- Downloads the zip, with a size cap.
- Extracts only the CSV files that sit directly in a configured station
  folder.
- Purges demo data only before the first load.
- Writes a `line_bundle_loaded` audit entry when it finishes.

A rerun with the same inputs exits at once. A run that died resumes where it
stopped. Without the three variables, a run does nothing.

## Run from a platform shell (Render)

Use the shell of the API service, which already has `DATABASE_URL`.

1. Put the station folders under `/tmp/line-data`. The disk there is
   ephemeral, so delete it when done.
2. Write the two YAML files to `/tmp/ingest-config` with a heredoc.
3. Run steps 1–6 with `--raw-store skip`. A starter instance has no object
   storage attached.
4. Keep the shell open until the load ends. If it closes, rerun the same
   command and the load resumes.
