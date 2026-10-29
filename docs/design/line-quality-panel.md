# Line quality panel (IQ-F14 / IQ-F15)

Full-screen shop-floor panel for the industrial edition: pieces produced, OK and
NOK for the shift, and alarms that ask for a specific action ("5 NOK in a row:
stop the line"). It replays a stretch of the active dimensional dataset piece by
piece -- the customer's REAL dataset locally, the SIMULATED one on the VPS -- and
a rule engine in the backend decides when each rule fires. Chosen by the user on
2026-10-28 after a prototype with three views (see `decisions.md`).

The panel never acts on production (CLAUDE.md §2): it asks the operator for an
action; acknowledgements and actions in the replay are presentation state only
and are not persisted (they would feed Decision Memory in a real deployment,
§23). Alarms carry engine name, version, rule, value, limit and evidence.

## Rules (engine `line_alarm_engine`, `app/engines/line_alarms/`)

Pieces are evaluated in line order (timestamp, then dataset order). `p_ref` is
the NOK rate of the whole line sequence of the dataset ("historical reference",
returned with the data). Thresholds are relative to `p_ref` so the same rules
work on datasets with very different NOK levels.

| Rule | Priority | Condition (after each piece) | Clears | Asks for |
|---|---|---|---|---|
| R1 NOK streak | 1 (diamond) | trailing consecutive NOK pieces >= `run_limit` (5) | next OK piece | Stop the line, segregate from the first NOK of the streak |
| R2 Nest out of pattern | 2 (triangle) | per nest: NOK rate of its last `nest_window` (100) pieces >= `nest_factor` (3.0) x pooled rate of the other nests' windows, and NOK count >= `nest_min_nok` (25); only with a full window | below the deadband | Check that nest's pins/locator; block the nest if it persists |
| R3 High NOK rate | 2 (triangle) | NOK rate of the last `rate_window` (200) line pieces >= `rate_factor` (2.5) x `p_ref`; full window | below the deadband | Call quality, check the first failing station |
| R4 Mold cavity | 3 (advisory, square) | per mold cavity: NOK rate of its last `cavity_window` (150) pieces >= `cavity_factor` (3.0) x `p_ref`; full window; only if the dataset has mold cavities | below the deadband | Tooling review at the next change, no stop |

**Deadband (ISA-18.2).** An open R2/R3/R4 alarm clears only when its value drops below
`clear_fraction` (0.75) of each limit (R2: ratio and minimum NOK count), so a value
hovering at the threshold does not chatter. Without it, and with the first draft
thresholds (2x over 50 pieces, minimum 10; R3 at 2x), the local real dataset produced
an alarm flood; the deadband and the thresholds above were chosen to stay within a
target of about one priority-2 alarm per hour (R1 is unchanged). Thresholds are still
to be confirmed with the customer.

Each alarm event: `rule`, `priority`, `key` (nest for R2, cavity for R4, null
otherwise), `raised_index` / `raised_ts`, `cleared_index` / `cleared_ts` (null if
still active at the end of the data), `evidence_from_index` / `_ts` (R1: first NOK
of the streak; R2/R3/R4: first piece of the window that triggered), `value` (at
raise: streak length / ratio / rate), `peak` (max value while active; for R1 the
final streak length), `limit`, `nests` (R1: nest of each streak piece up to the
raise, in order, repeats included), `station` (key of the first failing station of the raising piece, if the
dataset has stations).

Per-piece rule state (after processing the piece): `run`, `rate` (R3 window,
null until full), `nest_ratio` + `nest_ratio_nest` (highest ratio among nests
with full windows), `cavity_rate` + `cavity_worst` (highest rate among cavities
with full windows; null without mold cavities).

## API (`/api/v1/line-panel`, industrial edition, `measurement.measurement_result:read`)

Datasets: `demo-synthetic-dimensional` (machine filter, default `INY-01`) and
`real-dimensional` (local only, D8; machine ignored). Anything else: 404.

### `GET /line-panel/moments?dataset=&machine=`

Notable moments of the whole sequence, for the presenter's buttons:

```json
{
  "dataset": "real-dimensional", "dataset_name": "...", "provenance": "REAL",
  "utc_offset_minutes": -300, "start_ts": 0, "end_ts": 0, "pieces": 0,
  "reference_nok_rate": 0.1, "engine_name": "line_alarm_engine", "engine_version": "v1-experimental",
  "moments": [
    {"key": "stop-1", "kind": "stop", "rule": "R1", "key_group": null,
     "raised_ts": 0, "peak": 12, "label": "Racha de 12 NOK consecutivas", "replay_start_ts": 0}
  ]
}
```

`kind`: `stop` (R1 events, longest streak first, max 8), `attention` (R2 and R3
events by peak, max 6), `normal` (stretches of >= 600 line pieces -- REAL -- or
>= 120 -- SIMULATED -- with no priority 1/2 alarm active, longest first, max 4;
`raised_ts` = stretch start, `peak` = its length in pieces). `replay_start_ts` is
the timestamp of the piece 150 pieces (SIMULATED: 36) before the event, or the
stretch start + 10 % for `normal`, clamped to the data.

### `GET /line-panel/replay?dataset=&machine=&start=<epoch s>&minutes=<5..240, default 60>`

Window `[start, start + minutes)` plus `lead` pieces before it (up to 600) so
the strips and windows are full when the replay starts. All per-piece arrays have
the same length; index 0 is the first lead piece. `t` is seconds relative to
`window.start_ts` (negative for lead pieces).

```json
{
  "engine_name": "line_alarm_engine", "engine_version": "v1-experimental",
  "dataset": "...", "dataset_name": "...", "provenance": "REAL|SIMULATED", "nok_basis": "reported|spec",
  "utc_offset_minutes": -300, "machine": null,
  "line": {"nests": [1, 2], "mold_cavities": 32, "stations": [{"key": "pinpos", "name": "..."}]},
  "rules": {"run_limit": 5, "nest_window": 100, "nest_factor": 3.0, "nest_min_nok": 25,
            "rate_window": 200, "rate_factor": 2.5, "rate_limit": 0.25,
            "cavity_window": 150, "cavity_factor": 3.0, "cavity_limit": 0.3,
            "reference_nok_rate": 0.1, "clear_fraction": 0.75,
            "texts": {"R1": "...", "R2": "...", "R3": "...", "R4": "..."}},
  "window": {"start_ts": 0, "end_ts": 0}, "lead": 600,
  "shifts": [{"label": "06:00–14:00", "start_ts": 0, "end_ts": 0}],
  "baseline": {"pieces": 0, "nok": 0, "by_nest": [[1, 0, 0]], "by_cavity": [[1, 0, 0]],
               "by_station": [["pinpos", 0]], "hours": [[0, 0, 0]]},
  "pieces": {"t": [], "nest": [], "cavity": [], "nok": [], "station": []},
  "state": {"run": [], "rate": [], "nest_ratio": [], "nest_ratio_nest": [], "cavity_rate": [], "cavity_worst": []},
  "alarms": [{"id": "R1::1234", "rule": "R1", "priority": 1, "key": null,
              "raised_index": 0, "raised_ts": 0, "cleared_index": null, "cleared_ts": null,
              "evidence_from_index": 0, "evidence_from_ts": 0,
              "value": 5, "peak": 12, "limit": 5, "nests": [3, 4, 5, 6, 7], "station": "pinpos"}]
}
```

- `station` per piece: index into `line.stations` of its first failing station, `-1` if none.
  `cavity` per piece: mold cavity or null.
- Shifts are 8 h blocks in plant time starting 06:00 (demo assumption, stated in the UI).
  `shifts` lists every shift overlapping `[first lead piece, window end]`; `baseline` holds the
  counts of the shift that contains the first lead piece, from its start up to (not including)
  that piece (`by_nest` / `by_cavity`: `[group, pieces, nok]`; `by_station`: `[key, nok]` by first
  failing station; `hours`: `[hour_start_ts, pieces, nok]`). The client adds the replayed pieces
  and resets at each shift start.
- `alarms`: every event active at some point of the returned pieces; indices are relative to the
  arrays and may be negative (raised before the first lead piece); `cleared_index` may be null.
- `peak` and `cleared_*` are hindsight from the replay; the UI labels them as such.
- 422 for `minutes` out of range, `start` outside the data, or an unknown machine.

## Frontend (`features/line-panel/`, route `/demo/industrial-quality/panel-linea`)

Full-screen route outside the workbench chrome (ISA-101 grays, `.wb-root`
tokens), opened from the project tree, the View menu and the demo home. Three
views share one replay state: **A Andon** (status band, four KPI tiles, last 60
pieces, streak meter, required action), **B Process map** (KPIs, NOK by nest,
mold cavity grid, first failing station, NOK by hour, alarms with steps,
advisories, shift log) and **C Guided response** (distance to each rule when
calm; when an alarm is active the screen becomes the case: what/where/since,
pieces to contain, evidence, timeline, four steps, one-touch actions,
escalation countdown).

Commands: `R` acknowledge, `A` register action (1-4), `F` full screen; views
`1/2/3`. Presenter buttons `N` Normal / `W` Atención / `S` Paro jump the replay to
the next real moment of that kind (`moments`), `Espacio` pause, `V` speed (x1,
x5, x20). "Line stopped" pauses the replay; "Cause corrected - resume" resumes it.
Color only marks what needs action: a single NOK piece is dark neutral, red only
inside a streak that asked to stop; priority is coded by shape; symbols blink
only while unacknowledged.
