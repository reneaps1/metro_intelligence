# connectors — turning source files into platform data

No engine or service depends on a specific source (CLAUDE.md §3). Each
connector owns its format: structural/safety validation and parsing.

- `base.py` — the `ImportConnector` contract (F4.5) and `FileValidationError`
  (its message is safe to return to the caller as-is).
- `manual_upload.py` — the catalog's fixed wide CSV (`COL_<balloon>` columns).
  Feeds the **immutable measurement history** through `/api/v1/imports`
  (raw file kept in object storage, results traceable to it).
- `dimensional_csv.py` — IQ-F6, industrial edition. Any column layout →
  `DimensionalDataset` (`app/engines/quality_analytics/`) through an explicit,
  user-confirmed column mapping. Used by `/api/v1/quality-analytics/imports/preview`
  and `/datasets` for an **exploratory analysis**: nothing is written to the
  measurement history, PostgreSQL or MinIO (decision D6; the dataset lives in
  memory for its owner, `app/services/imported_dataset_store.py`).

## dimensional_csv in short

- `sniff()` — encoding (UTF-8 / Windows-1252), delimiter (`,` `;` tab `|`),
  decimal mark, column kinds by majority rule, date order, suggested mapping
  (aliases in Spanish/English/German). A suggestion only; the user confirms it.
- `build_dataset()` — *long* layout (one row per measurement, pivoted to one
  piece per piece ID, or per timestamp + nest + machine without one) or *wide*
  layout (one row per piece, one column per variable). Every rejected row is
  counted in quarantine with its reason (wrong column count, bad/implausible
  date, empty variable, null or non-numeric value, unit mismatch, duplicate
  piece/variable); nothing is dropped silently.
- Specification: limits from the file (long layout) or typed by the user
  (overrides the file). Without LSL/USL a variable has no spec NOK and no
  Cp/Cpk. A source OK/NOK column is kept as `reported_nok`, apart from the
  verdict recalculated from the specification.
- Hardening shared with `manual_upload`: binary signatures and
  formula-injection payloads reject the whole file; cell content is never
  evaluated; labels are length-capped; column and variable counts are capped.

## Large files: sample in the web request, full file offline

The web path never processes a whole multi-GB export. The browser sends only
the head of a file larger than `DIMENSIONAL_IMPORT_MAX_MB`, the backend stops
at `DIMENSIONAL_IMPORT_MAX_ROWS`, and the report states the share analysed
("sample of X rows, ~Y % of the file"). The head is time-ordered in typical
exports, so a sample covers the *first* period, not a random draw.

### Offline batch converter (IQ-F10)

`long_signal_batch.py` converts full *long signal* exports (`id,address,timestamp,value`,
one row per value, tens of millions of rows) on the operator's machine:

```
python -m app.connectors.long_signal_batch inventory --out <private>/inventory.json FILE...
python -m app.connectors.long_signal_batch convert --mapping <private>/mapping.json --out <private>/dataset FILE...
```

- A PRIVATE mapping assigns each address a role: nest, mold cavity, total
  verdict, station verdicts (in process order), dimensional variables, the
  empty-cycle rule and optional UI presets. Unmapped addresses are dropped on
  read; piece identifiers and source paths are never written.
- Bounded memory: pass 1 spills mapped rows into K hash partitions by piece
  id; pass 2 rebuilds one partition at a time (last value per piece and
  address by timestamp, then input order; piece time = first value); a final
  ordered merge writes `pieces.csv.gz` (deterministic for any K) and a
  `manifest.json` with a counts-only report (malformed rows by reason,
  sentinels, out-of-range groupings, empty cycles, repeated value signatures).
- Grouping normalization (IQ-F17): a nest or mold-cavity grouping may carry
  `remap` rules for loggers that report a known offset, e.g.
  `"nest": {"address": "...", "valid": [1, 12], "remap": [{"from": [13, 13], "offset": -12}]}`.
  Source ranges must lie outside `valid` and land inside it, so a rule can
  never move a legitimate value. Remapped pieces get flag `8`, the manifest
  lists the rules (`grouping_remaps`) and counts (`report.grouping_remapped`,
  e.g. `{"nest": {"13→1": n}}`), and the raw value is kept in the
  `nest_raw` / `mold_cavity_raw` columns (`pieces-v2`; `pieces-v1` files
  still load). After editing the mapping, re-run `convert`.
- Output is gzip CSV, not Parquet: the backend stays stdlib-only.
  `pieces_file.read_pieces` validates the manifest and checksum and builds a
  `DimensionalDataset` with `source_type="REAL"` and the machine's reported
  verdicts as NOK basis (no tolerances in such exports).
- The output directory must be outside the repository or under
  `demo-private/`. The backend loads it only when `DEMO_REAL_DATASET_PATH` is
  set and never in production (plan decision D8).
