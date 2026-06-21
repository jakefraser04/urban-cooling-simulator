"""
Upload enriched GeoJSON building data to Supabase PostGIS database.

This module loads processed building data with thermal annotations and cooling
recommendations, and uploads it to a Supabase-hosted PostGIS database for
storage and spatial querying.
"""

import geopandas as gpd
from sqlalchemy import create_engine
from geoalchemy2 import Geometry
import os
from dotenv import load_dotenv

# Output table parameters
DATABASE_TABLE = "buildings"
GEOMETRY_SRID = 4326  # WGS 84 (lat/lon)
INPUT_GEOJSON = "enriched_buildings.geojson"


def upload_to_postgis():
    """
    Load enriched GeoJSON data and upload to PostGIS database.

    Reads the processed building data with thermal analysis results
    from GeoJSON and pushes it to a Supabase-hosted PostGIS table,
    replacing any existing records.

    Returns:
        None. Uploads data to the remote database.
    """
    print("Loading enriched geojson...")
    # Load our processed data
    gdf = gpd.read_file(INPUT_GEOJSON)
    
    # Load environment variables from the .env file
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        print("Error: DATABASE_URL not found. Check your .env file.")
        return

    print("Connecting to Supabase...")
    # Create the SQLAlchemy engine
    engine = create_engine(db_url)
    
    print("Pushing data to the cloud (this may take a minute)...")
    # Push the GeoDataFrame to the PostGIS table
    gdf.to_postgis(
        name=DATABASE_TABLE,
        con=engine,
        if_exists="replace",  # Replace existing table
        index=False,
        dtype={"geometry": Geometry("GEOMETRY", srid=GEOMETRY_SRID)},
    )
    
    print(f"Success! {len(gdf)} buildings uploaded to Supabase.")

if __name__ == "__main__":
    upload_to_postgis()