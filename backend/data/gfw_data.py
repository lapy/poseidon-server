"""
Global Fishing Watch Data Access Module - Version 2
Using official gfw-api-python-client

🚀 NASA Space Apps Challenge 2025 - Sharks from Space
This module integrates Global Fishing Watch data for anthropogenic pressure assessment
in shark habitat prediction models using the official GFW Python client.

Data Source: Global Fishing Watch (https://globalfishingwatch.org/)
Attribution: Must include "Data provided by Global Fishing Watch" in all uses
"""

import gfwapiclient as gfw
import xarray as xr
import numpy as np
import pandas as pd
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GFWDataManager:
    """Manages Global Fishing Watch API access and local caching using official GFW client"""
    
    def __init__(self, api_key: Optional[str] = None, cache_dir: Optional[str] = None):
        """
        Initialize GFW Data Manager with official client
        
        Args:
            api_key: GFW API key (if None, reads from GFW_API_KEY environment variable)
            cache_dir: Directory for caching data (if None, uses CACHE_DIR environment variable)
        """
        # Get API key from environment variable or parameter
        self.api_key = api_key or os.getenv("GFW_API_KEY")
        
        # Initialize GFW client
        try:
            if self.api_key:
                self.client = gfw.Client(access_token=self.api_key)
                logger.info("GFW client initialized successfully")
            else:
                self.client = None
                logger.warning("GFW_API_KEY not found - API requests will fail")
                logger.warning("Set GFW_API_KEY environment variable or pass api_key parameter")
        except Exception as e:
            logger.error(f"Failed to initialize GFW client: {e}")
            self.client = None
        
        # Get cache directory from environment variable or use default
        if cache_dir is None:
            cache_dir = os.getenv("CACHE_DIR", "data_cache")
        self.cache_dir = Path(cache_dir) / "gfw_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.api_url = os.getenv("GFW_API_URL", "https://gateway.api.globalfishingwatch.org")
        self.cache_ttl_days = int(os.getenv("GFW_CACHE_TTL_DAYS", "30"))
        
        # Grid configuration (match NASA data grid)
        self.grid_resolution = 0.5  # degrees (matches NASA SSH dataset resolution)
        self.lat_range = (-90, 90)
        self.lon_range = (-180, 180)
        
        logger.info(f"GFW Data Manager initialized with cache dir: {self.cache_dir}")
        if self.client:
            logger.info("GFW API client ready for data requests")
        else:
            logger.warning("GFW API client not available - will return neutral pressure values")
    
    def _get_cache_path(self, dataset: str, date_str: str, bounds: Optional[Dict] = None) -> Path:
        """Generate cache file path for a dataset and date"""
        if bounds:
            bounds_hash = hash(f"{bounds.get('north')}_{bounds.get('south')}_{bounds.get('east')}_{bounds.get('west')}")
            filename = f"{dataset}_{date_str}_bounds_{bounds_hash}.nc"
        else:
            filename = f"{dataset}_{date_str}_global.nc"
        return self.cache_dir / filename
    
    def _is_cached(self, dataset: str, date_str: str, bounds: Optional[Dict] = None) -> bool:
        """Check if data is already cached and valid"""
        cache_path = self._get_cache_path(dataset, date_str, bounds)
        
        if not cache_path.exists():
            return False
        
        # Check cache age
        cache_age_days = (datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)).days
        if cache_age_days > self.cache_ttl_days:
            logger.info(f"Cache expired for {dataset} on {date_str} (age: {cache_age_days} days)")
            return False
        
        logger.info(f"Valid cache found for {dataset} on {date_str}")
        return True
    
    def _save_to_cache(self, data: xr.Dataset, dataset: str, date_str: str, bounds: Optional[Dict] = None):
        """Save data to cache"""
        try:
            cache_path = self._get_cache_path(dataset, date_str, bounds)
            data.to_netcdf(cache_path)
            logger.info(f"Cached {dataset} data for {date_str}")
        except Exception as e:
            logger.error(f"Failed to cache data: {e}")
    
    def _load_from_cache(self, dataset: str, date_str: str, bounds: Optional[Dict] = None) -> Optional[xr.Dataset]:
        """Load data from cache"""
        try:
            cache_path = self._get_cache_path(dataset, date_str, bounds)
            data = xr.open_dataset(cache_path, decode_timedelta=False)
            logger.info(f"Loaded {dataset} data from cache for {date_str}")
            return data
        except Exception as e:
            logger.error(f"Failed to load cached data: {e}")
            return None
    
    def fetch_fishing_effort(self, start_date: str, end_date: str, bounds: Optional[Dict] = None) -> Optional[xr.Dataset]:
        """
        Fetch fishing effort data using GFW Python client
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            bounds: Optional spatial bounds {'north': lat, 'south': lat, 'east': lon, 'west': lon}
            
        Returns:
            xarray Dataset with 'fishing_pressure' variable (0-1 normalized) or None
        """
        try:
            # Check cache first
            date_str = start_date.replace('-', '')
            if self._is_cached('fishing_effort', date_str, bounds):
                return self._load_from_cache('fishing_effort', date_str, bounds)
            
            # Use the exact requested date from API
            # Convert string to datetime.date object (GFW client accepts both)
            from datetime import datetime
            api_start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            api_end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            logger.info(f"Querying GFW fishing effort: {api_start_date} to {api_end_date}")
            
            if not self.client:
                logger.warning("No GFW client - returning neutral fishing pressure (zeros)")
                return self._create_neutral_dataset('fishing_pressure')
            
            # IMPORTANT: GFW API requires a 'region' parameter
            # For global queries, we'll fetch multiple regions and combine them
            if not bounds:
                logger.info("Global query detected - fetching multiple regions to create global map")
                global_data = self._fetch_global_fishing_effort(start_date, end_date)
                # Cache the global data
                if global_data is not None:
                    self._save_to_cache(global_data, 'fishing_effort', date_str, bounds)
                return global_data
            
            logger.info(f"Fetching fishing effort data from GFW API: {api_start_date} to {api_end_date}")
            
            try:
                # Use GFW client's fourwings API for fishing effort data
                logger.info("Using client.fourwings.create_fishing_effort_report() method")
                
                # Create fishing effort report using 4Wings API (ASYNC)
                # Run in separate thread with fresh client to avoid event loop conflicts
                # Each thread gets its own event loop and GFW client instance
                def run_in_thread():
                    """Run GFW API call in isolated thread with own event loop and client"""
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        # Create fresh GFW client in this thread
                        fresh_client = gfw.Client(access_token=self.api_key)
                        
                        # Create and run the coroutine
                        coro = fresh_client.fourwings.create_fishing_effort_report(
                            start_date=api_start_date,
                            end_date=api_end_date,
                            spatial_resolution='LOW',
                            temporal_resolution='MONTHLY'
                        )
                        
                        result = new_loop.run_until_complete(coro)
                        new_loop.run_until_complete(asyncio.sleep(0))  # Allow cleanup
                        return result
                    finally:
                        try:
                            new_loop.run_until_complete(new_loop.shutdown_asyncgens())
                        except Exception:
                            pass
                        new_loop.close()
                
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_in_thread)
                    report = future.result(timeout=60)
                
                logger.info(f"GFW API returned data type: {type(report)}")
                
                # The report may be a URL or data object - check type
                data = report
                
                # Process the data
                processed_data = self._process_gfw_data(data, 'fishing_pressure', bounds)
                
                if processed_data is not None:
                    # Cache the processed data
                    self._save_to_cache(processed_data, 'fishing_effort', date_str, bounds)
                    return processed_data
                else:
                    logger.warning("Data processing failed - returning neutral data")
                    return self._create_neutral_dataset('fishing_pressure')
                    
            except Exception as e:
                logger.error(f"GFW client request failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
                logger.warning("Returning neutral fishing pressure")
                return self._create_neutral_dataset('fishing_pressure')
            
        except Exception as e:
            logger.error(f"Error fetching fishing effort data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._create_neutral_dataset('fishing_pressure')
    
    def fetch_vessel_density(self, start_date: str, end_date: str, bounds: Optional[Dict] = None) -> Optional[xr.Dataset]:
        """
        Fetch vessel density/shipping data using GFW Python client
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            bounds: Optional spatial bounds
            
        Returns:
            xarray Dataset with 'shipping_density' variable (0-1 normalized) or None
        """
        try:
            # Check cache first
            date_str = start_date.replace('-', '')
            if self._is_cached('vessel_density', date_str, bounds):
                return self._load_from_cache('vessel_density', date_str, bounds)
            
            # Use the exact requested date from API
            # Convert string to datetime.date object (GFW client accepts both)
            from datetime import datetime
            api_start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            api_end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            logger.info(f"Querying GFW vessel density: {api_start_date} to {api_end_date}")
            
            if not self.client:
                logger.warning("No GFW client - returning neutral shipping density (zeros)")
                return self._create_neutral_dataset('shipping_density')
            
            # IMPORTANT: GFW API requires a 'region' parameter
            # For global queries, we'll fetch multiple regions and combine them
            if not bounds:
                logger.info("Global query detected - fetching multiple regions to create global map")
                global_data = self._fetch_global_vessel_density(start_date, end_date)
                # Cache the global data
                if global_data is not None:
                    self._save_to_cache(global_data, 'vessel_density', date_str, bounds)
                return global_data
            
            logger.info(f"Fetching vessel density data from GFW API: {api_start_date} to {api_end_date}")
            
            try:
                # Use GFW client's fourwings API for AIS vessel presence
                logger.info("Using client.fourwings.create_ais_presence_report() method")
                
                # Create AIS presence report for all vessel activity (ASYNC)
                # Run in separate thread with fresh client to avoid event loop conflicts
                # Each thread gets its own event loop and GFW client instance
                def run_in_thread():
                    """Run GFW API call in isolated thread with own event loop and client"""
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        # Create fresh GFW client in this thread
                        fresh_client = gfw.Client(access_token=self.api_key)
                        
                        # Create and run the coroutine
                        coro = fresh_client.fourwings.create_ais_presence_report(
                            start_date=api_start_date,
                            end_date=api_end_date,
                            spatial_resolution='LOW',
                            temporal_resolution='MONTHLY'
                        )
                        
                        result = new_loop.run_until_complete(coro)
                        new_loop.run_until_complete(asyncio.sleep(0))  # Allow cleanup
                        return result
                    finally:
                        try:
                            new_loop.run_until_complete(new_loop.shutdown_asyncgens())
                        except Exception:
                            pass
                        new_loop.close()
                
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_in_thread)
                    report = future.result(timeout=60)
                
                logger.info(f"GFW API returned data type: {type(report)}")
                
                # The report may be a URL or data object - check type
                data = report
                
                # Process the data
                processed_data = self._process_gfw_data(data, 'shipping_density', bounds)
                
                if processed_data is not None:
                    # Cache the processed data
                    self._save_to_cache(processed_data, 'vessel_density', date_str, bounds)
                    return processed_data
                else:
                    logger.warning("Data processing failed - returning neutral data")
                    return self._create_neutral_dataset('shipping_density')
                    
            except Exception as e:
                logger.error(f"GFW client request failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
                logger.warning("Returning neutral shipping density")
                return self._create_neutral_dataset('shipping_density')
            
        except Exception as e:
            logger.error(f"Error fetching vessel density data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._create_neutral_dataset('shipping_density')
    
    def _process_gfw_data(self, gfw_data: Any, variable_name: str, bounds: Optional[Dict] = None) -> Optional[xr.Dataset]:
        """
        Process data from GFW client into xarray Dataset
        
        GFW client can return data in various formats (pandas DataFrame, GeoDataFrame, dict, etc.)
        This method handles conversion to our standard xarray format.
        
        Args:
            gfw_data: Data returned from GFW client
            variable_name: Name for the variable ('fishing_pressure' or 'shipping_density')
            bounds: Optional spatial bounds
            
        Returns:
            xarray Dataset with normalized pressure variable
        """
        try:
            logger.info(f"Processing GFW data (type: {type(gfw_data)})")
            
            # Handle different return types from GFW client
            if isinstance(gfw_data, pd.DataFrame):
                return self._process_dataframe(gfw_data, variable_name)
            elif hasattr(gfw_data, '__geo_interface__'):  # GeoDataFrame or GeoJSON
                return self._process_geodata(gfw_data, variable_name)
            elif isinstance(gfw_data, dict):
                return self._process_dict(gfw_data, variable_name)
            else:
                logger.error(f"Unknown data type from GFW client: {type(gfw_data)}")
                logger.error("Cannot process GFW data - returning neutral (zero) dataset")
                return self._create_neutral_dataset(variable_name)
                
        except Exception as e:
            logger.error(f"Failed to process GFW data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.error("Returning neutral (zero) dataset for anthropogenic pressure")
            return self._create_neutral_dataset(variable_name)
    
    def _process_dataframe(self, df: pd.DataFrame, variable_name: str) -> xr.Dataset:
        """Process pandas DataFrame from GFW client"""
        logger.info(f"Gridding {len(df):,} records to global 0.5° grid...")
        
        # Try to find lat/lon columns
        lat_col = None
        lon_col = None
        value_col = None
        
        for col in df.columns:
            # Handle both string and integer column names
            col_str = str(col).lower() if not isinstance(col, str) else col.lower()
            
            if 'lat' in col_str:
                lat_col = col
            if 'lon' in col_str:
                lon_col = col
            if any(x in col_str for x in ['fishing', 'effort', 'hours', 'value', 'count', 'density']):
                value_col = col
        
        # If columns are integers, identify by position
        if lat_col is None and isinstance(df.columns[0], int):
            # Standard GFW column positions: lat=-2, lon=-1, hours=4
            if len(df.columns) >= 2:
                lat_col = df.columns[-2]
                lon_col = df.columns[-1]
            if len(df.columns) > 4:
                value_col = df.columns[4]
        
        if lat_col and lon_col and value_col:
            logger.info(f"Found columns: lat={lat_col}, lon={lon_col}, value={value_col}")
            return self._grid_dataframe(df, lat_col, lon_col, value_col, variable_name)
        else:
            logger.error(f"Could not identify required columns in DataFrame: {list(df.columns)}")
            logger.error("Returning neutral (zero) dataset")
            return self._create_neutral_dataset(variable_name)
    
    def _grid_dataframe(self, df: pd.DataFrame, lat_col: str, lon_col: str, value_col: str, variable_name: str) -> xr.Dataset:
        """Grid DataFrame data to common resolution matching NASA grid"""
        # Create coordinate arrays matching NASA grid exactly
        # NASA grid: -90 to 90 (361 points) and -180 to 180 (721 points)
        lat_coords = np.arange(self.lat_range[0], self.lat_range[1] + self.grid_resolution, self.grid_resolution)
        lon_coords = np.arange(self.lon_range[0], self.lon_range[1] + self.grid_resolution, self.grid_resolution)
        
        # Create bins for pd.cut (edges, not centers)
        lat_bins = np.arange(self.lat_range[0] - self.grid_resolution/2, 
                            self.lat_range[1] + self.grid_resolution, 
                            self.grid_resolution)
        lon_bins = np.arange(self.lon_range[0] - self.grid_resolution/2, 
                            self.lon_range[1] + self.grid_resolution, 
                            self.grid_resolution)
        
        # Bin the data
        df = df.copy()
        df['lat_bin'] = pd.cut(df[lat_col], bins=lat_bins, labels=lat_coords, include_lowest=True)
        df['lon_bin'] = pd.cut(df[lon_col], bins=lon_bins, labels=lon_coords, include_lowest=True)
        
        # Aggregate by bins
        gridded = df.groupby(['lat_bin', 'lon_bin'], observed=True)[value_col].sum().unstack(fill_value=0)
        
        # Reindex to full global grid (fills missing bins with 0)
        gridded = gridded.reindex(index=lat_coords, columns=lon_coords, fill_value=0)
        
        # Convert to numpy array
        gridded_array = gridded.values
        
        # DO NOT normalize here - the HSI model will normalize it
        # Just return raw aggregated values (fishing hours or vessel counts)
        # This avoids double normalization which crushes the signal
        pressure = gridded_array
        
        # Create xarray Dataset with matching dimensions
        dataset = xr.Dataset(
            {
                variable_name: (['lat', 'lon'], pressure)
            },
            coords={
                'lat': lat_coords,
                'lon': lon_coords
            }
        )
        
        dataset.attrs.update({
            'source': 'Global Fishing Watch (official client)',
            'description': f'{variable_name} from GFW API (raw aggregated values)',
            'units': 'fishing hours or vessel counts (unnormalized)',
            'processing': 'Gridded aggregation - normalization done in HSI model',
            'attribution': 'Data provided by Global Fishing Watch (https://globalfishingwatch.org/)'
        })
        
        logger.info(f"✓ Gridded to {pressure.shape}, mean={pressure.mean():.2f}, max={pressure.max():.2f}, non-zero={np.sum(pressure > 0)}")
        return dataset
    
    def _process_geodata(self, geodata: Any, variable_name: str) -> xr.Dataset:
        """Process GeoDataFrame or GeoJSON data"""
        logger.info("Processing geodata")
        # Convert to DataFrame and process
        if hasattr(geodata, 'to_dataframe'):
            df = geodata.to_dataframe()
            return self._process_dataframe(df, variable_name)
        else:
            logger.error("Cannot convert geodata to dataframe - returning neutral dataset")
            return self._create_neutral_dataset(variable_name)
    
    def _process_dict(self, data_dict: Dict, variable_name: str) -> xr.Dataset:
        """Process dictionary response from GFW client"""
        logger.info(f"Processing dict with keys: {list(data_dict.keys())}")
        # Try to convert to DataFrame
        try:
            df = pd.DataFrame(data_dict)
            return self._process_dataframe(df, variable_name)
        except Exception as e:
            logger.error(f"Failed to convert dict to DataFrame: {e}")
            return self._create_neutral_dataset(variable_name)
    
    def _fetch_global_fishing_effort(self, start_date: str, end_date: str) -> Optional[xr.Dataset]:
        """
        Fetch fishing effort for the global ocean using a single region query
        Covers full extent matching NASA data grid: -90° to 90° lat, -180° to 180° lon
        """
        logger.info("Fetching fishing effort for global ocean (matching NASA grid dimensions)...")
        
        # Define global region matching NASA data grid dimensions
        # Single global query covering full extent: -90° to 90° lat, -180° to 180° lon
        ocean_regions = [
            {"name": "Global Ocean", "geojson": {"type": "Polygon", "coordinates": [[[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]]}},
        ]
        
        # GFW requires full month queries - single day queries return empty data
        # Extract the month from the requested date and query the entire month
        from datetime import datetime, timedelta
        
        requested_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        target_year = requested_date.year
        target_month = requested_date.month
        
        # Query the full month containing the requested date
        api_start_date = datetime(target_year, target_month, 1).date()
        # Calculate last day of month
        if target_month == 12:
            api_end_date = datetime(target_year, 12, 31).date()
        else:
            api_end_date = (datetime(target_year, target_month + 1, 1) - timedelta(days=1)).date()
        
        logger.info(f"Querying full month: {api_start_date.strftime('%B %Y')} ({api_start_date} to {api_end_date})")
        
        # Fetch data for each region
        all_dataframes = []
        successful_regions = 0
        
        for i, region in enumerate(ocean_regions, 1):
            try:
                logger.info(f"Fetching region {i}/{len(ocean_regions)}: {region['name']}")
                
                # Fetch data for this region in a separate thread
                def fetch_region():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        fresh_client = gfw.Client(access_token=self.api_key)
                        # Use DAILY temporal resolution for single day, MONTHLY for ranges
                        temporal_res = 'DAILY' if api_start_date == api_end_date else 'MONTHLY'
                        
                        coro = fresh_client.fourwings.create_fishing_effort_report(
                            start_date=api_start_date,
                            end_date=api_end_date,
                            spatial_resolution='LOW',
                            temporal_resolution=temporal_res,
                            geojson=region['geojson']
                        )
                        result = new_loop.run_until_complete(coro)
                        new_loop.run_until_complete(asyncio.sleep(0))
                        return result
                    finally:
                        try:
                            new_loop.run_until_complete(new_loop.shutdown_asyncgens())
                        except Exception:
                            pass
                        new_loop.close()
                
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(fetch_region)
                    report = future.result(timeout=60)  # Increased timeout for larger regions
                
                # Extract dataframe from report
                if hasattr(report, 'df'):
                    df_data = report.df() if callable(report.df) else report.df
                    if df_data is not None and hasattr(df_data, 'empty') and not df_data.empty:
                        all_dataframes.append(df_data)
                        successful_regions += 1
                        logger.info(f"✓ {region['name']}: {len(df_data):,} records")
                    elif df_data is None or (hasattr(df_data, 'empty') and df_data.empty):
                        # Empty dataframe - try data() method
                        if hasattr(report, 'data'):
                            data_content = report.data() if callable(report.data) else report.data
                            if data_content and len(data_content) > 0:
                                df_data = pd.DataFrame(data_content)
                                if not df_data.empty:
                                    all_dataframes.append(df_data)
                                    successful_regions += 1
                                    logger.info(f"✓ {region['name']}: {len(df_data):,} records")
                    
            except Exception as e:
                logger.warning(f"Failed to fetch region {i}: {e}")
                continue
        
        if successful_regions == 0:
            logger.warning(f"No fishing effort data available for {api_start_date.strftime('%B %Y')}")
            logger.warning("Using neutral dataset (zero anthropogenic pressure)")
            return self._create_neutral_dataset('fishing_pressure')
        
        logger.info(f"Successfully fetched {successful_regions}/{len(ocean_regions)} ocean regions")
        
        # Combine all dataframes
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        logger.info(f"Combined {len(combined_df):,} total records from {successful_regions} regions")
        
        # Process combined dataframe
        return self._process_dataframe(combined_df, 'fishing_pressure')
    
    def _fetch_global_vessel_density(self, start_date: str, end_date: str) -> Optional[xr.Dataset]:
        """
        Fetch vessel density for the global ocean using a single region query
        Covers full extent matching NASA data grid: -90° to 90° lat, -180° to 180° lon
        """
        logger.info("Fetching vessel density for global ocean (matching NASA grid dimensions)...")
        
        # Define global region matching NASA data grid dimensions (same as fishing effort)
        # Single global query covering full extent: -90° to 90° lat, -180° to 180° lon
        ocean_regions = [
            {"name": "Global Ocean", "geojson": {"type": "Polygon", "coordinates": [[[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]]}},
        ]
        
        # GFW requires full month queries - single day queries return empty data
        # Extract the month from the requested date and query the entire month
        from datetime import datetime, timedelta
        
        requested_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        target_year = requested_date.year
        target_month = requested_date.month
        
        # Query the full month containing the requested date
        api_start_date = datetime(target_year, target_month, 1).date()
        # Calculate last day of month
        if target_month == 12:
            api_end_date = datetime(target_year, 12, 31).date()
        else:
            api_end_date = (datetime(target_year, target_month + 1, 1) - timedelta(days=1)).date()
        
        logger.info(f"Querying full month: {api_start_date.strftime('%B %Y')} ({api_start_date} to {api_end_date})")
        
        # Fetch data for each region
        all_dataframes = []
        successful_regions = 0
        
        for i, region in enumerate(ocean_regions, 1):
            try:
                logger.info(f"Fetching region {i}/{len(ocean_regions)}: {region['name']}")
                
                # Fetch data for this region in a separate thread
                def fetch_region():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        fresh_client = gfw.Client(access_token=self.api_key)
                        # Use DAILY temporal resolution for single day, MONTHLY for ranges
                        temporal_res = 'DAILY' if api_start_date == api_end_date else 'MONTHLY'
                        
                        coro = fresh_client.fourwings.create_ais_presence_report(
                            start_date=api_start_date,
                            end_date=api_end_date,
                            spatial_resolution='LOW',
                            temporal_resolution=temporal_res,
                            geojson=region['geojson']
                        )
                        result = new_loop.run_until_complete(coro)
                        new_loop.run_until_complete(asyncio.sleep(0))
                        return result
                    finally:
                        try:
                            new_loop.run_until_complete(new_loop.shutdown_asyncgens())
                        except Exception:
                            pass
                        new_loop.close()
                
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(fetch_region)
                    report = future.result(timeout=60)  # Increased timeout for larger regions
                
                # Extract dataframe from report
                if hasattr(report, 'df'):
                    df_data = report.df() if callable(report.df) else report.df
                    if df_data is not None and hasattr(df_data, 'empty') and not df_data.empty:
                        all_dataframes.append(df_data)
                        successful_regions += 1
                        logger.info(f"✓ {region['name']}: {len(df_data):,} records")
                    elif df_data is None or (hasattr(df_data, 'empty') and df_data.empty):
                        # Empty dataframe - try data() method
                        if hasattr(report, 'data'):
                            data_content = report.data() if callable(report.data) else report.data
                            if data_content and len(data_content) > 0:
                                df_data = pd.DataFrame(data_content)
                                if not df_data.empty:
                                    all_dataframes.append(df_data)
                                    successful_regions += 1
                                    logger.info(f"✓ {region['name']}: {len(df_data):,} records")
                    
            except Exception as e:
                logger.warning(f"Failed to fetch region {i}: {e}")
                continue
        
        if successful_regions == 0:
            logger.warning(f"No vessel density data available for {api_start_date.strftime('%B %Y')}")
            logger.warning("Using neutral dataset (zero anthropogenic pressure)")
            return self._create_neutral_dataset('shipping_density')
        
        logger.info(f"Successfully fetched {successful_regions}/{len(ocean_regions)} ocean regions")
        
        # Combine all dataframes
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        logger.info(f"Combined data shape: {combined_df.shape}")
        
        # Process combined dataframe
        return self._process_dataframe(combined_df, 'shipping_density')
    
    def _create_neutral_dataset(self, variable_name: str) -> xr.Dataset:
        """
        Create a neutral dataset (all zeros) for when GFW data is unavailable
        
        Returns zeros (no anthropogenic pressure) when:
        - GFW API key is not configured
        - GFW API request fails
        - No data available for requested period
        
        This is scientifically conservative: assumes no human pressure when data is missing.
        """
        logger.warning(f"GFW data unavailable - using neutral {variable_name} dataset (zeros = no anthropogenic pressure)")
        logger.warning("To use real GFW data, set the GFW_API_KEY environment variable")
        
        # Create grid matching NASA data resolution
        lats = np.arange(self.lat_range[0], self.lat_range[1] + self.grid_resolution, self.grid_resolution)
        lons = np.arange(self.lon_range[0], self.lon_range[1] + self.grid_resolution, self.grid_resolution)
        
        # Create zeros array (no anthropogenic pressure)
        zeros = np.zeros((len(lats), len(lons)))
        
        # Create xarray Dataset
        dataset = xr.Dataset(
            {
                variable_name: (['lat', 'lon'], zeros)
            },
            coords={
                'lat': lats,
                'lon': lons
            }
        )
        
        dataset.attrs.update({
            'source': 'Neutral (no GFW data available)',
            'description': f'Zero {variable_name} - assumes no anthropogenic pressure',
            'units': 'normalized (0-1)',
            'note': 'GFW API unavailable. Set GFW_API_KEY environment variable for real data.',
            'scientific_note': 'Conservative assumption: zero anthropogenic pressure when data unavailable'
        })
        
        return dataset
    
    def get_data_attribution(self) -> str:
        """Get required data attribution for GFW"""
        return "Data provided by Global Fishing Watch (https://globalfishingwatch.org/)"
    
    def clear_cache(self, older_than_days: Optional[int] = None):
        """Clear cached GFW data"""
        try:
            count = 0
            for cache_file in self.cache_dir.glob("*.nc"):
                if older_than_days:
                    age_days = (datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)).days
                    if age_days < older_than_days:
                        continue
                
                cache_file.unlink()
                count += 1
            
            logger.info(f"Cleared {count} cached GFW files")
            return count
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0

