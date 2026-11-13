# seed/sample_files — fictitious import fixtures

Everything here is **SIMULATED** (CLAUDE.md §7/§20) and checked by
`tests/seed_validation/test_confidentiality.py`. Never add real customer files.

| File | Generator | Used by |
|---|---|---|
| `mi_demo_100*_import_batch.csv`, `mi_demo_import_batch.xlsx` | `seed/scripts/generate_sample_files.py` | `/api/v1/imports` (catalog wide format, measurement history) |
| `mi_demo_dimensional_long.csv`, `mi_demo_dimensional_wide.csv` | `seed/scripts/generate_dimensional_samples.py` | IQ-F6 column-mapping import (industrial edition) |

Both generators are deterministic (fixed seed and dates): regenerating gives
byte-identical files.

## IQ-F6 dimensional samples

**Long** (`;`, decimal comma, D/M/Y date + separate time): one row per
measurement, limits per row, source `Resultado` OK/NOK. 960 pieces (60 cycles ×
16 nests, 2 presses) × 6 characteristics. The suggested mapping is complete:
load it and press *Validar y analizar*. Expected: 5 rows in quarantine (one per
reason: non-numeric value, empty value, impossible date, different unit,
duplicate piece + variable). Spec NOK ≈ 2.2 %; nest 11 reaches 25 % NOK
(relative risk ≈ 37×) through `Diametro_Pin`; press PRS-B drifts on
`Longitud_Terminal` after day 2. The source verdict uses a tighter
in-house flatness limit (0.040 mm) than the file's LSE (0.050 mm), so
"reported by source" and "recalculated by spec" differ on purpose (source
5.0 % NOK; 27 pieces NOK only for the source).

**Wide** (`,`, ISO 8601 with offset): one row per piece, 1 200 pieces (150
cycles × 8 cavities `CAV-0n`), `PASS`/`FAIL` column, **no limits in the file**.
Without typing limits there is no spec NOK and no Cp/Cpk. To get them, type
these in the mapping screen:

| Variable | LIE | LSE | Unit |
|---|---|---|---|
| PinHeight | 2.470 | 2.530 | mm |
| PinPitch | 1.258 | 1.282 | mm |
| BodyLength | 21.940 | 22.060 | mm |
| WallThickness | 0.770 | 0.830 | mm |
| Warp | — | 0.070 | mm |

Expected: 3 rows in quarantine (non-numeric value, unparseable date, row
without values). The second material lot (`LOT-M2`) runs thin on
`WallThickness` and drives most of the NOK (~11 %, spread over all
cavities); cavity 3 runs high on `PinHeight` and only stands out when the
analysis is filtered to that variable — a useful "filter before blaming a
nest" moment.
