"""
Extract building footprints from OpenStreetMap for urban thermal analysis.

This module queries OSMnx (OpenStreetMap via Overpass API) for building
footprints within a specified radius and exports them as GeoJSON for use
in thermal simulation and analysis workflows.
"""

import osmnx as ox
import geopandas as gpd

# Query parameters
CENTER_POINT = (39.1031, -84.5120)  # Downtown Cincinnati
SEARCH_RADIUS_METERS = 1000  # 1 km radius
BUILDING_TAGS = {"building": True}
OUTPUT_FILENAME = "cincinnati_test_buildings.geojson"
COLUMNS_TO_KEEP = ["geometry", "building", "name"]


def fetch_building_footprints():
    """
    Download building footprints from OpenStreetMap and export as GeoJSON.

    Uses OSMnx to query the Overpass API for all features tagged as buildings
    within a defined radius, filters for valid polygon geometries, and exports
    the cleaned dataset to GeoJSON format.

    Returns:
        None. Writes GeoJSON file to the current directory.
    """
    print("Initializing OSMnx pipeline...")
    
    print(f"Fetching building data within {SEARCH_RADIUS_METERS}m of {CENTER_POINT}...")
    buildings_gdf = ox.features.features_from_point(CENTER_POINT, tags=BUILDING_TAGS, dist=SEARCH_RADIUS_METERS)
    
    print(f"Raw features retrieved: {len(buildings_gdf)}")
    
    # Filter for closed polygons (actual building footprints)
    polygons_gdf = buildings_gdf[buildings_gdf.geom_type.isin(["Polygon", "MultiPolygon"])]
    
    # Keep only the essential columns for the simulator
    existing_columns = [col for col in COLUMNS_TO_KEEP if col in polygons_gdf.columns]
    clean_gdf = polygons_gdf[existing_columns]
    
    print(f"Cleaned building polygons: {len(clean_gdf)}")
    
    # Export to GeoJSON
    clean_gdf.to_file(OUTPUT_FILENAME, driver="GeoJSON")
    print(f"Success! Saved to {OUTPUT_FILENAME}")

if __name__ == "__main__":
    fetch_building_footprints()