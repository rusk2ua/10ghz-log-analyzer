# ARRL 10 GHz and Up Contest Log Analyzer

Python script to convert Google Sheets contest logs to Cabrillo format for the ARRL 10 GHz and Up Contest.

## Features

- Converts Google Sheets data to proper Cabrillo format
- Calculates contest scores with distance-based points and band multipliers
- Supports all microwave bands (10 GHz through 300+ GHz)
- Generates both Cabrillo log files and contest summaries
- Handles Maidenhead grid square calculations and distance computations
- Forward-fill functionality for incomplete spreadsheet data

## Version

Current version: **v1.6.1**

## New in v1.6.1
- Fixed the band multipliers for 142 GHz and up. They scored 142 GHz at 6x and 241 GHz and 300 GHz at 10x, but the ARRL 10 GHz and Up rules (section 5.2) give every band from 122 GHz up a multiplier of 5. This changed the actual claimed score in the Cabrillo `CLAIMED-SCORE:` line, the summary, the weekend analysis and the directional plots for any log with QSOs on those bands. Logs on 10 through 122 GHz only are unaffected

## New in v1.6.0
- `directional_visualization.py` has a new `-location-based` (or `--location-based`) switch that generates one polar plot per operating location (6-digit grid) per date, instead of one per contest day. Files are named `{CALLSIGN}_{GRID}_direction_analysis_{YYYY-MM-DD}.png`, e.g. `K2UA_FN32kp_direction_analysis_2026-09-20.png`
  - A grid operated from on more than one date gets a separate plot for each date
  - With the switch, only the location-based plots are generated; without it, the per-contest-day plots are unchanged
  - Grids are written in standard Maidenhead case (`FN32kp`) regardless of how they were entered in the log
  - Each plot is titled with the call sign, grid and date (e.g. "K2UA from FN32kp - 2026-09-20"), and its summary box covers only that location and date
  - QSOs with a missing or invalid operating grid are skipped with a warning; a 4-character operating grid is accepted and used in the filename as-is
- `directional_visualization.py` now uses the call sign from the Cabrillo `CALLSIGN:` header when available, and otherwise prompts for it (CSV and Google Sheets sources don't carry one) instead of naming files `UNKNOWN_...`. If the prompt is left blank or the script runs non-interactively, it falls back to `UNKNOWN`
- `.gitignore` now excludes the new `*_direction_analysis_*.png` output files

## New in v1.5.4
- Fixed `directional_visualization.py` generating no plots ("Generated directional analysis plots for 0 contest days") when the source was a raw QSO CSV or a Google Sheets URL -- pandas read the `time` column as a number (`0930` became `930`, or `1005.0` when the column had blank cells), which the script couldn't parse, so every QSO was silently discarded. `data_source.py` now normalizes `time` to a 4-digit `HHMM` string for every script
- Fixed a bare-number band column (`10`, `24`, ...) being read as `10.0`/`24.0` when the column has blank cells, which the band lookup didn't recognize -- this scored every band at 1x and wrote `10.0` instead of `10G` as the Cabrillo band code
- `directional_visualization.py` no longer crashes with a `TypeError` when a QSO has a missing or invalid grid; it warns and leaves that QSO off the plot
- `directional_visualization.py` now explains why when it can't generate any plots, instead of exiting silently
- Added `requirements.txt` (including `numpy`, which the directional script imports directly)

## New in v1.5.3
- `arrl_10ghz_cabrillo.py` no longer prompts for Operator Category, Power Category, or Mode Category -- this contest only has one option for each (single operator, no power distinction, mixed mode), so asking wasn't a real choice. The interactive prompts are now just Call and Band Category
- Band Category prompt is trimmed to the two choices that actually apply to this contest: `10G` (10 GHz only) and `ALL` (all bands)
- The generated Cabrillo header always includes `CATEGORY-OPERATOR: SINGLE-OP` and `CATEGORY-MODE: MIXED`; the `CATEGORY-POWER:` line is no longer generated at all, since there's no power category in this contest

## New in v1.5.2
- Fixed the summary header hardcoded to "ARRL 10 GHz and Up Contest, 2025" -- it now derives the contest year from the QSO dates in the source log, same as the dynamic contest-date detection already used elsewhere

## New in v1.5.1
- Fixed 78 GHz (and other bands whose Cabrillo code doesn't literally contain their name, e.g. "75G") disappearing from `station_report.py`, `weekend_analysis.py`, `comprehensive_analysis.py`, and `directional_visualization.py` when analyzing a Cabrillo log -- band matching is now a single canonical lookup in `data_source.py` (`normalize_band`/`band_to_cabrillo`/`band_multiplier`) instead of five slightly-different copies scattered across scripts, several of which didn't recognize Cabrillo band codes at all
- Fixed a data-integrity bug where a stray blank row in a raw QSO sheet/CSV (e.g. an accidental empty line) got forward-filled on *every* column, including `call` and `grid` -- silently manufacturing a phantom duplicate QSO identical to the row above. Forward-fill is now scoped to `date`/`band`/`sourcegrid`/`time` only; a row with no call sign is dropped, never invented
- `time` is now forward-filled like `date`/`band`/`sourcegrid` (two QSOs logged in the same clock minute are commonly left blank on the second row) -- previously this produced a malformed `0nan` timestamp in the generated Cabrillo file
- `logs/README.md` and `data_source.py`'s docstrings updated to reflect the corrected forward-fill rules

## New in v1.5.0
- Added a `logs/` folder for local contest logs, with sample files (`sample_qso_log.csv` and `sample_cabrillo.log`) so a fresh clone has something to run immediately
- Every script now accepts a single `source` command-line argument (2-4 for `log_comparison.py`), which can be a local Cabrillo `.log` file, a local raw QSO `.csv` file, or a Google Sheets share URL -- `arrl_10ghz_cabrillo.py` previously had no CLI argument at all
- Auto-detection (when no argument is given) now checks `logs/` in addition to the current directory
- Added a shared `data_source.py` module so all six scripts load data the same way instead of each duplicating the same functions
- Added `--help` to every script (via `argparse`)

## New in v1.4.1
- Added detailed documentation for directional visualization script and its polar plot output

## New in v1.4.0
- Removed hardcoded callsign from output filenames; callsign is now extracted from Cabrillo file header or QSO lines
- Removed hardcoded contest year; contest dates are now determined dynamically from log data
- Added matplotlib as an explicit dependency for directional analysis
- Fixed deprecated pandas `fillna(method='ffill')` calls
- Removed dead code in Cabrillo generator

## New in v1.3.0
- Added multi-log comparison functionality (up to 4 logs)
- Full Cabrillo file support for all analysis scripts
- Unique filename generation based on callsign and contest date
- Fixed weekend analysis day numbering
- Comprehensive comparison metrics and performance insights

## New in v1.2.1
- Updated Cabrillo date format to yyyy-mm-dd standard

## New in v1.2
- Added comprehensive station activity analysis
- Added detailed weekend-by-weekend breakdown
- Added directional and time-based analysis
- Added bearing calculations and propagation analysis
- Multiple analysis scripts for different perspectives
- Updated Cabrillo date format to yyyy-mm-dd standard

## Usage

1. Set up virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Drop your own log into `logs/` (or point at a Google Sheets URL -- see
   [Data Sources](#data-sources) below), then run the converter:
```bash
python arrl_10ghz_cabrillo.py logs/your_log.csv
```

3. Follow the prompts to enter contest information

Try it immediately with the bundled sample data (no setup required):
```bash
python arrl_10ghz_cabrillo.py logs/sample_qso_log.csv
```

## Data Sources

Every script in this project takes a single optional `source` argument
(`log_comparison.py` takes 2-4). It can be any of:

- **A local Cabrillo `.log` file** -- e.g. `logs/sample_cabrillo.log`, or a
  file produced by `arrl_10ghz_cabrillo.py`.
- **A local raw QSO `.csv` file** -- e.g. `logs/sample_qso_log.csv`, shaped
  like a Google Sheets export: columns `date, band, sourcegrid, time, call,
  grid`. It's normal for `date`, `band`, and `sourcegrid` to be blank on a
  row when they haven't changed since the previous QSO -- every script
  forward-fills those automatically.
- **A Google Sheets share URL** -- fetched live and forward-filled the same
  way.

If you omit the argument, each script auto-detects a `.log` file (checking
the current directory, then `logs/`), and falls back to this project's
default Google Sheets URL if nothing is found. Run any script with `--help`
for the exact usage text.

See `logs/README.md` for more on the sample files and the expected CSV
format.

## Output Files

- `{CALLSIGN}_ARRL_10GHZ.log` - Cabrillo format contest log
- `{CALLSIGN}_ARRL_10GHZ_Summary.txt` - Contest summary with scoring breakdown
- `{CALLSIGN}_Station_Report_{DATE}.txt` - Station-by-station activity analysis
- `{CALLSIGN}_Weekend_Analysis_{DATE}.txt` - Weekend-by-weekend breakdown
- `{CALLSIGN}_Comprehensive_Analysis_{DATE}.txt` - Complete contest analysis
- `Log_Comparison_{CALLS}.txt` - Multi-log comparison analysis
- `{CALLSIGN}_Directional_Analysis_Day_{N}_{DATE}.png` - Polar plot of directional activity per contest day
- `{CALLSIGN}_{GRID}_direction_analysis_{YYYY-MM-DD}.png` - Polar plot of directional activity per operating location per date (with `-location-based`)

## Analysis Scripts

### Individual Log Analysis
```bash
# Auto-detect a .log file (current directory, then logs/), or fall back to
# the default Google Sheets URL
python station_report.py
python weekend_analysis.py
python comprehensive_analysis.py

# Analyze a specific Cabrillo file, raw QSO CSV, or Google Sheets URL
python station_report.py logs/mylog.log
python weekend_analysis.py logs/mylog.log
python comprehensive_analysis.py logs/mylog.log

# Try it with the bundled sample data
python station_report.py logs/sample_cabrillo.log
```

### Multi-Log Comparison
```bash
# Compare 2-4 sources -- Cabrillo files, raw QSO CSVs, or Google Sheets URLs
python log_comparison.py source1 source2 [source3] [source4]

# Examples
python log_comparison.py logs/k2ua_2025.log logs/k2ua_2026.log
python log_comparison.py station1.log station2.log station3.log
```

### Directional Visualization
```bash
# Generate polar plots from a Cabrillo file, raw QSO CSV, or Google Sheets URL
python directional_visualization.py logs/mylog.log

# Or let it auto-detect a .log file (current directory, then logs/)
python directional_visualization.py

# One plot per operating location (6-digit grid) per date instead of per contest day
python directional_visualization.py logs/mylog.log -location-based
```

If the source is a CSV or Google Sheets URL (which don't include your call sign),
the script prompts for your call sign so it can name the output files. Cabrillo
logs use the `CALLSIGN:` header automatically.

This script produces polar (radar) plots that visualize your contest activity by compass bearing and band. One PNG image is generated per contest day, saved as `{CALLSIGN}_Directional_Analysis_Day_{N}_{DATE}.png`.

Each plot shows:

- **Radial axes** representing the 16 compass directions (N, NNE, NE, … NNW) from your operating location.
- **One trace per band** (color-coded) showing total contest points earned in each direction. This makes it easy to see which bearings were most productive and on which bands.
- **Filled regions** beneath each trace to highlight directional concentration at a glance.
- **A legend** listing each active band along with its total points for the day.
- **Summary statistics** in the lower-left corner: total QSOs, total points, and best DX distance for the day.

#### Location-based mode (`-location-based`)

Rovers and multi-site operators can instead get one plot per operating location per date. Each plot
covers only the QSOs made from that 6-digit grid (the `sourcegrid` column, or the sent grid in a
Cabrillo QSO line) on that date. If you operated from the same grid on two different dates, you get
two plots. Files are named `{CALLSIGN}_{GRID}_direction_analysis_{YYYY-MM-DD}.png` with the grid in
standard Maidenhead case, e.g. `K2UA_FN32kp_direction_analysis_2026-09-20.png`. In this mode the
per-contest-day plots are not generated. QSOs with a missing or invalid operating grid are skipped
with a warning; a 4-character operating grid is used in the filename as-is.

The plots are useful for:

- Identifying your strongest propagation paths and any directional gaps in activity.
- Comparing band-by-band performance across different bearings (e.g., did 24 GHz work better to the south while 10 GHz was stronger to the east?).
- Evaluating multi-day strategy — generating one plot per contest day lets you see how conditions or operating locations shifted between weekends.
- Planning future contests by understanding which directions yield the most contacts and distance from a given grid.

## Scoring Rules

- Distance points: Ceiling of km distance × band multiplier
- Band multipliers (ARRL rules 5.2): 10 GHz=1x, 24 GHz=2x, 47 GHz=3x, 75 GHz (78 GHz)=4x, 122 GHz and up (122, 142, 241, 300 GHz)=5x
- Bonus points: 100 points per unique callsign per band
- Minimum distance: 1 km per QSO

## Requirements

- Python 3.x
- pandas
- numpy (installed with pandas; also used directly by the directional visualization)
- requests
- matplotlib (for directional analysis visualization)

Install everything with `pip install -r requirements.txt`.
