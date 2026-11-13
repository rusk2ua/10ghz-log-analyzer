"""Raw QSO CSV headers: the column names people actually use.

A header the loader didn't recognize used to fall back to the legacy Google
Sheets layout, which skips two rows: a CSV with a `my_grid` column silently
lost its first two QSOs.
"""
import subprocess
import sys

import pytest

from data_source import RAW_COLUMNS, CsvHeaderError, load_local_raw_csv

ROWS = ("2026-08-15,10 GHz,FN03CN,1005,VE2ZAZ,FN03HV\n"
        "2026-08-15,10 GHz,FN03CN,1006,VE3FN,FN03HV\n"
        "2026-08-15,10 GHz,FN03CN,1020,W2FU,FN13AD\n")


QSOS = [line.split(",") for line in ROWS.strip().split("\n")]  # in RAW_COLUMNS order


@pytest.mark.parametrize("header", [
    # (name in the file, the column it means), in file order
    [("date", "date"), ("band", "band"), ("sourcegrid", "sourcegrid"),
     ("time", "time"), ("call", "call"), ("grid", "grid")],
    [("date", "date"), ("band", "band"), ("my_grid", "sourcegrid"),
     ("time", "time"), ("call", "call"), ("grid", "grid")],
    [("Date", "date"), ("Band", "band"), ("My Grid", "sourcegrid"),
     ("Time", "time"), ("Callsign", "call"), ("Gridsquare", "grid")],
    [("qso_date", "date"), ("band", "band"), ("home_grid", "sourcegrid"),
     ("qso_time", "time"), ("call", "call"), ("their_grid", "grid")],
    [("call", "call"), ("grid", "grid"), ("station_grid", "sourcegrid"),
     ("time", "time"), ("band", "band"), ("date", "date")],
], ids=["standard", "my_grid", "spaced", "alternates", "reordered"])
def test_every_qso_is_kept_whatever_the_column_names(tmp_path, header):
    lines = [",".join(name for name, _ in header)]
    for qso in QSOS:
        values = dict(zip(RAW_COLUMNS, qso))
        lines.append(",".join(values[col] for _, col in header))
    path = tmp_path / "log.csv"
    path.write_text("\n".join(lines) + "\n")

    df = load_local_raw_csv(str(path))
    assert list(df.columns) == RAW_COLUMNS
    assert list(df["call"]) == ["VE2ZAZ", "VE3FN", "W2FU"]
    assert list(df["sourcegrid"]) == ["FN03CN"] * 3
    assert list(df["grid"]) == ["FN03HV", "FN03HV", "FN13AD"]


def test_a_header_missing_a_column_is_an_error_not_two_lost_qsos(tmp_path):
    path = tmp_path / "log.csv"
    path.write_text("date,band,where_i_was,time,call,grid\n" + ROWS)
    with pytest.raises(CsvHeaderError, match="sourcegrid"):
        load_local_raw_csv(str(path))


def test_the_legacy_sheet_export_still_loads(tmp_path):
    # A direct download of the original sheet: a title row, two more
    # non-QSO rows, then QSOs in fixed column order.
    path = tmp_path / "log.csv"
    path.write_text("ARRL 10 GHz log,,,,,\nDate,Band,Grid,UTC,Call,Their grid\n"
                    "(yyyy-mm-dd),,,,,\n" + ROWS)
    df = load_local_raw_csv(str(path))
    assert list(df["call"]) == ["VE2ZAZ", "VE3FN", "W2FU"]


def test_the_cli_explains_a_bad_header(tmp_path):
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    (tmp_path / "log.csv").write_text("date,band,where_i_was,time,call,grid\n" + ROWS)
    result = subprocess.run([sys.executable, os.path.join(root, "station_report.py"), "log.csv"],
                            cwd=tmp_path, capture_output=True, text=True, input="")
    assert result.returncode == 1
    assert "no column for sourcegrid" in result.stdout
    assert "Traceback" not in result.stderr


def test_a_sheet_export_with_a_partial_title_row_still_loads(tmp_path):
    # A title row that happens to contain "Call" and "Grid": the two rows
    # after it aren't QSOs, so this is the legacy layout, not a bad header.
    path = tmp_path / "log.csv"
    path.write_text("Date,Band,My QTH,UTC,Call,Grid\n"
                    "(yyyy-mm-dd),(GHz),,,(their call),(their grid)\n"
                    ",,,,,\n" + ROWS)
    df = load_local_raw_csv(str(path))
    assert list(df["call"]) == ["VE2ZAZ", "VE3FN", "W2FU"]


def test_a_single_row_is_checked_too(tmp_path):
    # One QSO under a header missing a column: an error naming the column.
    path = tmp_path / "one.csv"
    path.write_text("date,band,where_i_was,time,call,grid\n" + ROWS.split("\n")[0] + "\n")
    with pytest.raises(CsvHeaderError, match="sourcegrid"):
        load_local_raw_csv(str(path))
    # One non-QSO row under a title row: the legacy layout (no QSOs), not an error.
    path.write_text("Date,Band,My QTH,UTC,Call,Grid\n(yyyy-mm-dd),(GHz),,,(their call),(their grid)\n")
    assert len(load_local_raw_csv(str(path))) == 0
