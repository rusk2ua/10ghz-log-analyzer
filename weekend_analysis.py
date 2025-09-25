#!/usr/bin/env python3

import pandas as pd
import requests
from io import StringIO
import math
from datetime import datetime, timedelta
from collections import defaultdict

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

def calculate_bearing(grid1, grid2):
    """Calculate bearing from grid1 to grid2"""
    lat1, lon1 = grid_to_latlon(grid1)
    lat2, lon2 = grid_to_latlon(grid2)
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.atan2(y, x)
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360
    return bearing

def get_direction(bearing):
    """Convert bearing to compass direction"""
    directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 
                 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    idx = round(bearing / 22.5) % 16
    return directions[idx]

def parse_datetime(date_str, time_str):
    """Parse date and time strings into datetime object"""
    try:
        # Handle various date formats
        if '/' in date_str:
            date_parts = date_str.split('/')
            if len(date_parts[2]) == 4:  # MM/DD/YYYY
                date_obj = datetime.strptime(date_str, '%m/%d/%Y')
            else:  # MM/DD/YY
                date_obj = datetime.strptime(date_str, '%m/%d/%y')
        else:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Parse time (HHMM format)
        time_str = str(time_str).zfill(4)
        hour = int(time_str[:2])
        minute = int(time_str[2:])
        
        return date_obj.replace(hour=hour, minute=minute)
    except:
        return None

def categorize_contest_day(dt):
    """Categorize QSO into contest day periods"""
    if dt is None:
        return "Unknown"
    
    # Expanded contest day mapping to include Monday activity
    contest_dates = {
        '2025-08-16': 1,
        '2025-08-17': 2, 
        '2025-08-18': 2,  # Extended to include Monday
        '2025-09-20': 3,
        '2025-09-21': 4,
        '2025-09-22': 4   # Extended to include Monday
    }
    
    # Expanded contest period: all hours on contest dates
    date_key = dt.strftime('%Y-%m-%d')
    day_num = contest_dates.get(date_key)
    
    if day_num:
        return f"{date_key} Day {day_num}"
    else:
        return "Outside Contest Hours"

def get_band_multiplier(band):
    """Get points per km multiplier based on band"""
    band_str = str(band).lower().replace(' ', '')
    if '10ghz' in band_str or '10g' in band_str:
        return 1
    elif '24ghz' in band_str or '24g' in band_str:
        return 2
    elif '47ghz' in band_str or '47g' in band_str:
        return 3
    elif '78ghz' in band_str or '78g' in band_str or '75g' in band_str:
        return 4
    elif '122ghz' in band_str or '122g' in band_str or '123g' in band_str:
        return 5
    else:
        return 1

def calculate_points(distance, band):
    """Calculate contest points for a QSO"""
    distance_km = max(1, math.ceil(distance))
    band_multiplier = get_band_multiplier(band)
    return distance_km * band_multiplier

def normalize_band(band):
    """Normalize band name to standard GHz format"""
    band_str = str(band).strip().lower()
    if 'ghz' in band_str:
        import re
        match = re.search(r'(\d+)', band_str)
        if match:
            number = match.group(1)
            return f"{number} GHz"
    return str(band).strip()

def analyze_weekend_activity(df):
    """Generate detailed weekend analysis"""
    lines = []
    
    # Header
    lines.append("ARRL 10 GHz and Up Contest - Weekend Analysis Report")
    lines.append("=" * 65)
    lines.append("")
    
    # Parse datetime and add analysis columns
    df['datetime'] = df.apply(lambda row: parse_datetime(row['date'], row['time']), axis=1)
    df['contest_day'] = df['datetime'].apply(categorize_contest_day)
    df['distance'] = df.apply(lambda row: calculate_distance(row['sourcegrid'], row['grid']), axis=1)
    df['bearing'] = df.apply(lambda row: calculate_bearing(row['sourcegrid'], row['grid']), axis=1)
    df['direction'] = df['bearing'].apply(get_direction)
    df['hour'] = df['datetime'].apply(lambda x: x.hour if x else None)
    df['band_normalized'] = df['band'].apply(normalize_band)
    df['points'] = df.apply(lambda row: calculate_points(row['distance'], row['band']), axis=1)
    
    # Group by contest days
    contest_days = df[df['contest_day'] != "Unknown"].groupby('contest_day')
    
    for day_name, day_data in contest_days:
        if "Outside Contest Hours" in day_name:
            continue
            
        lines.append(f"CONTEST DAY: {day_name}")
        lines.append("=" * 50)
        lines.append("")
        
        # Basic statistics
        total_qsos = len(day_data)
        unique_calls = day_data['call'].nunique()
        avg_distance = day_data['distance'].mean()
        max_distance = day_data['distance'].max()
        min_distance = day_data['distance'].min()
        
        lines.append(f"Total QSOs: {total_qsos}")
        lines.append(f"Unique Stations: {unique_calls}")
        lines.append(f"Average Distance: {avg_distance:.1f} km")
        lines.append(f"Best DX: {max_distance:.1f} km")
        lines.append(f"Shortest QSO: {min_distance:.1f} km")
        lines.append("")
        
        # Time analysis
        lines.append("HOURLY ACTIVITY BREAKDOWN:")
        lines.append("-" * 30)
        hourly_counts = day_data.groupby('hour').size().sort_index()
        for hour, count in hourly_counts.items():
            if hour is not None:
                lines.append(f"{hour:02d}00-{hour:02d}59 UTC: {count} QSOs")
        
        # Find most/least productive hours
        if len(hourly_counts) > 0:
            best_hour = hourly_counts.idxmax()
            worst_hour = hourly_counts.idxmin()
            lines.append("")
            lines.append(f"Most productive hour: {best_hour:02d}00 UTC ({hourly_counts[best_hour]} QSOs)")
            lines.append(f"Least productive hour: {worst_hour:02d}00 UTC ({hourly_counts[worst_hour]} QSOs)")
        lines.append("")
        
        # Direction analysis
        lines.append("DIRECTIONAL ANALYSIS:")
        lines.append("-" * 25)
        direction_counts = day_data['direction'].value_counts()
        direction_stats = day_data.groupby('direction').agg({
            'distance': ['count', 'mean', 'max'],
            'points': 'sum'
        })
        
        for direction in ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 
                         'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']:
            if direction in direction_stats.index:
                stats = direction_stats.loc[direction]
                qsos = int(stats[('distance', 'count')])
                avg_dist = stats[('distance', 'mean')]
                best_dx = stats[('distance', 'max')]
                points = int(stats[('points', 'sum')])
                lines.append(f"{direction:3s}: {qsos:2d} QSOs, Avg: {avg_dist:5.1f} km, Best: {best_dx:5.1f} km, Points: {points:4d}")
        
        best_direction = direction_stats[('points', 'sum')].idxmax()
        best_points = int(direction_stats.loc[best_direction, ('points', 'sum')])
        lines.append("")
        lines.append(f"Most productive direction: {best_direction} ({best_points} points)")
        lines.append("")
        
        # Band analysis
        lines.append("BAND ACTIVITY:")
        lines.append("-" * 15)
        band_counts = day_data['band_normalized'].value_counts()
        for band, count in band_counts.items():
            band_data = day_data[day_data['band_normalized'] == band]
            avg_dist = band_data['distance'].mean()
            max_dist = band_data['distance'].max()
            lines.append(f"{str(band):10s}: {count:2d} QSOs, Avg: {avg_dist:5.1f} km, Best: {max_dist:5.1f} km")
        lines.append("")
        
        # Operating locations analysis
        lines.append("OPERATING LOCATIONS:")
        lines.append("-" * 20)
        location_counts = day_data['sourcegrid'].value_counts()
        for grid, count in location_counts.items():
            lines.append(f"{grid}: {count} QSOs")
        
        if len(location_counts) > 1:
            lines.append("")
            lines.append(f"Most productive location: {location_counts.index[0]} ({location_counts.iloc[0]} QSOs)")
        lines.append("")
        
        # Highlights and lowlights
        lines.append("HIGHLIGHTS:")
        lines.append("-" * 12)
        
        # Best DX
        best_dx_qso = day_data.loc[day_data['distance'].idxmax()]
        lines.append(f"• Best DX: {best_dx_qso['call']} at {best_dx_qso['distance']:.1f} km on {best_dx_qso['band_normalized']}")
        
        # Most worked station
        most_worked = day_data['call'].value_counts()
        if len(most_worked) > 0:
            lines.append(f"• Most worked station: {most_worked.index[0]} ({most_worked.iloc[0]} QSOs)")
        
        # Unique achievements
        unique_bands = day_data['band_normalized'].nunique()
        lines.append(f"• Bands active: {unique_bands}")
        
        # Time span
        if day_data['datetime'].notna().any():
            start_time = day_data['datetime'].min()
            end_time = day_data['datetime'].max()
            duration = end_time - start_time
            lines.append(f"• Operating period: {start_time.strftime('%H%M')} - {end_time.strftime('%H%M')} UTC ({duration})")
        
        lines.append("")
        lines.append("OBSERVATIONS:")
        lines.append("-" * 14)
        
        # Activity patterns
        if total_qsos > 20:
            lines.append("• High activity day with good propagation conditions")
        elif total_qsos > 10:
            lines.append("• Moderate activity with decent conditions")
        else:
            lines.append("• Limited activity, possibly due to conditions or time constraints")
        
        # Distance patterns
        if avg_distance > 200:
            lines.append("• Excellent long-distance propagation observed")
        elif avg_distance > 100:
            lines.append("• Good propagation for medium-distance contacts")
        else:
            lines.append("• Primarily local/regional contacts")
        
        # Band diversity
        if unique_bands >= 4:
            lines.append("• Excellent multi-band activity across microwave spectrum")
        elif unique_bands >= 2:
            lines.append("• Good multi-band operation")
        else:
            lines.append("• Single-band focus")
        
        lines.append("")
        lines.append("=" * 65)
        lines.append("")
    
    # Overall weekend comparison
    lines.append("WEEKEND COMPARISON SUMMARY")
    lines.append("=" * 30)
    lines.append("")
    
    weekend_summary = df[df['contest_day'] != "Unknown"].groupby('contest_day').agg({
        'call': 'count',
        'call': 'nunique',
        'distance': ['mean', 'max'],
        'band': 'nunique'
    }).round(1)
    
    lines.append("Day\t\t\tQSOs\tUnique\tAvg Dist\tBest DX\tBands")
    lines.append("-" * 65)
    
    for day in weekend_summary.index:
        day_stats = df[df['contest_day'] == day]
        qsos = len(day_stats)
        unique = day_stats['call'].nunique()
        avg_dist = day_stats['distance'].mean()
        best_dx = day_stats['distance'].max()
        bands = day_stats['band_normalized'].nunique()
        
        day_short = day.split()[0][-5:]  # Last 5 chars of date
        lines.append(f"{day_short}\t\t{qsos}\t{unique}\t{avg_dist:.1f}\t{best_dx:.1f}\t{bands}")
    
    return '\n'.join(lines)

def parse_cabrillo_file(filename):
    """Parse Cabrillo log file and return DataFrame"""
    qsos = []
    
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('QSO:'):
                # QSO: 10G CW 2025-08-16 1135 K2UA EN81PM KE2AIZ FN12EU
                parts = line.split()
                if len(parts) >= 8:
                    band = parts[1]
                    date = parts[3]
                    time = parts[4]
                    sourcegrid = parts[6]
                    call = parts[7]
                    grid = parts[8] if len(parts) > 8 else ''
                    
                    qsos.append({
                        'date': date,
                        'band': band,
                        'sourcegrid': sourcegrid,
                        'time': time,
                        'call': call,
                        'grid': grid
                    })
    
    return pd.DataFrame(qsos)

def get_data_source():
    """Determine data source and load data"""
    import sys
    import os
    
    # Check for command line argument
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        if os.path.exists(filename) and filename.lower().endswith('.log'):
            print(f"Loading Cabrillo file: {filename}")
            return parse_cabrillo_file(filename)
    
    # Check for local Cabrillo file
    cabrillo_files = [f for f in os.listdir('.') if f.endswith('.log')]
    if cabrillo_files:
        filename = cabrillo_files[0]
        print(f"Found Cabrillo file: {filename}")
        return parse_cabrillo_file(filename)
    
    # Default to Google Sheets
    print("Loading from Google Sheets...")
    sheet_url = "https://docs.google.com/spreadsheets/d/1UFbxzWJBpPdUEkfLhNA6csKbHaNypDmGeWpaeP-bQyA/edit?usp=sharing"
    df = get_sheet_data(sheet_url)
    contact_data = df.iloc[2:].copy()
    contact_data.columns = ['date', 'band', 'sourcegrid', 'time', 'call', 'grid']
    return contact_data

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

def main():
    # Get data from appropriate source
    contact_data = get_data_source()
    
    # Forward fill empty cells
    contact_data = contact_data.fillna(method='ffill')
    
    # Clean data
    contact_data = contact_data.dropna(subset=['call'])
    
    # Generate analysis
    analysis = analyze_weekend_activity(contact_data)
    
    # Generate unique filename
    filename = get_output_filename(contact_data, "Weekend_Analysis")
    
    # Save report
    with open(filename, 'w') as f:
        f.write(analysis)
    
    print(f"Weekend analysis saved as: {filename}")
    print(f"Total QSOs analyzed: {len(contact_data)}")

if __name__ == "__main__":
    main()
