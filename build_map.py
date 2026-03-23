import os
import pandas as pd
import geopandas as gpd
import folium
import branca.colormap as cm
from branca.element import Template, MacroElement

# ==========================================
# CONTROL PANEL: TUNABLE PARAMETERS
# ==========================================
SHAPEFILE_PATH = os.path.join("map_data", "cb_2020_us_zcta520_500k.shp")
CSV_PATH = "zip_affordability_final.csv"

# --- Affordability Logic ---
VERY_THRESHOLD_MULTIPLIER = 0.5 
DATA_YEAR = "2022"

# --- Colors ---
COLOR_GRADIENT = ['#8b0000', '#6a5acd', '#00bfff'] # Dark Red -> Slate Blue -> Deep Sky Blue
COLOR_MIN = -1000
COLOR_MAX = 1000

# Tooltip HTML Label Colors
LABEL_COLOR_VERY_UNAFFORDABLE = '#8b0000' # Dark Red
LABEL_COLOR_UNAFFORDABLE      = '#d45050' # Soft Red
LABEL_COLOR_AFFORDABLE        = '#6a5acd' # Slate Blue
LABEL_COLOR_VERY_AFFORDABLE   = '#00bfff' # Deep Sky Blue

MISSING_DATA_COLOR = '#222222'      
POLYGON_BORDER_COLOR = '#111111'    
INTERACTIVE_THEME = 'CartoDB dark_matter'

# ==========================================
# DATA PROCESSING FUNCTIONS
# ==========================================

def create_html_labels(row):
    delta = row['affordability_delta']
    ideal = row['ideal_rent']
    
    if pd.isna(delta) or pd.isna(ideal):
        return "N/A", '<div style="background:#444; color:white; padding:4px; text-align:center;">NO DATA</div>'
        
    delta_bg = LABEL_COLOR_VERY_UNAFFORDABLE if delta < 0 else LABEL_COLOR_VERY_AFFORDABLE
    delta_text = "white" if delta < 0 else "black"
    formatted_delta = f'<span style="background-color:{delta_bg}; color:{delta_text}; padding:2px 6px; border-radius:4px; font-weight:bold;">${delta:,.2f}</span>'
    
    threshold = ideal * VERY_THRESHOLD_MULTIPLIER
    
    if delta <= -threshold:
        bg_color, text = LABEL_COLOR_VERY_UNAFFORDABLE, "VERY UNAFFORDABLE"
    elif delta < 0:
        bg_color, text = LABEL_COLOR_UNAFFORDABLE, "UNAFFORDABLE"
    elif delta >= threshold:
        bg_color, text = LABEL_COLOR_VERY_AFFORDABLE, "VERY AFFORDABLE"
    else:
        bg_color, text = LABEL_COLOR_AFFORDABLE, "AFFORDABLE"
        
    formatted_label = f'<div style="background-color:{bg_color}; color:white; padding:5px 10px; text-align:center; border-radius:4px; font-weight:900; letter-spacing:1px; margin-top:4px;">{text}</div>'
    return formatted_delta, formatted_label

def format_currency(val):
    if pd.isna(val): return "N/A"
    return f"${val:,.0f}"

def load_and_merge_data():
    print("Loading geographic shapes...")
    gdf = gpd.read_file(SHAPEFILE_PATH)
    gdf = gdf.rename(columns={"ZCTA5CE20": "zip_code"})
    
    # SIMPLIFY GEOMETRY: Crucial for web performance (prevents massive HTML file sizes)
    print("Simplifying geometries for web browser rendering...")
    gdf['geometry'] = gdf['geometry'].simplify(tolerance=0.01, preserve_topology=True)
    
    print("Loading affordability data...")
    df = pd.read_csv(CSV_PATH, dtype={'zip_code': str})
    
    print("Formatting HTML Tooltips...")
    df[['fmt_delta', 'html_label']] = df.apply(lambda row: pd.Series(create_html_labels(row)), axis=1)
    
    df['fmt_ideal'] = df['ideal_rent'].apply(format_currency) + "/mo"
    df['fmt_rent'] = df['median_rent'].apply(format_currency) + "/mo"
    df['fmt_income'] = df['median_income_renter'].apply(format_currency) + "/yr"
    
    print("Merging spatial and tabular data...")
    merged_gdf = gdf.merge(df, on="zip_code", how="left")
    
    # Filter out Alaska, Hawaii, and PR for the initial view, or just let bounds handle it.
    # To keep the file fast, we will clip roughly to the Contiguous US + AK/HI for now.
    return merged_gdf, df

# ==========================================
# MAP GENERATION FUNCTIONS
# ==========================================

def generate_interactive_map(gdf, raw_df):
    print("Generating full US interactive map...")
    
    # Project to Mercator for accurate centroid, then back
    projected_area = gdf.to_crs(epsg=3857)
    centroids = projected_area.geometry.centroid.to_crs(epsg=4326)
    
    # Center roughly on the geographic center of the Contiguous US
    m = folium.Map(location=[39.8283, -98.5795], zoom_start=5, tiles=INTERACTIVE_THEME)
    
    nat_median_income = raw_df['median_income_renter'].median()
    nat_median_rent = raw_df['median_rent'].median()
    nat_ideal_rent = (nat_median_income / 12) * 0.30

    colormap = cm.LinearColormap(colors=COLOR_GRADIENT, vmin=COLOR_MIN, vmax=COLOR_MAX)
    colormap.caption = 'Affordability Delta ($)[Ideal - Actual]'
    colormap.add_to(m)
    
    def style_function(feature):
        delta = feature['properties']['affordability_delta']
        if pd.isna(delta):
            return {'fillColor': MISSING_DATA_COLOR, 'color': POLYGON_BORDER_COLOR, 'weight': 0.1, 'fillOpacity': 0.3}
        return {'fillColor': colormap(delta), 'color': POLYGON_BORDER_COLOR, 'weight': 0.3, 'fillOpacity': 0.85}

    folium.GeoJson(
        gdf,
        style_function=style_function,
        tooltip=folium.features.GeoJsonTooltip(
            fields=['zip_code', 'fmt_delta', 'fmt_ideal', 'fmt_rent', 'fmt_income', 'html_label'],
            aliases=['ZIP Code:', 'Delta:', 'Ideal Rent (30%):', 'Median Rent:', 'Renter Income:', ''],
            localize=True
        )
    ).add_to(m)
    
    # -- HTML OVERLAYS (Title, Medians Box, Footer) --
    overlay_html = f"""
    {{% macro html(this, kwargs) %}}
    <!-- Title -->
    <div style="position: fixed; 
                top: 20px; left: 50%; transform: translateX(-50%);
                background-color: rgba(17, 17, 17, 0.85); 
                padding: 10px 30px; border-radius: 8px; border: 1px solid #6a5acd;
                z-index: 9999; color: white; font-family: Arial, sans-serif; 
                text-align: center; box-shadow: 0px 4px 10px rgba(0,0,0,0.5);">
        <h1 style="margin: 0; font-size: 28px; color: #00bfff;">The Affordability Delta</h1>
        <p style="margin: 5px 0 0 0; font-size: 14px; color: #ccc;">Mapping the Gap Between Renter Incomes and Reality</p>
    </div>

    <!-- National Medians -->
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 280px; 
                background-color: rgba(17, 17, 17, 0.9); 
                border: 2px solid #6a5acd; border-radius: 8px; 
                z-index: 9999; padding: 15px; color: white; 
                font-family: Arial, sans-serif; box-shadow: 3px 3px 15px rgba(0,0,0,0.5);">
        <h4 style="margin-top: 0; margin-bottom: 10px; color: #00bfff;">US National Medians</h4>
        <p style="margin: 5px 0; font-size: 14px;"><b>Renter Income:</b> ${nat_median_income:,.0f}/yr</p>
        <p style="margin: 5px 0; font-size: 14px;"><b>Gross Rent:</b> ${nat_median_rent:,.0f}/mo</p>
        <hr style="border-color: #555;">
        <p style="margin: 5px 0; font-size: 14px; color: #d45050;"><b>Ideal 30% Rent:</b> ${nat_ideal_rent:,.0f}/mo</p>
    </div>
    
    <!-- Footer -->
    <div style="position: fixed; 
                bottom: 10px; right: 10px;
                background-color: rgba(17, 17, 17, 0.7); 
                padding: 5px 15px; border-radius: 4px; 
                z-index: 9999; color: #aaa; font-family: Arial, sans-serif; 
                font-size: 12px; pointer-events: none;">
        Data Source: {DATA_YEAR} US Census Bureau (American Community Survey 5-Year Estimates)
    </div>
    {{% endmacro %}}
    """
    macro = MacroElement()
    macro._template = Template(overlay_html)
    m.get_root().add_child(macro)
    
    m.save("index.html")
    print("Saved full map to 'index.html'.")

def main():
    merged_gdf, raw_df = load_and_merge_data()
    generate_interactive_map(merged_gdf, raw_df)

if __name__ == "__main__":
    main()