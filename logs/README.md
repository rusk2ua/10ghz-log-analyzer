# logs/

Drop your own contest logs here. Every script in this project will
auto-detect a `.log` file placed in this folder (or the current directory)
if you run it with no arguments, and every script also accepts an explicit
path to a file in here as its command-line argument.

## What can go in this folder

- **Cabrillo `.log` files** -- the format `arrl_10ghz_cabrillo.py` produces,
  and what all the analysis scripts (`station_report.py`,
  `weekend_analysis.py`, `comprehensive_analysis.py`,
  `directional_visualization.py`, `log_comparison.py`) read directly.
- **Raw QSO `.csv` files** -- an export of your working log (e.g. from
  Google Sheets: File > Download > Comma Separated Values), with columns
  `date, band, sourcegrid, time, call, grid`. Only `arrl_10ghz_cabrillo.py`
  consumes this directly (to build a Cabrillo file); the analysis scripts
  will also read one if you point them at it.

It's normal for `date`, `band`, `sourcegrid`, and `time` to be blank on a
row when they haven't changed since the previous QSO (including two
contacts logged in the same clock minute) -- that's exactly how most people
keep a running log in a spreadsheet, and every script here forward-fills
those blanks automatically. `call` and `grid` should always be filled in on
every row -- a row with a blank call is treated as a non-QSO (e.g. a stray
blank separator line) and dropped rather than forward-filled, since
guessing a call sign from the row above would silently invent a duplicate
contact.

## Sample files

- `sample_qso_log.csv` -- a handful of fictional QSOs in the raw CSV
  format described above, showing the forward-fill pattern in action
  (band changes, a mid-day grid change for a rover, and a day boundary).
- `sample_cabrillo.log` -- the same QSOs already converted to Cabrillo
  format, so you can try the analysis scripts immediately without running
  the converter first.

Try it:

```bash
python arrl_10ghz_cabrillo.py logs/sample_qso_log.csv
python station_report.py logs/sample_cabrillo.log
python comprehensive_analysis.py logs/sample_cabrillo.log
python directional_visualization.py logs/sample_cabrillo.log
```

These sample files are illustrative only -- not real contest data, and
`CLAIMED-SCORE` in `sample_cabrillo.log` is a placeholder, not a computed
score.
