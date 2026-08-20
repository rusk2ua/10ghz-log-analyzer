#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import math

from data_source import (
    load_source_or_exit, build_arg_parser,
    normalize_band, band_multiplier,
)

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

def categorize_contest_day(dt, contest_dates):
    """Categorize QSO into contest day periods using dynamically determined dates"""
    if dt is None:
        return "Unknown"
    
    date_key = dt.strftime('%Y-%m-%d')
    day_num = contest_dates.get(date_key)
    
    if day_num:
        return f"{date_key} Day {day_num}"
    else:
        return "Outside Contest Hours"

def determine_contest_dates(df):
    """Determine contest day assignments from the actual QSO dates in the log.
    
    The ARRL 10 GHz contest runs over two weekends. This function groups
    dates into contest weekends and assigns day numbers sequentially.
    """
    unique_dates = []
    for date_str in df['date'].unique():
        try:
            if '/' in str(date_str):
                date_parts = str(date_str).split('/')
                if len(date_parts[2]) == 4:
                    dt = datetime.strptime(str(date_str), '%m/%d/%Y')
                else:
                    dt = datetime.strptime(str(date_str), '%m/%d/%y')
            else:
                dt = datetime.strptime(str(date_str), '%Y-%m-%d')
            unique_dates.append(dt)
        except:
            continue
    
    if not unique_dates:
        return {}
    
    unique_dates.sort()
    
    # Group dates into weekends (dates within 3 days of each other are same weekend)
    weekends = []
    current_weekend = [unique_dates[0]]
    
    for i in range(1, len(unique_dates)):
        if (unique_dates[i] - current_weekend[-1]).days <= 3:
            current_weekend.append(unique_dates[i])
        else:
            weekends.append(current_weekend)
            current_weekend = [unique_dates[i]]
    weekends.append(current_weekend)
    
    # Assign day numbers sequentially across weekends
    contest_dates = {}
    day_num = 1
    for weekend in weekends:
        for date in weekend:
            contest_dates[date.strftime('%Y-%m-%d')] = day_num
            day_num += 1
    
    return contest_dates

def calculate_points(distance, band):
    """Calculate contest points for a QSO"""
    distance_km = max(1, math.ceil(distance))
    multiplier = band_multiplier(band)
    return distance_km * multiplier

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
    parser = build_arg_parser(
        "Generate polar (radar) plots of directional contest activity from "
        "a Cabrillo log, a raw QSO CSV, or a Google Sheets share URL."
    )
    args = parser.parse_args()

    # Get data
    contact_data, callsign = load_source_or_exit(args.source)

    # Determine contest dates dynamically from the data
    contest_dates = determine_contest_dates(contact_data)
    
    # Add analysis columns
    contact_data['datetime'] = contact_data.apply(lambda row: parse_datetime(row['date'], row['time']), axis=1)
    contact_data['contest_day'] = contact_data['datetime'].apply(lambda dt: categorize_contest_day(dt, contest_dates))
    contact_data['distance'] = contact_data.apply(lambda row: calculate_distance(row['sourcegrid'], row['grid']), axis=1)
    contact_data['bearing'] = contact_data.apply(lambda row: calculate_bearing(row['sourcegrid'], row['grid']), axis=1)
    contact_data['direction'] = contact_data['bearing'].apply(get_direction)
    contact_data['band_normalized'] = contact_data['band'].apply(normalize_band)
    contact_data['points'] = contact_data.apply(lambda row: calculate_points(row['distance'], row['band']), axis=1)
    
    # Group by contest days - extract just the day number for grouping
    contact_data['day_number'] = contact_data['contest_day'].str.extract(r'Day (\d+)')[0]
    contest_days = contact_data[contact_data['day_number'].notna()].groupby('day_number')
    
    # Get last date for filename
    last_date = max(contact_data['date'].unique())
    if '/' in str(last_date):
        try:
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
