# ARRL 10 GHz and Up Contest Logger

Python script to convert Google Sheets contest logs to Cabrillo format for the ARRL 10 GHz and Up Contest.

## Features

- Converts Google Sheets data to proper Cabrillo format
- Calculates contest scores with distance-based points and band multipliers
- Supports all microwave bands (10 GHz through 300+ GHz)
- Generates both Cabrillo log files and contest summaries
- Handles Maidenhead grid square calculations and distance computations
- Forward-fill functionality for incomplete spreadsheet data

## Version

Current version: **v1.4.1**

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
pip install pandas requests matplotlib
```

2. Run the script:
```bash
python arrl_10ghz_cabrillo.py
```

3. Follow the prompts to enter contest information

## Output Files

- `{CALLSIGN}_ARRL_10GHZ.log` - Cabrillo format contest log
- `{CALLSIGN}_ARRL_10GHZ_Summary.txt` - Contest summary with scoring breakdown
- `{CALLSIGN}_Station_Report_{DATE}.txt` - Station-by-station activity analysis
- `{CALLSIGN}_Weekend_Analysis_{DATE}.txt` - Weekend-by-weekend breakdown
- `{CALLSIGN}_Comprehensive_Analysis_{DATE}.txt` - Complete contest analysis
- `Log_Comparison_{CALLS}.txt` - Multi-log comparison analysis
- `{CALLSIGN}_Directional_Analysis_Day_{N}_{DATE}.png` - Polar plot of directional activity per contest day

## Analysis Scripts

### Individual Log Analysis
```bash
# Analyze from Google Sheets (default)
python station_report.py
python weekend_analysis.py
python comprehensive_analysis.py

# Analyze from Cabrillo file
python station_report.py logfile.log
python weekend_analysis.py logfile.log
python comprehensive_analysis.py logfile.log
```

### Multi-Log Comparison
```bash
# Compare 2-4 log files
python log_comparison.py log1.log log2.log [log3.log] [log4.log]

# Examples
python log_comparison.py k2ua_2022.log k2ua_2023.log
python log_comparison.py station1.log station2.log station3.log
```

### Directional Visualization
```bash
# Generate polar plots from a Cabrillo file
python directional_visualization.py logfile.log

# Or let it auto-detect a .log file in the current directory
python directional_visualization.py
```

This script produces polar (radar) plots that visualize your contest activity by compass bearing and band. One PNG image is generated per contest day, saved as `{CALLSIGN}_Directional_Analysis_Day_{N}_{DATE}.png`.

Each plot shows:

- **Radial axes** representing the 16 compass directions (N, NNE, NE, … NNW) from your operating location.
- **One trace per band** (color-coded) showing total contest points earned in each direction. This makes it easy to see which bearings were most productive and on which bands.
- **Filled regions** beneath each trace to highlight directional concentration at a glance.
- **A legend** listing each active band along with its total points for the day.
- **Summary statistics** in the lower-left corner: total QSOs, total points, and best DX distance for the day.

The plots are useful for:

- Identifying your strongest propagation paths and any directional gaps in activity.
- Comparing band-by-band performance across different bearings (e.g., did 24 GHz work better to the south while 10 GHz was stronger to the east?).
- Evaluating multi-day strategy — generating one plot per contest day lets you see how conditions or operating locations shifted between weekends.
- Planning future contests by understanding which directions yield the most contacts and distance from a given grid.

## Scoring Rules

- Distance points: Ceiling of km distance × band multiplier
- Band multipliers: 10 GHz=1x, 24 GHz=2x, 47 GHz=3x, 78 GHz=4x, 122 GHz=5x
- Bonus points: 100 points per unique callsign per band
- Minimum distance: 1 km per QSO

## Requirements

- Python 3.x
- pandas
- requests
- matplotlib (for directional analysis visualization)
