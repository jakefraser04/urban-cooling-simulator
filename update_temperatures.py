"""
Aggregate multi-day Landsat thermal data and update building temperature records.

This module processes multiple thermal rasters, performs zonal statistics for each
building, aggregates temperatures across days, and updates the database with averaged
thermal data for robust urban heat analysis.
"""

import os
from dotenv import load_dotenv
import geopandas as gpd
from sqlalchemy import create_engine, text
import rasterio
import rasterio.mask
import numpy as np
from collections import defaultdict

load_dotenv()

# Thermal data processing parameters
MAX_LANDSAT_RASTERS = 5  # Maximum expected satellite images
THERMAL_CONVERSION_FACTOR = 0.00341802  # Scaling factor for raw DN to spectral radiance
THERMAL_OFFSET = 149.0  # Offset for spectral radiance
ABSOLUTE_ZERO_KELVIN = 273.15  # Kelvin to Celsius offset
FAHRENHEIT_MULTIPLIER = 9 / 5  # Celsius to Fahrenheit conversion
VALID_TEMP_RANGE = (50.0, 160.0)  # Valid temperature range in Fahrenheit for sanity check


def update_database_with_averaged_thermal_data():
    """
    Aggregate multi-day thermal data and update building temperature records.

    Processes all available Landsat thermal rasters, extracts per-building zonal
    statistics, averages temperatures across days, and updates the PostGIS database
    with robust multi-day average temperatures.

    Returns:
        None. Updates 'baseline_temp_f' column in the buildings database table.
    """
    print("\n=======================================================")
    print("  STARTING MULTI-DAY SPATIAL PROCESSING PIPELINE")
    print("=======================================================")
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        user = os.getenv("SUPABASE_DB_USER", "postgres")
        password = os.getenv("SUPABASE_DB_PASSWORD")
        host = os.getenv("SUPABASE_DB_HOST")
        port = os.getenv("SUPABASE_DB_PORT", "5432")
        db_name = os.getenv("SUPABASE_DB_NAME", "postgres")
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

    engine = create_engine(db_url)
    
    print("📥 Downloading structural geometries from Supabase PostGIS...")
    sql = "SELECT id, geometry FROM buildings;"
    buildings_gdf = gpd.read_postgis(sql, engine, geom_col="geometry")
    print(f"   -> Loaded {len(buildings_gdf)} building profiles.")

    # Find all downloaded landsat tiff files sequentially
    raster_files = [f"landsat_thermal_{i}.tif" for i in range(1, MAX_LANDSAT_RASTERS + 1) if os.path.exists(f"landsat_thermal_{i}.tif")]
    
    if not raster_files:
        print("❌ Error: No calibrated satellite files found. Run harvest_landsat.py first.")
        return
        
    print(f"   -> Located {len(raster_files)} satellite rasters for blending matrix.")

    # Key dictionary: building_id -> list of temperatures across different days
    building_thermal_history = defaultdict(list)

    # Loop through each raster file independently to maximize vector CRS reprojections safely
    for raster_path in raster_files:
        print(f"\nProcessing spatial intersections for: {raster_path}")
        
        with rasterio.open(raster_path) as src:
            nodata_val = src.nodata if src.nodata is not None else 0
            # Align vector coordinates to this specific raster grid
            buildings_projected = buildings_gdf.to_crs(src.crs)
            
            for idx, row in buildings_projected.iterrows():
                geom = row["geometry"]
                b_id = int(row["id"])
                
                try:
                    out_image, out_transform = rasterio.mask.mask(src, [geom], crop=True, all_touched=True)
                    data = out_image[0]
                    valid_pixels = data[data != nodata_val]
                    
                    if len(valid_pixels) == 0:
                        continue
                        
                    raw_mean = float(np.mean(valid_pixels))
                    # Convert Landsat Band 11 DN to brightness temperature (Kelvin)
                    kelvin = (raw_mean * THERMAL_CONVERSION_FACTOR) + THERMAL_OFFSET
                    # Convert Kelvin to Fahrenheit
                    fahrenheit = (kelvin - ABSOLUTE_ZERO_KELVIN) * FAHRENHEIT_MULTIPLIER + 32
                    
                    # Sanity check: reject invalid outliers
                    if VALID_TEMP_RANGE[0] <= fahrenheit <= VALID_TEMP_RANGE[1]:
                        building_thermal_history[b_id].append(fahrenheit)
                except (OSError, ValueError):
                    # Skip buildings that fail to process
                    continue

    print("\nComputing multi-day averages and pushing updates to Supabase...")
    updated_records = 0
    stmt = text("UPDATE buildings SET baseline_temp_f = :temp WHERE id = :id")
    
    with engine.begin() as conn:
        for b_id, temp_list in building_thermal_history.items():
            if not temp_list:
                continue
                
            # Compute the statistical average across all days this building was successfully captured
            avg_fahrenheit = float(np.mean(temp_list))
            
            conn.execute(stmt, {"temp": avg_fahrenheit, "id": b_id})
            updated_records += 1

    print(f"✅ Success! Calibrated and updated {updated_records} building footprints using a multi-day average.")
    print("=======================================================")

if __name__ == "__main__":
    update_database_with_averaged_thermal_data()