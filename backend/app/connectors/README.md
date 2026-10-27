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

Next step for full files (not implemented): an offline batch job run by an
operator inside the customer network, reading the file from disk in chunks
with the same `ColumnMapping` (exported from the UI as JSON), streaming rows
through `build_dataset`'s validation and writing either a columnar file
(Parquet) or, once D3 is revisited, persisted measurement runs with a
`cavity_code`. It belongs in a CLI/worker, never in a request handler.
