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

Current version: **v1.4.0**

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
