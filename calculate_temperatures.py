import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.mask import mask

def generate_thermal_and_overlay():
    print("Loading building footprints...")
    gdf = gpd.read_file("cincinnati_test_buildings.geojson")
    
    minx, miny, maxx, maxy = gdf.total_bounds
    width, height = 500, 500
    transform = from_bounds(minx, miny, maxx, maxy, width, height)
    
    print("Generating simulated Land Surface Temperature (LST) grid...")
    y, x = np.mgrid[0:height, 0:width]
    raw_thermal = 32.0 + 8.0 * np.sin(x / 100.0) * np.cos(y / 100.0) + np.random.normal(0, 0.5, size=(height, width))
    
    raster_filename = "simulated_thermal.tif"
    with rasterio.open(
        raster_filename, 'w', driver='GTiff',
        height=height, width=width, count=1, dtype=raw_thermal.dtype,
        crs=gdf.crs.to_string(), transform=transform
    ) as dst:
        dst.write(raw_thermal, 1)
        
    print(f"Satellite raster saved as {raster_filename}")
    print("Calculating zonal statistics using rasterio.mask...")

    # Open the newly created raster map to extract pixel values per building
    baseline_temps = []
    
    with rasterio.open(raster_filename) as src:
        for geom in gdf.geometry:
            try:
                # The mask function isolates only the pixels inside the building polygon
                # crop=True keeps the processed array small and fast
                out_image, _ = mask(src, [geom], crop=True, nodata=-9999)
                data = out_image[0] # Get the first band
                
                # Filter out the background pixels so we only average the roof pixels
                roof_pixels = data[data != -9999]
                
                if len(roof_pixels) > 0:
                    baseline_temps.append(float(roof_pixels.mean()))
                else:
                    baseline_temps.append(32.0) # Fallback baseline
            except Exception:
                baseline_temps.append(32.0)

    # Assign calculated temperatures back to the data frame
    gdf['baseline_temp_c'] = baseline_temps
    gdf['baseline_temp_f'] = (gdf['baseline_temp_c'] * 9/5) + 32
    
    print("Generating tailoring recommendations...")
    recommendations = []
    for temp in gdf['baseline_temp_f']:
        if temp > 93:
            recommendations.append("Critical Heat Retention: Highly recommend high-albedo ultra-white roof coating (90%+ solar reflectance).")
        elif temp > 88:
            recommendations.append("Moderate Heat Retention: Recommend a cool roof paint or partial green roof implementation.")
        else:
            recommendations.append("Optimal: Roof temperature is stable. Maintain current surface or consider standard reflective updates.")
            
    gdf['cooling_recommendation'] = recommendations

    output_geojson = "enriched_buildings.geojson"
    gdf.to_file(output_geojson, driver="GeoJSON")
    print(f"\nSuccess! Calculated temperatures for {len(gdf)} buildings.")
    print(f"Sample data mapped. Enriched file saved as: {output_geojson}")

if __name__ == "__main__":
    generate_thermal_and_overlay()