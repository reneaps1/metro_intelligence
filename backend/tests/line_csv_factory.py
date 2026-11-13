"""Synthetic station exports in the line file format (ADR-004).

Same structure as a real export (`;`, latin-1, CRLF, one header row,
`YYYYMMDD-HH:MM:SS` local timestamps, German machine column names) with
fictitious piece ids and values. Never copy real rows here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.ingest.config import IngestConfig, parse_config

TOTAL = "Gesamtergebnis [true..iO | false..NiO]"
LEN_CODES = "[4..iO | 2..kürzer | 1..länger]"
TF = "[true..iO | false..NiO]"
STATION_PINS = 9  # the export always has 9 positions; the test product has 8


def make_config(pins: int = 8, in_scope: tuple[int, ...] = (2, 3)) -> IngestConfig:
    return parse_config(
        {
            "plant": {
                "organization": {"code": "MI-DEMO-ORG", "name": "Demo org"},
                "site": {"code": "MI-DEMO-SITE", "name": "Demo site"},
                "area": {"code": "MI-DEMO-AREA", "name": "Demo area"},
                "line": {"code": "MI-DEMO-LINE-01", "name": "Demo line"},
                "cell": {"code": "MI-DEMO-CELL", "name": "Demo cell"},
                "timezone": "America/Mexico_City",
            },
            "product": {
                "family": {"code": "MI-DEMO-FAM", "name": "Demo family"},
                "part_number": {"code": "MI-DEMO-2001", "name": "Demo housing"},
                "pins": pins,
            },
            "recipes": {"in_scope": list(in_scope)},
            "stations": [
                {
                    "sequence": 1,
                    "code": "ET1",
                    "name": "Electrical test 1",
                    "kind": "electrical",
                    "folder": "01_et1",
                    "file_prefix": "Log_ET1_",
                    "programs": [21],
                },
                {
                    "sequence": 2,
                    "code": "LEN-PCB",
                    "name": "Pin length PCB",
                    "kind": "pin_length",
                    "side": "pcb",
                    "folder": "03_len_pcb",
                    "file_prefix": "Log_LEN_PCB_",
                },
                {
                    "sequence": 3,
                    "code": "LEN-CON",
                    "name": "Pin length connector",
                    "kind": "pin_length",
                    "side": "connector",
                    "folder": "04_len_con",
                    "file_prefix": "Log_LEN_CON_",
                },
                {
                    "sequence": 4,
                    "code": "POS-PCB",
                    "name": "Pin position PCB",
                    "kind": "pin_position",
                    "side": "pcb",
                    "folder": "05_pos_pcb",
                    "file_prefix": "Log_POS_PCB_",
                    "programs": [2],
                },
                {
                    "sequence": 5,
                    "code": "POS-CON",
                    "name": "Pin position connector",
                    "kind": "pin_position",
                    "side": "connector",
                    "folder": "06_pos_con",
                    "file_prefix": "Log_POS_CON_",
                    "programs": [2],
                },
                {
                    "sequence": 6,
                    "code": "TYPE",
                    "name": "Type check",
                    "kind": "type_check",
                    "folder": "07_type",
                    "file_prefix": "Log_TYPE_",
                },
            ],
        }
    )


def _stamp(day: str, seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{day.replace('-', '')}-{h:02d}:{m:02d}:{s:02d}"


def _bool(value: bool) -> str:
    return "True" if value else "False"


@dataclass
class Piece:
    serial: str
    recipe: int
    nest: int = 1
    second: int = 0
    length_pcb: float = 9.85
    length_con: float = 5.45
    pos_pcb: float = 0.10
    pos_con: float = 0.08
    machine_ok: bool = True


@dataclass
class LineFiles:
    """Builds one day of files for every station of `test_config()`."""

    day: str = "2026-03-02"
    pieces: list[Piece] = field(default_factory=list)
    extra_rows: dict[str, list[list[str]]] = field(default_factory=dict)

    def program_for_station(self, piece: Piece) -> int:
        return 1 if piece.recipe == 1 else 2

    def write(self, root: Path) -> Path:
        self._write(root, "07_type", "Log_TYPE_", self._type_rows())
        self._write(root, "03_len_pcb", "Log_LEN_PCB_", self._length_rows("pcb"))
        self._write(root, "04_len_con", "Log_LEN_CON_", self._length_rows("con"))
        self._write(root, "05_pos_pcb", "Log_POS_PCB_", self._pos_pcb_rows())
        self._write(root, "06_pos_con", "Log_POS_CON_", self._pos_con_rows())
        self._write(root, "01_et1", "Log_ET1_", self._electrical_rows())
        return root

    def _write(self, root: Path, folder: str, prefix: str, table: tuple[list[str], list[list[str]]]) -> None:
        header, rows = table
        rows = rows + self.extra_rows.get(folder, [])
        target = root / folder
        target.mkdir(parents=True, exist_ok=True)
        lines = [";".join(header)] + [";".join(row) for row in rows]
        (target / f"{prefix}{self.day.replace('-', '.')}.csv").write_bytes(
            ("\r\n".join(lines) + "\r\n").encode("latin-1")
        )

    def _type_rows(self) -> tuple[list[str], list[list[str]]]:
        header = ["time stamp", "Ldf.Id", "Kavität", "Programmnummer", TOTAL]
        rows = [
            [_stamp(self.day, p.second + 5), p.serial, str(p.nest), str(p.recipe), _bool(p.machine_ok)]
            for p in self.pieces
        ]
        return header, rows

    def _length_rows(self, side: str) -> tuple[list[str], list[list[str]]]:
        header = [
            "time stamp",
            "Lfd.Id",
            "Kavität",
            TOTAL,
            f"Ergebnis Referenz 1 {TF}",
            f"Ergebnis Ref-MT1 {LEN_CODES}",
            "Messwert Ref-MT1 [mm]",
        ]
        for n in range(1, STATION_PINS + 1):
            header += [f"Ergebnis MT{n} {LEN_CODES}", f"Messwert MT{n} [mm]"]
        rows = []
        for p in self.pieces:
            base = p.length_pcb if side == "pcb" else p.length_con
            row = [
                _stamp(self.day, p.second + 1),
                p.serial,
                str(p.nest),
                _bool(p.machine_ok),
                "True",
                "4",
                "-0.010",
            ]
            for n in range(1, STATION_PINS + 1):
                row += ["0", "0"] if n == STATION_PINS else ["4", f"{base + n * 0.001:.4f}"]
            rows.append(row)
        return header, rows

    def _pos_pcb_rows(self) -> tuple[list[str], list[list[str]]]:
        header = ["time stamp", "Lfd.Id", "Kavität", "Programmnummer", TOTAL]
        for n in range(1, STATION_PINS + 1):
            header += [f"Ergebnis {n} {TF}", f"Taumelkreis {n} [mm]"]
        rows = []
        for p in self.pieces:
            row = [
                _stamp(self.day, p.second + 2),
                p.serial,
                str(p.nest),
                str(self.program_for_station(p)),
                _bool(p.machine_ok),
            ]
            for n in range(1, STATION_PINS + 1):
                row += ["False", "0"] if n == STATION_PINS else [_bool(p.pos_pcb <= 0.35), f"{p.pos_pcb:.3f}"]
            rows.append(row)
        return header, rows

    def _pos_con_rows(self) -> tuple[list[str], list[list[str]]]:
        header = ["time stamp", "Lfd.Id", "Kavität", "Programmnummer", TOTAL]
        for n in range(1, STATION_PINS + 1):
            header += [
                f"Ergebnis {n} X {TF}",
                f"Abweichung {n} X [mm]",
                f"Ergebnis {n} Y {TF}",
                f"Abweichung {n} Y [mm]",
            ]
        rows = []
        for p in self.pieces:
            row = [
                _stamp(self.day, p.second + 3),
                p.serial,
                str(p.nest),
                str(self.program_for_station(p)),
                _bool(p.machine_ok),
            ]
            for n in range(1, STATION_PINS + 1):
                if n == STATION_PINS:
                    row += ["False", "0.175", "False", "0.264"]
                else:
                    ok = _bool(p.pos_con <= 0.40)
                    row += [ok, f"{p.pos_con:.3f}", ok, f"{p.pos_con / 2:.3f}"]
            rows.append(row)
        return header, rows

    def _electrical_rows(self) -> tuple[list[str], list[list[str]]]:
        header = [
            "time stamp",
            "Lfd.Id",
            "Kavität",
            "Programmnummer",
            TOTAL,
            "Anzahl Fehler",
            "iFehlerType",
            "iMessType",
            "iFromPoint",
            "iToPoint",
            "rMesswert1",
            "rMesswert2",
        ]
        rows = []
        for p in self.pieces[:2]:  # the station logs only some pieces
            program = "21" if p.recipe != 1 else "11"
            for pair in ((1, 2), (3, 4)):
                rows.append(
                    [
                        _stamp(self.day, p.second + 4),
                        p.serial,
                        str(p.nest),
                        program,
                        "True",
                        "0",
                        "+0",
                        "+1",
                        f"+{pair[0]}",
                        f"+{pair[1]}",
                        "+8.055121E-1",
                        "+1.000000E+15",
                    ]
                )
        return header, rows


def length_row(day: str, serial: str, value: float) -> list[str]:
    row = [_stamp(day, 900), serial, "1", "True", "True", "4", "0.0"]
    for _n in range(1, STATION_PINS + 1):
        row += ["4", f"{value:.4f}"]
    return row


def raw_row(*cells: Any) -> list[str]:
    return [str(c) for c in cells]
