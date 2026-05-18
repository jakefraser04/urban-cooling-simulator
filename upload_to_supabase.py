import geopandas as gpd
from sqlalchemy import create_engine
from geoalchemy2 import Geometry
import os
from dotenv import load_dotenv

def upload_to_postgis():
    print("Loading enriched geojson...")
    # Load our processed data
    gdf = gpd.read_file("enriched_buildings.geojson")
    
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
    # Push the GeoDataFrame directly to a new table called 'buildings'
    # srid=4326 tells PostGIS that these are standard GPS coordinates (Latitude/Longitude)
    gdf.to_postgis(
        name='buildings',
        con=engine,
        if_exists='replace', # If we run this script again, it drops and replaces the table
        index=False,
        dtype={'geometry': Geometry('GEOMETRY', srid=4326)} 
    )
    
    print(f"Success! {len(gdf)} buildings uploaded to Supabase.")

if __name__ == "__main__":
    upload_to_postgis()