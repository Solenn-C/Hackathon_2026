# Import modules
from pathlib import Path
import xarray as xr
import pandas as pd

bronze_dir = Path("data/bronze/copernicus")
silver_dir = Path("data/silver")

def main():

    silver_dir.mkdir(parents=True, exist_ok=True)
    

    # Example: process all NetCDF files dropped in bronze
    for nc_file in bronze_dir.glob("*.nc"):
        print(f"Processing {nc_file.name}...")
        ds = xr.open_dataset(nc_file)

        # For this product there is a time series of global sea level anomalies.
        # Turn into a long DataFrame; adjust as needed for your schema.
        df = ds.to_dataframe().reset_index()
        print(df.head())  # Check the structure; adjust column names as needed

        parquet_path = silver_dir / (nc_file.stem + ".parquet")
        df.to_parquet(parquet_path, index=False)

if __name__ == "__main__":
    main()
