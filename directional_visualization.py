#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
import os
from datetime import datetime, timedelta
import math
from io import StringIO
import requests

def get_sheet_data(sheet_url):
    """Convert Google Sheets URL to CSV export URL and fetch data"""
    sheet_id = sheet_url.split('/d/')[1].split('/')[0]
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    response = requests.get(csv_url)
    return pd.read_csv(StringIO(response.text))

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

def grid_to_latlon(grid):
    """Convert 6-digit Maidenhead grid to lat/lon"""
    grid = str(grid).upper().strip()
    if len(grid) < 4:
        return None, None
    
    lon = (ord(grid[0]) - ord('A')) * 20 - 180
    lat = (ord(grid[1]) - ord('A')) * 10 - 90
    lon += (ord(grid[2]) - ord('0')) * 2
    lat += (ord(grid[3]) - ord('0')) * 1
    
    if len(grid) >= 6:
        lon += (ord(grid[4]) - ord('A')) * (2/24)
        lat += (ord(grid[5]) - ord('A')) * (1/24)
    
    return lat, lon

def calculate_distance(grid1, grid2):
    """Calculate distance between two grids in km"""
    lat1, lon1 = grid_to_latlon(grid1)
    lat2, lon2 = grid_to_latlon(grid2)
    
    if None in [lat1, lon1, lat2, lon2]:
        return 0
    
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

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
        if '/' in date_str:
            date_parts = date_str.split('/')
            if len(date_parts[2]) == 4:
                date_obj = datetime.strptime(date_str, '%m/%d/%Y')
            else:
                date_obj = datetime.strptime(date_str, '%m/%d/%y')
        else:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        
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

def normalize_band(band):
    """Normalize band name to standard GHz format"""
    band_str = str(band).strip().lower()
    if 'g' in band_str:
        import re
        match = re.search(r'(\d+)', band_str)
        if match:
            return f"{match.group(1)} GHz"
    return str(band)

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

def create_polar_plot(day_data, day_name):
    """Create polar plot showing directional analysis by band"""
    # Set up the plot
    fig, ax = plt.subplots(figsize=(12, 10), subplot_kw=dict(projection='polar'))
    
    # Direction mapping to angles (in radians)
    directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 
                 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    angles = np.linspace(0, 2*np.pi, 16, endpoint=False)
    direction_to_angle = dict(zip(directions, angles))
    
    # Get unique bands and assign colors
    bands = sorted(day_data['band_normalized'].unique())
    colors = plt.cm.Set1(np.linspace(0, 1, len(bands)))
    
    # Plot each band
    for i, band in enumerate(bands):
        band_data = day_data[day_data['band_normalized'] == band]
        
        # Calculate points by direction for this band
        direction_points = band_data.groupby('direction')['points'].sum()
        
        # Prepare data for polar plot
        plot_angles = []
        plot_values = []
        
        for direction in directions:
            if direction in direction_points.index:
                plot_angles.append(direction_to_angle[direction])
                plot_values.append(direction_points[direction])
            else:
                plot_angles.append(direction_to_angle[direction])
                plot_values.append(0)
        
        # Close the plot by adding the first point at the end
        plot_angles.append(plot_angles[0])
        plot_values.append(plot_values[0])
        
        # Plot the band
        ax.plot(plot_angles, plot_values, 'o-', linewidth=2, 
               label=f'{band} ({band_data["points"].sum()} pts)', 
               color=colors[i], markersize=6)
        ax.fill(plot_angles, plot_values, alpha=0.1, color=colors[i])
    
    # Customize the plot
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_thetagrids(np.degrees(angles), directions)
    ax.set_title(f'{day_name}\nDirectional Analysis by Band (Points)', 
                pad=20, fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', bbox_to_anchor=(1.1, 1))
    ax.grid(True)
    
    # Add statistics text
    total_qsos = len(day_data)
    total_points = day_data['points'].sum()
    best_dx = day_data['distance'].max()
    
    stats_text = f'Total: {total_qsos} QSOs, {total_points} points\nBest DX: {best_dx:.1f} km'
    plt.figtext(0.02, 0.02, stats_text, fontsize=10, 
               bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
    
    plt.tight_layout()
    return fig

def main():
    # Get data
    contact_data = get_data_source()
    
    # Forward fill empty cells
    contact_data = contact_data.fillna(method='ffill')
    
    # Clean data
    contact_data = contact_data.dropna(subset=['call'])
    
    # Add analysis columns
    contact_data['datetime'] = contact_data.apply(lambda row: parse_datetime(row['date'], row['time']), axis=1)
    contact_data['contest_day'] = contact_data['datetime'].apply(categorize_contest_day)
    contact_data['distance'] = contact_data.apply(lambda row: calculate_distance(row['sourcegrid'], row['grid']), axis=1)
    contact_data['bearing'] = contact_data.apply(lambda row: calculate_bearing(row['sourcegrid'], row['grid']), axis=1)
    contact_data['direction'] = contact_data['bearing'].apply(get_direction)
    contact_data['band_normalized'] = contact_data['band'].apply(normalize_band)
    contact_data['points'] = contact_data.apply(lambda row: calculate_points(row['distance'], row['band']), axis=1)
    
    # Group by contest days - extract just the day number for grouping
    contact_data['day_number'] = contact_data['contest_day'].str.extract(r'Day (\d+)')[0]
    contest_days = contact_data[contact_data['day_number'].notna()].groupby('day_number')
    
    # Get callsign and last date for filename
    callsign = "K2UA"
    last_date = max(contact_data['date'].unique())
    if '/' in str(last_date):
        try:
            from datetime import datetime
            date_obj = datetime.strptime(str(last_date), '%m/%d/%Y')
            date_str = date_obj.strftime('%Y%m%d')
        except:
            date_str = str(last_date).replace('/', '')
    else:
        date_str = str(last_date).replace('-', '')
    
    # Create plots for each day
    for day_num, day_data in contest_days:
        if len(day_data) > 0:
            # Get date range for the day
            dates = sorted(day_data['contest_day'].str.extract(r'(\d{4}-\d{2}-\d{2})')[0].unique())
            if len(dates) == 1:
                day_name = f"{dates[0]} Day {day_num}"
            else:
                day_name = f"{dates[0]} to {dates[-1]} Day {day_num}"
            
            fig = create_polar_plot(day_data, day_name)
            
            # Save the plot with callsign and date
            filename = f"{callsign}_Directional_Analysis_Day_{day_num}_{date_str}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"Saved: {filename}")
            plt.close()
    
    print(f"\nGenerated directional analysis plots for {len(contest_days)} contest days")

if __name__ == "__main__":
    main()
