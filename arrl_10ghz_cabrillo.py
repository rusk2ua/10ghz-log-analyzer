#!/usr/bin/env python3

import pandas as pd
import requests
from io import StringIO
from datetime import datetime
import math

VERSION = "1.4.0"

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
        return 0.0, 0.0  # Return origin for invalid grids
    if len(grid) < 6:
        grid = grid + 'AA'[:6-len(grid)]  # Pad with AA if too short
    grid = grid[:6]  # Truncate if too long
    
    try:
        lon = (ord(grid[0]) - ord('A')) * 20 - 180
        lat = (ord(grid[1]) - ord('A')) * 10 - 90
        lon += (ord(grid[2]) - ord('0')) * 2
        lat += (ord(grid[3]) - ord('0')) * 1
        lon += (ord(grid[4]) - ord('A')) * 5/60
        lat += (ord(grid[5]) - ord('A')) * 2.5/60
        return lat + 1.25/60, lon + 2.5/60
    except (ValueError, IndexError):
        return 0.0, 0.0  # Return origin for invalid grids

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
    # Replace various ghz formats with standard GHz
    if 'ghz' in band_str:
        # Extract number and replace with standard format
        import re
        match = re.search(r'(\d+)', band_str)
        if match:
            number = match.group(1)
            return f"{number} GHz"
    return str(band).strip()

def generate_summary(df, header_info, total_score):
    """Generate plain-text summary matching the screenshot format"""
    lines = []
    
    # Header
    lines.append("ARRL 10 GHz and Up Contest, 2025")
    lines.append(f"Call\t\t{header_info['callsign']}")
    lines.append(f"Class\t\t{header_info['category_operator'].replace('-', ' ').title()}")
    lines.append(f"Score\t\t{total_score}")
    lines.append("")
    lines.append("Band\t\tQSOs\t\tPoints\t\tUnique Calls\tBest DX (km)")
    
    # Calculate stats per band
    band_stats = {}
    for _, row in df.iterrows():
        band = normalize_band(row['band'])  # Normalize band name
        call = row['call'].upper()
        distance = calculate_distance(row['sourcegrid'], row['grid'])
        distance_km = max(1, math.ceil(distance))
        band_multiplier = get_band_multiplier(band)
        points = distance_km * band_multiplier
        
        if band not in band_stats:
            band_stats[band] = {
                'qsos': 0,
                'points': 0,
                'unique_calls': set(),
                'best_dx': 0
            }
        
        band_stats[band]['qsos'] += 1
        band_stats[band]['points'] += points
        band_stats[band]['unique_calls'].add(call)
        band_stats[band]['best_dx'] = max(band_stats[band]['best_dx'], math.ceil(distance))
    
    # Sort bands by frequency
    band_order = ['10 GHz', '24 GHz', '47 GHz', '78 GHz', '122 GHz', '241 GHz', '300 GHz']
    
    total_qsos = 0
    total_points = 0
    total_unique = set()
    
    for band_name in band_order:
        # Find matching band in data
        matching_band = None
        for band in band_stats.keys():
            if band_name.split()[0].lower() in str(band).lower():
                matching_band = band
                break
        
        if matching_band:
            stats = band_stats[matching_band]
            qsos = stats['qsos']
            distance_points = stats['points']
            unique_calls = len(stats['unique_calls'])
            bonus_points = unique_calls * 100
            total_band_points = distance_points + bonus_points
            best_dx = stats['best_dx']
            
            lines.append(f"{band_name}\t\t{qsos}\t\t{total_band_points}\t\t{unique_calls}\t\t{best_dx}")
            
            total_qsos += qsos
            total_points += total_band_points
            total_unique.update(stats['unique_calls'])
        else:
            lines.append(f"{band_name}\t\t0\t\t0\t\t0\t\t0")
    
    # Calculate totals
    total_qsos = sum(stats['qsos'] for stats in band_stats.values())
    total_points = sum(stats['points'] + len(stats['unique_calls']) * 100 for stats in band_stats.values())
    total_unique_sum = sum(len(stats['unique_calls']) for stats in band_stats.values())
    
    lines.append("")
    lines.append("Light")
    lines.append(f"Total\t\t{len(df)}\t\t{total_score}\t\t{total_unique_sum}")
    
    return '\n'.join(lines)

def get_band_multiplier(band):
    """Get points per km multiplier based on band"""
    band_str = str(band).lower().replace(' ', '')
    if '10ghz' in band_str or '10g' in band_str:
        return 1
    elif '24ghz' in band_str or '24g' in band_str:
        return 2
    elif '47ghz' in band_str or '47g' in band_str:
        return 3
    elif '78ghz' in band_str or '75g' in band_str or '76g' in band_str:
        return 4
    elif '122ghz' in band_str or '119g' in band_str or '120g' in band_str:
        return 5
    elif '142ghz' in band_str or '142g' in band_str:
        return 6
    elif '241ghz' in band_str or '241g' in band_str:
        return 10
    else:
        return 1  # Default multiplier

def check_duplicates(df):
    """Check for duplicate contacts (same call, source grid, destination grid, and band)"""
    print("\n=== Duplicate Contact Check ===")
    
    # Normalize band names for comparison
    df['band_normalized'] = df['band'].apply(lambda x: normalize_band(x))
    
    # Create a key for duplicate detection: call + source grid + destination grid + band
    df['dup_key'] = df['call'].str.upper() + '_' + df['sourcegrid'].str.upper() + '_' + df['grid'].str.upper() + '_' + df['band_normalized']
    
    # Find duplicates
    duplicates = df[df.duplicated(subset=['dup_key'], keep=False)]
    
    if len(duplicates) > 0:
        print(f"WARNING: Found {len(duplicates)} duplicate contacts:")
        print("Date     Time Call     Band    Source   Dest     Status")
        print("-" * 55)
        
        # Group by duplicate key to show sets
        for dup_key, group in duplicates.groupby('dup_key'):
            for i, (_, row) in enumerate(group.iterrows()):
                status = "ORIGINAL" if i == 0 else "DUPLICATE"
                print(f"{str(row['date'])[:10]} {str(row['time']).zfill(4)} {str(row['call']).upper():<8} {str(row['band']):<7} {str(row['sourcegrid']).upper():<8} {str(row['grid']).upper():<8} {status}")
            print("-" * 55)
    else:
        print("No duplicate contacts found.")
    
    print("")
    return len(duplicates)

def calculate_score(df):
    """Calculate contest score - distance points × band multiplier + 100 per unique call per band"""
    
    # Check for duplicates first
    duplicate_count = check_duplicates(df)
    
    total_score = 0
    unique_calls_per_band = {}
    
    print("\n=== Points Breakdown ===")
    
    for _, row in df.iterrows():
        # Distance points with band multiplier and minimum of 1 km
        distance = calculate_distance(row['sourcegrid'], row['grid'])
        distance_km = max(1, math.ceil(distance))  # Round up and minimum 1 km per QSO
        band_multiplier = get_band_multiplier(row['band'])
        distance_points = distance_km * band_multiplier
        total_score += distance_points
        
        print(f"{row['call'].upper()}: {distance:.1f} km → {distance_km} km × {band_multiplier} ({row['band']}) = {distance_points} points")
        
        # Track unique calls per band
        band = normalize_band(row['band'])
        call = row['call'].upper()
        if band not in unique_calls_per_band:
            unique_calls_per_band[band] = set()
        unique_calls_per_band[band].add(call)
    
    # Add 100 points per unique call per band
    bonus_points = 0
    for band, calls in unique_calls_per_band.items():
        band_bonus = len(calls) * 100
        bonus_points += band_bonus
        print(f"\nBand {band}: {len(calls)} unique calls × 100 = {band_bonus} bonus points")
    
    print(f"\nDistance points: {total_score}")
    print(f"Bonus points: {bonus_points}")
    print(f"Total score: {total_score + bonus_points}")
    
    if duplicate_count > 0:
        print(f"\nNOTE: {duplicate_count} duplicate contacts detected above - review log for accuracy")
    
    return total_score + bonus_points

def convert_band_to_cabrillo_format(band):
    """Convert band to Cabrillo format (e.g., '10 GHz' -> '10G')"""
    band_str = str(band).strip().lower()
    if '10' in band_str:
        return '10G'
    elif '24' in band_str:
        return '24G'
    elif '47' in band_str:
        return '47G'
    elif '78' in band_str or '75' in band_str or '76' in band_str:
        return '75G'
    elif '122' in band_str or '119' in band_str or '120' in band_str:
        return '123G'
    elif '142' in band_str:
        return '142G'
    elif '241' in band_str:
        return '241G'
    else:
        return str(band).upper()

def generate_cabrillo(df, header_info):
    """Generate Cabrillo format output matching k2ua.log format"""
    lines = []
    
    # Header - only essential lines, no X- or HQ- lines
    lines.append("START-OF-LOG: 3.0")
    lines.append(f"CONTEST: {header_info['contest']}")
    lines.append(f"CALLSIGN: {header_info['callsign'].upper()}")
    lines.append(f"CATEGORY-BAND: {header_info['category_band'].upper()}")
    lines.append(f"CATEGORY-OPERATOR: {header_info['category_operator'].upper()}")
    lines.append(f"CATEGORY-MODE: {header_info['category_mode'].upper()}")
    lines.append(f"CATEGORY-POWER: {header_info['category_power'].upper()}")
    
    score = header_info['claimed_score'] if header_info['claimed_score'] else calculate_score(df)
    lines.append(f"CLAIMED-SCORE: {score}")
    lines.append(f"CREATED-BY: K2UA Python Logger v{VERSION}")
    
    # QSO lines - format: QSO: <band> <mode> <date> <time> <mycall> <mygrid> <call> <grid>
    for _, row in df.iterrows():
        # Convert time to HHMM format
        time_str = str(row['time']).zfill(4) if len(str(row['time'])) <= 4 else str(row['time'])[:4]
        
        # Convert band to Cabrillo format
        band_formatted = convert_band_to_cabrillo_format(row['band'])
        
        # Format date as yyyy-mm-dd
        date_str = str(row['date'])
        if '/' in date_str:
            # Convert mm/dd/yyyy to yyyy-mm-dd
            try:
                date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                date_str = date_obj.strftime('%Y-%m-%d')
            except:
                pass
        
        # Format matching k2ua.log: QSO: 10G CW 2022-08-20 1035 K2UA EN91KT KB8VAO EN91IS
        qso_line = f"QSO: {band_formatted} CW {date_str} {time_str} {header_info['callsign'].upper()} {str(row['sourcegrid']).upper()} {str(row['call']).upper()} {str(row['grid']).upper()}"
        lines.append(qso_line)
    
    lines.append("END-OF-LOG:")
    return '\n'.join(lines)

def get_user_input():
    """Get required Cabrillo header information from user"""
    print("\n=== ARRL 10 GHz and Up Contest - Cabrillo Header Information ===\n")
    
    callsign = input("Your callsign (e.g., W1ABC): ").strip().upper()
    contest = "ARRL-10-GHZ"
    
    print("\nOperator Category:")
    print("  SINGLE-OP = Single operator")
    print("  MULTI-OP  = Multiple operators")
    category_operator = input("Enter SINGLE-OP or MULTI-OP: ").strip().upper()
    
    print("\nBand Category:")
    print("  10G  = 10 GHz only")
    print("  24G  = 24 GHz only") 
    print("  47G  = 47 GHz only")
    print("  75G  = 75+ GHz only")
    print("  119G = 119 GHz only")
    print("  142G = 142 GHz only")
    print("  241G = 241 GHz only")
    print("  ALL  = All bands")
    category_band = input("Enter band category: ").strip().upper()
    
    print("\nPower Category:")
    print("  LOW  = Low power")
    print("  HIGH = High power")
    category_power = input("Enter LOW or HIGH: ").strip().upper()
    
    print("\nMode Category:")
    print("  CW    = CW only")
    print("  FM    = FM only")
    print("  MIXED = Multiple modes")
    category_mode = input("Enter CW, FM, or MIXED: ").strip().upper()
    
    claimed_score = input("\nClaimed score (press Enter to auto-calculate): ").strip()
    
    return {
        'callsign': callsign,
        'contest': contest,
        'category_operator': category_operator,
        'category_band': category_band,
        'category_power': category_power,
        'category_mode': category_mode,
        'claimed_score': claimed_score
    }

def main():
    sheet_url = "https://docs.google.com/spreadsheets/d/1UFbxzWJBpPdUEkfLhNA6csKbHaNypDmGeWpaeP-bQyA/edit?usp=sharing"
    
    # Get data
    df = get_sheet_data(sheet_url)
    
    # Skip header rows and get contact data
    contact_data = df.iloc[2:].copy()  # Skip first 2 header rows
    contact_data.columns = ['date', 'band', 'sourcegrid', 'time', 'call', 'grid']
    
    # Forward fill empty cells with values from above
    contact_data = contact_data.ffill()
    
    # Clean data
    contact_data = contact_data.dropna(subset=['call'])
    
    # Get user input
    header_info = get_user_input()
    
    # Calculate score
    total_score = calculate_score(contact_data)
    
    # Generate Cabrillo
    cabrillo_content = generate_cabrillo(contact_data, header_info)
    
    # Generate summary
    summary_content = generate_summary(contact_data, header_info, total_score)
    
    # Save files
    cabrillo_filename = f"{header_info['callsign']}_ARRL_10GHZ.log"
    summary_filename = f"{header_info['callsign']}_ARRL_10GHZ_Summary.txt"
    
    with open(cabrillo_filename, 'w') as f:
        f.write(cabrillo_content)
    
    with open(summary_filename, 'w') as f:
        f.write(summary_content)
    
    print(f"\nCabrillo file saved as: {cabrillo_filename}")
    print(f"Summary file saved as: {summary_filename}")
    print(f"Total QSOs: {len(contact_data)}")

if __name__ == "__main__":
    main()
