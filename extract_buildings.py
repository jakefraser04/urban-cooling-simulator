import osmnx as ox
import geopandas as gpd

def fetch_building_footprints():
    print("Initializing OSMnx pipeline...")
    
    # Define a central point (Downtown Cincinnati) and a radius in meters
    center_point = (39.1031, -84.5120) 
    radius_meters = 1000  
    
    # We only want features tagged as buildings
    tags = {"building": True}
    
    print(f"Fetching building data within {radius_meters}m of {center_point}...")
    buildings_gdf = ox.features.features_from_point(center_point, tags=tags, dist=radius_meters)
    
    print(f"Raw features retrieved: {len(buildings_gdf)}")
    
    # Filter for closed polygons (actual building footprints)
    polygons_gdf = buildings_gdf[buildings_gdf.geom_type.isin(['Polygon', 'MultiPolygon'])]
    
    # Keep only the essential columns for the simulator
    columns_to_keep = ['geometry', 'building', 'name']
    existing_columns = [col for col in columns_to_keep if col in polygons_gdf.columns]
    clean_gdf = polygons_gdf[existing_columns]
    
    print(f"Cleaned building polygons: {len(clean_gdf)}")
    
    # Export to GeoJSON
    output_filename = "cincinnati_test_buildings.geojson"
    clean_gdf.to_file(output_filename, driver="GeoJSON")
    print(f"Success! Saved to {output_filename}")

if __name__ == "__main__":
    fetch_building_footprints()