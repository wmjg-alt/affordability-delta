import os
import requests
import zipfile
import pandas as pd
import argparse

# ==========================================
# CONFIGURATION PARAMETERS (EASY TO ALTER)
# ==========================================
CENSUS_YEAR = "2022"
SHAPEFILE_YEAR = "2020" 
SHAPEFILE_DIR = "map_data"

def fetch_census_api_data(year=CENSUS_YEAR):
    """
    Fetches renter/owner income and gross rent data from the Census API.
    Calculates affordability metrics based purely on renter income.
    """
    print(f"--- Fetching {year} Census Data (Income & Rent) ---")
    url = f"https://api.census.gov/data/{year}/acs/acs5"
    
    # B25119_002E = Median Household Income (Owner Occupied)
    # B25119_003E = Median Household Income (Renter Occupied)
    # B25064_001E = Median Gross Rent
    params = {
        "get": "NAME,B25119_002E,B25119_003E,B25064_001E",
        "for": "zip code tabulation area:*"
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    data = response.json()
    headers = data[0]
    df = pd.DataFrame(data[1:], columns=headers)
    
    # Clean and rename
    df = df.rename(columns={
        "B25119_002E": "median_income_owner",
        "B25119_003E": "median_income_renter",
        "B25064_001E": "median_rent",
        "zip code tabulation area": "zip_code"
    })
    
    # Convert types, forcing Census error codes (negatives) to NaN
    for col in['median_income_owner', 'median_income_renter', 'median_rent']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Drop rows missing renter income or rent (we must have these to map affordability)
    # Note: We keep the row even if owner_income is missing!
    df = df[(df['median_income_renter'] > 0) & (df['median_rent'] > 0)].copy()
    
    # Calculate Affordability Delta (Ideal Rent minus Actual Rent)
    df['ideal_rent'] = (df['median_income_renter'] / 12) * 0.30
    df['affordability_delta'] = df['ideal_rent'] - df['median_rent']
    
    df['ideal_rent'] = df['ideal_rent'].round(2)
    df['affordability_delta'] = df['affordability_delta'].round(2)
    
    df.to_csv("zip_affordability_final.csv", index=False)
    print(f"Success: Saved {len(df)} rows to zip_affordability_final.csv\n")

def fetch_zcta_shapefile(year=SHAPEFILE_YEAR):
    """Downloads and extracts the ZCTA shapefile for the specified year."""
    print(f"--- Fetching {year} ZCTA Shapefile ---")
    url = f"https://www2.census.gov/geo/tiger/GENZ{year}/shp/cb_{year}_us_zcta520_500k.zip"
    
    if not os.path.exists(SHAPEFILE_DIR):
        os.makedirs(SHAPEFILE_DIR)
        
    zip_path = os.path.join(SHAPEFILE_DIR, "zcta.zip")
    
    print("Downloading zip file (this may take a minute)...")
    response = requests.get(url)
    response.raise_for_status()
    
    with open(zip_path, 'wb') as f:
        f.write(response.content)
        
    print("Extracting shapefile...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(SHAPEFILE_DIR)
        
    os.remove(zip_path)
    print(f"Success: Shapefiles extracted to ./{SHAPEFILE_DIR}/\n")

def main():
    parser = argparse.ArgumentParser(description="Fetch Data for The Affordability Delta")
    parser.add_argument('--census', action='store_true', help="Fetch only the Census API data (CSV)")
    parser.add_argument('--zip', action='store_true', help="Fetch only the ZCTA Shapefiles (Map Data)")
    parser.add_argument('--all', action='store_true', help="Fetch everything (Default behavior)")
    
    args = parser.parse_args()
    run_all = args.all or not (args.census or args.zip)

    if args.census or run_all:
        fetch_census_api_data()
        
    if args.zip or run_all:
        fetch_zcta_shapefile()

if __name__ == "__main__":
    main()