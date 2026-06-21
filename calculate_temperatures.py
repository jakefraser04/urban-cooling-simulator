"""
Generate simulated thermal data and calculate building roof temperature recommendations.

This module creates a synthetic Land Surface Temperature (LST) grid, overlays it with
building footprints, calculates zonal statistics for each building's roof, and generates
cooling recommendations based on thermal performance.
"""

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.mask import mask

# Thermal simulation parameters
GRID_WIDTH = 500  # Pixels
GRID_HEIGHT = 500  # Pixels
BASE_TEMPERATURE_C = 32.0  # Base temperature in Celsius
THERMAL_AMPLITUDE = 8.0  # Amplitude of thermal variation
TEMPERATURE_NOISE_STD = 0.5  # Standard deviation of noise

# Temperature thresholds for cooling recommendations (°F)
CRITICAL_HEAT_THRESHOLD = 93.0
MODERATE_HEAT_THRESHOLD = 88.0
FALLBACK_TEMPERATURE = 32.0

# Output file names
RASTER_FILENAME = "simulated_thermal.tif"
OUTPUT_GEOJSON = "enriched_buildings.geojson"

# Cooling recommendations by temperature range
COOLING_RECOMMENDATIONS = {
    "critical": "Critical Heat Retention: Highly recommend high-albedo ultra-white roof coating (90%+ solar reflectance).",
    "moderate": "Moderate Heat Retention: Recommend a cool roof paint or partial green roof implementation.",
    "optimal": "Optimal: Roof temperature is stable. Maintain current surface or consider standard reflective updates.",
}


def generate_thermal_and_overlay():
    """
    Generate synthetic thermal data and calculate building roof temperature recommendations.

    Loads building footprints, creates a simulated LST raster, extracts per-building
    thermal statistics, and generates cooling recommendations based on temperature thresholds.

    Returns:
        None. Writes enriched GeoJSON file to the current directory.
    """
    print("Loading building footprints...")
    gdf = gpd.read_file("cincinnati_test_buildings.geojson")
    
    minx, miny, maxx, maxy = gdf.total_bounds
    transform = from_bounds(minx, miny, maxx, maxy, GRID_WIDTH, GRID_HEIGHT)
    
    print("Generating simulated Land Surface Temperature (LST) grid...")
    y, x = np.mgrid[0:GRID_HEIGHT, 0:GRID_WIDTH]
    raw_thermal = (
        BASE_TEMPERATURE_C
        + THERMAL_AMPLITUDE * np.sin(x / 100.0) * np.cos(y / 100.0)
        + np.random.normal(0, TEMPERATURE_NOISE_STD, size=(GRID_HEIGHT, GRID_WIDTH))
    )
    
    with rasterio.open(
        RASTER_FILENAME, "w", driver="GTiff",
        height=GRID_HEIGHT, width=GRID_WIDTH, count=1, dtype=raw_thermal.dtype,
        crs=gdf.crs.to_string(), transform=transform
    ) as dst:
        dst.write(raw_thermal, 1)
        
    print(f"Satellite raster saved as {RASTER_FILENAME}")
    print("Calculating zonal statistics using rasterio.mask...")

    # Open the newly created raster map to extract pixel values per building
    baseline_temps = []
    
    with rasterio.open(RASTER_FILENAME) as src:
        for geom in gdf.geometry:
            try:
                # The mask function isolates only the pixels inside the building polygon
                # crop=True keeps the processed array small and fast
                out_image, _ = mask(src, [geom], crop=True, nodata=-9999)
                data = out_image[0]  # Get the first band
                
                # Filter out the background pixels so we only average the roof pixels
                roof_pixels = data[data != -9999]
                
                if len(roof_pixels) > 0:
                    baseline_temps.append(float(roof_pixels.mean()))
                else:
                    baseline_temps.append(FALLBACK_TEMPERATURE)
            except (OSError, ValueError):
                # Skip buildings that fail to process
                baseline_temps.append(FALLBACK_TEMPERATURE)

    # Assign calculated temperatures back to the data frame
    gdf["baseline_temp_c"] = baseline_temps
    gdf["baseline_temp_f"] = (gdf["baseline_temp_c"] * 9 / 5) + 32
    
    print("Generating tailoring recommendations...")
    recommendations = []
    for temp in gdf["baseline_temp_f"]:
        if temp > CRITICAL_HEAT_THRESHOLD:
            recommendations.append(COOLING_RECOMMENDATIONS["critical"])
        elif temp > MODERATE_HEAT_THRESHOLD:
            recommendations.append(COOLING_RECOMMENDATIONS["moderate"])
        else:
            recommendations.append(COOLING_RECOMMENDATIONS["optimal"])
            
    gdf["cooling_recommendation"] = recommendations

    gdf.to_file(OUTPUT_GEOJSON, driver="GeoJSON")
    print(f"\nSuccess! Calculated temperatures for {len(gdf)} buildings.")
    print(f"Sample data mapped. Enriched file saved as: {OUTPUT_GEOJSON}")

if __name__ == "__main__":
    generate_thermal_and_overlay()