import argparse
from datetime import datetime, timedelta
import pystac_client
import planetary_computer
import rioxarray
from shapely.geometry import box

def get_optimal_thermal_window():
    now = datetime.now()
    current_year = now.year
    
    if 7 <= now.month <= 10:
        start_date = (now - timedelta(days=60)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
        print(f"Current season is Summer/Fall. Setting relative search window: {start_date} to {end_date}")
    else:
        target_year = current_year - 1
        start_date = f"{target_year}-06-01"
        end_date = f"{target_year}-08-31"
        print(f"Outside of peak summer season. Defaulting to previous year's summer ({target_year}): {start_date} to {end_date}")
        
    return f"{start_date}/{end_date}"

def harvest_real_thermal_data(lat, lon, buffer_size, temp_floor):
    print("\n=======================================================")
    print("  INITIALIZING MULTI-SCENE SATELLITE HARVESTER")
    print("=======================================================")
    
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )

    min_lon = lon - buffer_size
    max_lon = lon + buffer_size
    min_lat = lat - buffer_size
    max_lat = lat + buffer_size
    search_area = box(min_lon, min_lat, max_lon, max_lat)

    dynamic_datetime = get_optimal_thermal_window()

    print("Querying STAC asset registry for candidate scenes...")
    search = catalog.search(
        collections=["landsat-c2-l2"],
        intersects=search_area,
        datetime=dynamic_datetime,
        query={"eo:cloud_cover": {"lt": 35}}, # Accept up to 35% clouds for a larger initial pool
    )

    items = list(search.item_collection())
    if not items:
        print("❌ Error: No satellite scenes found matching basic search boundaries.")
        return

    print(f"\nScanning thermal metrics for {len(items)} scenes to isolate warm days...")
    warm_survivors = []

    for scene in items:
        scene_date = datetime.strptime(scene.properties["datetime"][:10], "%Y-%m-%d").strftime("%B %d, %Y")
        thermal_url = scene.assets["lwir11"].href
        cloud_cover = scene.properties["eo:cloud_cover"]
        
        try:
            with rioxarray.open_rasterio(thermal_url) as raster:
                local_slice = raster.rio.clip([search_area], crs="EPSG:4326")
                max_raw_value = float(local_slice.max())
                
                max_kelvin = (max_raw_value * 0.00341802) + 149.0
                max_fahrenheit = (max_kelvin - 273.15) * (9/5) + 32
                
                if max_fahrenheit >= temp_floor:
                    warm_survivors.append({
                        "scene": scene,
                        "cloud_cover": cloud_cover,
                        "date": scene_date,
                        "temp": max_fahrenheit
                    })
        except Exception:
            continue

    if not warm_survivors:
        print(f"❌ Error: Zero scenes cleared the {temp_floor}°F threshold constraint.")
        return

    # Sort survivors by cloud cover (clearest first) and grab the top 5
    top_winners = sorted(warm_survivors, key=lambda x: x["cloud_cover"])[:5]

    print(f"\n🏆 Selected the Top {len(top_winners)} Clearest Heatwave Days for Averaging:")
    for i, winner in enumerate(top_winners):
        print(f"   [{i+1}] Date: {winner['date']} | Clouds: {winner['cloud_cover']:.1f}% | Peak Heat: {winner['temp']:.1f}°F")

    print("\nDownloading and cropping selected thermal assets...")
    for i, winner in enumerate(top_winners):
        best_scene = winner["scene"]
        thermal_asset = best_scene.assets["lwir11"]
        output_name = f"landsat_thermal_{i+1}.tif"
        
        with rioxarray.open_rasterio(thermal_asset.href) as raster:
            clipped_raster = raster.rio.clip([search_area], crs="EPSG:4326")
            clipped_raster.rio.to_raster(output_name)
            print(f"   -> Saved: {output_name}")
            
    print("=======================================================\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Global Landsat Multi-Scene Harvester")
    parser.add_argument("--lat", type=float, default=39.1031)
    parser.add_argument("--lon", type=float, default=-84.5120)
    parser.add_argument("--buffer", type=float, default=0.05)
    parser.add_argument("--temp-floor", type=float, default=70.0)
    
    args = parser.parse_args()
    harvest_real_thermal_data(args.lat, args.lon, args.buffer, args.temp_floor)