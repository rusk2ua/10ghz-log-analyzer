#!/usr/bin/env python3

import pandas as pd
import requests
from io import StringIO
import math

def get_sheet_data(sheet_url):
    """Convert Google Sheets URL to CSV export URL and fetch data"""
    sheet_id = sheet_url.split('/d/')[1].split('/')[0]
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    response = requests.get(csv_url)
    return pd.read_csv(StringIO(response.text))

def grid_to_latlon(grid):
    """Convert 6-digit Maidenhead grid to lat/lon"""
    grid = str(grid).upper().strip()
    if len(grid) < 4:
        return 0.0, 0.0
    if len(grid) < 6:
        grid = grid + 'AA'[:6-len(grid)]
    grid = grid[:6]
    
    try:
        lon = (ord(grid[0]) - ord('A')) * 20 - 180
        lat = (ord(grid[1]) - ord('A')) * 10 - 90
        lon += (ord(grid[2]) - ord('0')) * 2
        lat += (ord(grid[3]) - ord('0')) * 1
        lon += (ord(grid[4]) - ord('A')) * 5/60
        lat += (ord(grid[5]) - ord('A')) * 2.5/60
        return lat + 1.25/60, lon + 2.5/60
    except (ValueError, IndexError):
        return 0.0, 0.0

def calculate_distance(grid1, grid2):
    """Calculate distance between two grids in km"""
    lat1, lon1 = grid_to_latlon(grid1)
    lat2, lon2 = grid_to_latlon(grid2)
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return 6371 * 2 * math.asin(math.sqrt(a))

def normalize_band(band):
    """Normalize band name to standard format"""
    band_str = str(band).strip().lower()
    if 'ghz' in band_str:
        import re
        match = re.search(r'(\d+)', band_str)
        if match:
            number = match.group(1)
            return f"{number} GHz"
    return str(band).strip()

def generate_station_report(df):
    """Generate detailed station report"""
    lines = []
    
    # Header
    lines.append("ARRL 10 GHz and Up Contest - Station Activity Report")
    lines.append("=" * 60)
    lines.append("")
    
    # Collect station data
    station_data = {}
    
    for _, row in df.iterrows():
        call = row['call'].upper()
        band = normalize_band(row['band'])
        distance = calculate_distance(row['sourcegrid'], row['grid'])
        
        if call not in station_data:
            station_data[call] = {
                'total_qsos': 0,
                'bands': {},
                'best_dx_overall': 0
            }
        
        station_data[call]['total_qsos'] += 1
        station_data[call]['best_dx_overall'] = max(station_data[call]['best_dx_overall'], distance)
        
        if band not in station_data[call]['bands']:
            station_data[call]['bands'][band] = {
                'count': 0,
                'best_dx': 0
            }
        
        station_data[call]['bands'][band]['count'] += 1
        station_data[call]['bands'][band]['best_dx'] = max(station_data[call]['bands'][band]['best_dx'], distance)
    
    # Sort stations by total QSOs (most worked first)
    sorted_stations = sorted(station_data.items(), key=lambda x: x[1]['total_qsos'], reverse=True)
    
    # Most Worked Stations Summary
    lines.append("MOST WORKED STATIONS (Top 20)")
    lines.append("-" * 40)
    lines.append("Call\t\tTotal QSOs\tBest DX (km)")
    lines.append("-" * 40)
    
    for call, data in sorted_stations[:20]:
        lines.append(f"{call:<12}\t{data['total_qsos']}\t\t{data['best_dx_overall']:.0f}")
    
    lines.append("")
    lines.append("")
    
    # Detailed breakdown by band
    lines.append("DETAILED STATION BREAKDOWN BY BAND")
    lines.append("=" * 60)
    lines.append("")
    
    band_order = ['10 GHz', '24 GHz', '47 GHz', '78 GHz', '122 GHz', '241 GHz', '300 GHz']
    
    for call, data in sorted_stations:
        lines.append(f"Station: {call}")
        lines.append(f"Total QSOs: {data['total_qsos']}, Best DX: {data['best_dx_overall']:.0f} km")
        lines.append("")
        
        # Show band breakdown
        lines.append("Band\t\tQSOs\tBest DX (km)")
        lines.append("-" * 35)
        
        for band_name in band_order:
            # Find matching band in data
            matching_band = None
            for band in data['bands'].keys():
                if band_name.split()[0].lower() in str(band).lower():
                    matching_band = band
                    break
            
            if matching_band:
                band_info = data['bands'][matching_band]
                lines.append(f"{band_name}\t\t{band_info['count']}\t{band_info['best_dx']:.0f}")
        
        lines.append("")
        lines.append("-" * 60)
        lines.append("")
    
    # Band activity summary
    lines.append("")
    lines.append("BAND ACTIVITY SUMMARY")
    lines.append("=" * 30)
    lines.append("")
    
    band_summary = {}
    for call, data in station_data.items():
        for band, info in data['bands'].items():
            if band not in band_summary:
                band_summary[band] = {
                    'unique_stations': set(),
                    'total_qsos': 0,
                    'best_dx': 0
                }
            band_summary[band]['unique_stations'].add(call)
            band_summary[band]['total_qsos'] += info['count']
            band_summary[band]['best_dx'] = max(band_summary[band]['best_dx'], info['best_dx'])
    
    lines.append("Band\t\tUnique Stations\tTotal QSOs\tBest DX (km)")
    lines.append("-" * 55)
    
    for band_name in band_order:
        matching_band = None
        for band in band_summary.keys():
            if band_name.split()[0].lower() in str(band).lower():
                matching_band = band
                break
        
        if matching_band:
            summary = band_summary[matching_band]
            lines.append(f"{band_name}\t\t{len(summary['unique_stations'])}\t\t{summary['total_qsos']}\t\t{summary['best_dx']:.0f}")
    
    return '\n'.join(lines)

def parse_cabrillo_file(filename):
    """Parse Cabrillo log file and return DataFrame"""
    qsos = []
    
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('QSO:'):
                parts = line.split()
                if len(parts) >= 8:
                    qsos.append({
                        'date': parts[3],
                        'band': parts[1],
                        'sourcegrid': parts[6],
                        'time': parts[4],
                        'call': parts[7],
                        'grid': parts[8] if len(parts) > 8 else ''
                    })
    return pd.DataFrame(qsos)

def get_data_source():
    """Determine data source and load data"""
    import sys
    import os
    
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        if os.path.exists(filename) and filename.lower().endswith('.log'):
            return parse_cabrillo_file(filename)
    
    cabrillo_files = [f for f in os.listdir('.') if f.endswith('.log')]
    if cabrillo_files:
        return parse_cabrillo_file(cabrillo_files[0])
    
    sheet_url = "https://docs.google.com/spreadsheets/d/1UFbxzWJBpPdUEkfLhNA6csKbHaNypDmGeWpaeP-bQyA/edit?usp=sharing"
    df = get_sheet_data(sheet_url)
    contact_data = df.iloc[2:].copy()
    contact_data.columns = ['date', 'band', 'sourcegrid', 'time', 'call', 'grid']
    return contact_data

def main():
    contact_data = get_data_source()
    
    # Forward fill empty cells
    contact_data = contact_data.fillna(method='ffill')
    
    # Clean data
    contact_data = contact_data.dropna(subset=['call'])
    
    # Generate report
    report = generate_station_report(contact_data)
    
    # Generate unique filename
    filename = get_output_filename(contact_data, "Station_Report")
    
    # Save report
    with open(filename, 'w') as f:
        f.write(report)
    
    print(f"Station report saved as: {filename}")
    print(f"Total stations worked: {len(set(contact_data['call'].str.upper()))}")
    print(f"Total QSOs: {len(contact_data)}")

def get_output_filename(contact_data, base_name):
    """Generate unique filename based on callsign and last contest date"""
    dates = contact_data['date'].unique()
    last_date = max(dates)
    callsign = "K2UA"
    
    # Handle different date formats
    if '/' in str(last_date):
        # Convert mm/dd/yyyy to yyyymmdd
        try:
            from datetime import datetime
            date_obj = datetime.strptime(str(last_date), '%m/%d/%Y')
            last_date = date_obj.strftime('%Y%m%d')
        except:
            last_date = str(last_date).replace('/', '')
    else:
        # Handle yyyy-mm-dd format
        last_date = str(last_date).replace('-', '')
    
    return f"{callsign}_{base_name}_{last_date}.txt"

if __name__ == "__main__":
    main()
