"""
NASA Data Access Module using earthaccess
Handles authentication, searching, and downloading of NASA datasets

🚀 NASA Space Apps Challenge 2025 - Sharks from Space
This module integrates NASA Earthdata Cloud for satellite-based shark habitat prediction.
Demonstrates real-time satellite data processing for marine conservation applications.

Challenge URL: https://www.spaceappschallenge.org/2025/challenges/sharks-from-space/
"""

import earthaccess
import xarray as xr
import numpy as np
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
from pathlib import Path
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NASADataManager:
    """Manages NASA Earthdata access and local caching"""
    
    def __init__(self, cache_dir: Optional[str] = None):
        # Get cache directory from environment variable or use default
        if cache_dir is None:
            cache_dir = os.getenv("CACHE_DIR", "data_cache")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # NASA dataset short names and configurations
        self.datasets = {
            'chlorophyll': {
                'short_name': 'PACE_OCI_L3M_CHL',
                'description': 'Level-3 Binned Mapped Chlorophyll-a Concentration (Monthly Composite)',
                'variable': 'chlor_a',
                'units': 'mg/m³'
            },
            'sea_level': {
                'short_name': 'NASA_SSH_REF_SIMPLE_GRID_V1',
                'description': 'NASA SSH Simple Gridded Sea Surface Height from Standardized Reference Missions Only Version 1',
                'variable': 'ssha',
                'units': 'm',
                'coverage_note': 'Limited coverage in western hemisphere due to satellite tracks and ocean basin separation logic',
                'temporal_resolution': '7 days',
                'spatial_resolution': '0.5 degrees',
                'oceanographic_features': {
                    'eddy_detection': 'Primary source for detecting mesoscale eddies (50-300 km)',
                    'front_detection': 'Identifies ocean fronts through spatial gradient analysis',
                    'data_quality': 'Basin-aware processing, quality flags (nasa_flag=0, median_filter_flag=0)',
                    'satellite_mission': 'TOPEX/Poseidon, Jason series, Sentinel-6',
                    'processing_method': '10-day observations with Gaussian weighted spatial averaging (100 km width)'
                }
            },
            'sst': {
                'short_name': 'VIIRSN_L3m_SST3',
                'description': 'VIIRS NPP Level-3 mapped Sea Surface Temperature (SST)',
                'variable': 'sst_triple',
                'units': '°C'
            },
            'salinity': {
                'short_name': 'OISSS_L4_multimission_monthly_v2',
                'description': 'Multi-Mission Optimally Interpolated Sea Surface Salinity Global Monthly Dataset V2',
                'variable': 'sss',
                'units': 'psu',
                'temporal_resolution': 'monthly',
                'spatial_resolution': '0.25 degrees',
                'coverage_note': 'Global coverage with monthly composites for stable salinity patterns',
                'shark_habitat_filtering': {
                    'bull_shark_range': (0.5, 35.0),
                    'great_white_shark_range': (30.0, 37.0),
                    'tiger_shark_range': (30.0, 37.0),
                    'spiny_dogfish_minimum': 21.0,
                    'default_minimum': 30.0
                }
            }
        }
        
        # Global grid parameters
        self.grid_resolution = 0.25  # degrees
        self.lat_range = (-90, 90)
        self.lon_range = (-180, 180)
        
        
        # Check if authenticated
        self._check_auth()
    
    def _check_auth(self):
        """Check if user is authenticated with NASA Earthdata"""
        try:
            # Check if .netrc file exists or environment variables are set
            import os
            from pathlib import Path
            
            # Check for .netrc file
            netrc_path = Path.home() / ".netrc"
            if netrc_path.exists():
                logger.info("Found .netrc file for NASA Earthdata authentication")
                return
            
            # Check for environment variables
            if os.getenv('EARTHDATA_USERNAME') and os.getenv('EARTHDATA_PASSWORD'):
                logger.info("Found NASA Earthdata credentials in environment variables")
                return
            
            # If neither exists, show authentication instructions
            logger.info("NASA Earthdata authentication not configured.")
            logger.info("To authenticate, run: python -c \"import earthaccess; earthaccess.login()\"")
            logger.info("Or set EARTHDATA_USERNAME and EARTHDATA_PASSWORD environment variables")
            logger.info("Or create a .netrc file with your credentials")
            
        except Exception as e:
            logger.warning(f"Authentication check failed: {e}")
            logger.info("To authenticate, run: python -c \"import earthaccess; earthaccess.login()\"")
    
    def authenticate(self, username: Optional[str] = None, password: Optional[str] = None):
        """Authenticate with NASA Earthdata Login"""
        try:
            if username and password:
                # Use environment variables for authentication
                import os
                os.environ['EARTHDATA_USERNAME'] = username
                os.environ['EARTHDATA_PASSWORD'] = password
                auth = earthaccess.login(strategy="environment")
            else:
                # Use interactive login or netrc file
                auth = earthaccess.login()
            
            if auth:
                logger.info("Successfully authenticated with NASA Earthdata")
                return True
            else:
                logger.error("Authentication failed - no auth object returned")
                return False
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def _get_cache_path(self, dataset: str, date_str: str) -> Path:
        """Generate cache file path for a dataset and date"""
        filename = f"{dataset}_{date_str}.nc"
        return self.cache_dir / filename
    
    def _is_cached(self, dataset: str, date_str: str) -> bool:
        """Check if data is already cached"""
        cache_path = self.cache_dir / f"{dataset}_{date_str}.nc"
        return cache_path.exists()
    
    def _save_to_cache(self, data: xr.Dataset, dataset: str, date_str: str):
        """Save data to cache"""
        cache_path = self.cache_dir / f"{dataset}_{date_str}.nc"
        data.to_netcdf(cache_path)
        logger.info(f"Cached {dataset} data for {date_str}")
    
    def _load_from_cache(self, dataset: str, date_str: str) -> Optional[xr.Dataset]:
        """Load data from cache"""
        cache_path = self.cache_dir / f"{dataset}_{date_str}.nc"
        try:
            data = xr.open_dataset(cache_path, decode_timedelta=False)
            logger.info(f"Loaded {dataset} data from cache for {date_str}")
            return data
        except Exception as e:
            logger.error(f"Failed to load cached data: {e}")
            return None
    
    def search_data(self, dataset: str, start_date: str, end_date: str) -> List[Dict]:
        """Search for data granules"""
        try:
            dataset_config = self.datasets.get(dataset)
            if not dataset_config:
                raise ValueError(f"Unknown dataset: {dataset}")
            
            short_name = dataset_config['short_name']
            logger.info(f"Searching for {dataset} data using short_name: {short_name}")
            logger.info(f"Date range: {start_date} to {end_date}")
            
            # Add specific search parameters for each dataset
            search_params = {
                'short_name': short_name,
                'temporal': (start_date, end_date),
                'count': 10
            }
            
            # Add dataset-specific parameters
            if dataset == 'chlorophyll':
                # Prefer monthly composite for chlorophyll
                search_params['cloud_hosted'] = True
                logger.info("Added cloud_hosted=True for chlorophyll search")
            elif dataset == 'sst':
                # VIIRS SST is a daily mapped product, so we can be more specific
                search_params['cloud_hosted'] = True
                logger.info("Added cloud_hosted=True for VIIRS SST search")
            elif dataset == 'sea_level':
                # NASA-SSH L4 specific parameters
                search_params['cloud_hosted'] = True
                logger.info("Added cloud_hosted=True for NASA-SSH L4 sea level search")
                # NASA-SSH L4 has 7-day temporal resolution
                logger.info("Note: NASA-SSH L4 has 7-day temporal resolution")
            elif dataset == 'salinity':
                # OISSS L4 salinity specific parameters
                search_params['cloud_hosted'] = True
                logger.info("Added cloud_hosted=True for OISSS L4 salinity search")
                # OISSS L4 has monthly temporal resolution
                logger.info("Note: OISSS L4 has monthly temporal resolution")
            
            logger.info(f"Search parameters: {search_params}")
            results = earthaccess.search_data(**search_params)
            
            logger.info(f"Found {len(results)} granules for {dataset}")
            
            # Log details about found granules
            if results:
                for i, granule in enumerate(results[:3]):  # Show first 3 granules
                    logger.info(f"Granule {i+1}: {granule.get('title', 'Unknown title')}")
                    logger.info(f"  - Temporal: {granule.get('time_start', 'Unknown start')} to {granule.get('time_end', 'Unknown end')}")
                    logger.info(f"  - Size: {granule.get('size', 'Unknown size')}")
            else:
                logger.warning(f"No granules found for {dataset} in date range {start_date} to {end_date}")
                # Try a broader search for sea level data
                if dataset == 'sea_level':
                    logger.info("Attempting broader search for sea level data...")
                    broader_params = {
                        'short_name': short_name,
                        'temporal': (start_date, end_date),
                        'count': 50  # Search more broadly
                    }
                    broader_results = earthaccess.search_data(**broader_params)
                    logger.info(f"Broader search found {len(broader_results)} granules")
                    
                    if broader_results:
                        logger.info("Available sea level data dates:")
                        for granule in broader_results[:10]:  # Show first 10
                            start_time = granule.get('time_start', 'Unknown')
                            end_time = granule.get('time_end', 'Unknown')
                            logger.info(f"  - {start_time} to {end_time}")
            
            return results
        except Exception as e:
            logger.error(f"Search failed for {dataset}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def download_data(self, dataset: str, target_date: str, geographic_bounds: Dict = None) -> Optional[xr.Dataset]:
        """Download and process data for a specific date"""
        # For salinity, use a generic cache key since it's time-insensitive
        if dataset == 'salinity':
            date_str = 'latest'  # Use generic cache key for salinity
            logger.info(f"Starting download for {dataset} (using latest available data)")
        else:
            date_str = target_date.replace('-', '')
            logger.info(f"Starting download for {dataset} on {target_date}")
        
        # Check cache first (by date only since datasets are global)
        if self._is_cached(dataset, date_str):
            logger.info(f"Using cached data for {dataset} on {target_date}")
            cached_data = self._load_from_cache(dataset, date_str)
            
            # Apply geographic filtering to cached data if bounds provided
            if geographic_bounds and cached_data is not None:
                cached_data = self._apply_geographic_filter(cached_data, geographic_bounds)
                logger.info(f"Applied geographic filtering to cached {dataset} data")
            
            return cached_data
        
        try:
            # Search for data around the target date
            # Adjust search window based on dataset temporal resolution
            if dataset == 'sea_level':
                # NASA-SSH L4 has 7-day temporal resolution
                search_window = 7
            elif dataset == 'salinity':
                # OISSS L4 has monthly temporal resolution - use hardcoded latest available date
                # Salinity is relatively stable, and OISSS L4 data is typically 1-2 years behind
                # Use a known good date from 2022 when data is reliably available
                target_date = "2022-12-01"  # December 2022 - typically latest reliable OISSS L4 data
                logger.info(f"Using hardcoded latest date for salinity: {target_date}")
                search_window = 90  # Wider search window for monthly data
            else:
                # Default 7-day window for other datasets
                search_window = 7
            
            start_date = (datetime.strptime(target_date, '%Y-%m-%d') - timedelta(days=search_window)).strftime('%Y-%m-%d')
            end_date = (datetime.strptime(target_date, '%Y-%m-%d') + timedelta(days=search_window)).strftime('%Y-%m-%d')
            
            logger.info(f"Searching for {dataset} data in range: {start_date} to {end_date} (window: ±{search_window} days)")
            results = self.search_data(dataset, start_date, end_date)
            
            if not results:
                logger.warning(f"No data found for {dataset} on {target_date}")
                # For sea level data, try a much broader search
                if dataset == 'sea_level':
                    logger.info("Attempting much broader search for sea level data (30 days range)...")
                    broader_start = (datetime.strptime(target_date, '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d')
                    broader_end = (datetime.strptime(target_date, '%Y-%m-%d') + timedelta(days=30)).strftime('%Y-%m-%d')
                    broader_results = self.search_data(dataset, broader_start, broader_end)
                    if broader_results:
                        logger.info(f"Found {len(broader_results)} granules in broader search")
                        results = broader_results
                    else:
                        logger.error("No sea level data found even with broader search")
                        return None
                else:
                    return None
            
            # Download the closest match
            granule = results[0]  # Take the first result for now
            logger.info(f"Selected granule for download: {granule.get('title', 'Unknown title')}")
            logger.info(f"Granule temporal coverage: {granule.get('time_start', 'Unknown')} to {granule.get('time_end', 'Unknown')}")
            
            # Download to temporary location
            temp_dir = self.cache_dir / "temp"
            temp_dir.mkdir(exist_ok=True)
            
            logger.info(f"Downloading to: {temp_dir}")
            files = earthaccess.download([granule], local_path=str(temp_dir))
            
            if files:
                # Load the downloaded file
                file_path = files[0]
                
                try:
                    # Open dataset with context manager to ensure proper cleanup
                    with xr.open_dataset(file_path, decode_timedelta=False) as data:
                        # Process and regrid the data
                        processed_data = self._process_data(data, dataset)
                        
                        # Save to cache (by date only since datasets are global)
                        # For salinity, use 'latest' as cache key since it's time-insensitive
                        cache_key = 'latest' if dataset == 'salinity' else date_str
                        self._save_to_cache(processed_data, dataset, cache_key)
                        
                        # Apply geographic filtering if bounds provided
                        if geographic_bounds:
                            processed_data = self._apply_geographic_filter(processed_data, geographic_bounds)
                            logger.info(f"Applied geographic filtering to {dataset} data")
                        
                        return processed_data
                        
                finally:
                    # Clean up temporary files with retry logic
                    self._cleanup_temp_file(file_path)
            else:
                logger.error(f"Failed to download {dataset} data")
                return None
                
        except Exception as e:
            logger.error(f"Download failed for {dataset}: {e}")
            return None
    
    
    def _process_data(self, data: xr.Dataset, dataset: str) -> xr.Dataset:
        """Process and regrid data to common grid"""
        try:
            if dataset == 'chlorophyll':
                return self._process_chlorophyll(data)
            elif dataset == 'sea_level':
                return self._process_sea_level(data)
            elif dataset == 'sst':
                return self._process_sst(data)
            elif dataset == 'salinity':
                return self._process_salinity(data)
            else:
                return data
        except Exception as e:
            logger.error(f"Data processing failed for {dataset}: {e}")
            return data
    
    def _process_chlorophyll(self, data: xr.Dataset) -> xr.Dataset:
        """Process PACE OCI Level-3 Binned Mapped Chlorophyll-a data"""
        try:
            # PACE OCI uses 'chlor_a' as the primary variable
            expected_var = 'chlor_a'
            
            if expected_var in data.data_vars:
                chl_var = expected_var
                logger.info(f"Found PACE OCI chlorophyll variable: {chl_var}")
            else:
                # Fallback to other possible variable names
                chl_vars = ['CHL', 'chlor_a', 'chlorophyll', 'chlor_a_mean']
                chl_var = None
                
                for var in chl_vars:
                    if var in data.data_vars:
                        chl_var = var
                        break
                
                if chl_var is None:
                    logger.warning("Chlorophyll variable not found, using first data variable")
                    chl_var = list(data.data_vars)[0]
            
            # Extract chlorophyll data
            chlorophyll_data = data[chl_var]
            
            # Handle fill values and invalid data
            if hasattr(chlorophyll_data, 'fill_value'):
                chlorophyll_data = chlorophyll_data.where(chlorophyll_data != chlorophyll_data.fill_value)
            
            # Remove negative values (not physically meaningful for chlorophyll)
            chlorophyll_data = chlorophyll_data.where(chlorophyll_data >= 0)
            
            # Create standardized dataset
            processed = xr.Dataset({
                'chlorophyll': chlorophyll_data
            })
            
            # Add metadata
            processed.attrs.update({
                'source': 'PACE OCI Level-3 Binned Mapped Chlorophyll-a',
                'variable': chl_var,
                'units': 'mg/m³',
                'description': 'Monthly composite chlorophyll-a concentration'
            })
            
            # Regrid to common grid
            return self._regrid_to_common_grid(processed, 'chlorophyll')
            
        except Exception as e:
            logger.error(f"Chlorophyll processing failed: {e}")
            return data
    
    def _process_sea_level(self, data: xr.Dataset) -> xr.Dataset:
        """Process NASA-SSH Level-4 Simple Gridded Sea Surface Height data"""
        try:
            # NASA-SSH L4 uses 'ssha' as the primary variable for Sea Surface Height Anomaly
            expected_var = 'ssha'
            
            if expected_var in data.data_vars:
                sl_var = expected_var
                logger.info(f"Found NASA-SSH L4 sea surface height anomaly variable: {sl_var}")
            else:
                # Fallback to other possible variable names for NASA-SSH L4
                sl_vars = ['ssha', 'ssha_smoothed', 'SLA', 'sea_level_anomaly', 'adt', 'sla', 'ssh_anomaly', 'ssh']
                sl_var = None
                
                for var in sl_vars:
                    if var in data.data_vars:
                        sl_var = var
                        break
                
                if sl_var is None:
                    logger.warning("Sea surface height anomaly variable not found, using first data variable")
                    sl_var = list(data.data_vars)[0]
            
            # Extract sea surface height anomaly data
            ssha_data = data[sl_var]
            
            # Apply NASA quality flag filtering (nasa_flag = 0 for good data)
            if 'nasa_flag' in data.data_vars:
                good_data_mask = data['nasa_flag'] == 0
                ssha_data = ssha_data.where(good_data_mask)
                logger.info("Applied NASA quality flag filtering (nasa_flag = 0)")
            else:
                logger.warning("NASA quality flag not found, proceeding without quality filtering")
            
            # Apply median filter flag for additional quality control
            if 'median_filter_flag' in data.data_vars:
                median_good_mask = data['median_filter_flag'] == 0
                ssha_data = ssha_data.where(median_good_mask)
                logger.info("Applied median filter flag (median_filter_flag = 0)")
            
            # Handle fill values and invalid data
            if hasattr(ssha_data, 'fill_value'):
                ssha_data = ssha_data.where(ssha_data != ssha_data.fill_value)
            
            # Remove extreme outliers (SSHA typically ranges from -1 to +1 meters)
            ssha_data = ssha_data.where((ssha_data >= -2) & (ssha_data <= 2))
            
            # Create standardized dataset
            processed = xr.Dataset({
                'sea_level': ssha_data
            })
            
            # Add metadata
            processed.attrs.update({
                'source': 'NASA-SSH Simple Gridded SSH V1',
                'variable': sl_var,
                'units': 'm',
                'description': 'NASA-SSH L4 Sea Surface Height Anomaly (7-day resolution, 0.5° grid)',
                'temporal_resolution': '7 days',
                'spatial_resolution': '0.5°',
                'data_period': '10 days of observations per grid',
                'quality_flags': 'nasa_flag=0, median_filter_flag=0',
                'reference': 'DTU21 mean sea surface'
            })
            
            # Regrid to common grid
            return self._regrid_to_common_grid(processed, 'sea_level')
            
        except Exception as e:
            logger.error(f"NASA-SSH L4 sea surface height anomaly processing failed: {e}")
            return data
    
    def _process_sst(self, data: xr.Dataset) -> xr.Dataset:
        """Process VIIRS NPP Level-3 mapped Sea Surface Temperature data"""
        try:
            logger.info(f"Processing VIIRS SST data. Available variables: {list(data.data_vars)}")
            logger.info(f"Available coordinates: {list(data.coords)}")
            logger.info(f"Dataset dimensions: {dict(data.dims)}")
            
            # VIIRS SST uses 'sst_triple' as the primary variable
            expected_var = 'sst_triple'
            
            if expected_var in data.data_vars:
                sst_var = expected_var
                logger.info(f"Found VIIRS SST variable: {sst_var}")
            else:
                # Fallback to other possible variable names for VIIRS SST
                sst_vars = ['sst_triple', 'sst', 'sst_11um', 'sst_4um', 'sea_surface_temperature', 'sst_mean']
                sst_var = None
                
                for var in sst_vars:
                    if var in data.data_vars:
                        sst_var = var
                        break
                
                if sst_var is None:
                    logger.warning(f"SST variable not found. Available variables: {list(data.data_vars)}")
                    if not data.data_vars:
                        logger.error("No data variables found in SST dataset!")
                        return data
                    sst_var = list(data.data_vars)[0]
            
            # Extract SST data
            sst_data = data[sst_var]
            
            # Handle fill values and invalid data for VIIRS SST
            # VIIRS SST typically uses -32767 as fill value
            if hasattr(sst_data, 'fill_value'):
                sst_data = sst_data.where(sst_data != sst_data.fill_value)
            else:
                # Common VIIRS fill value
                sst_data = sst_data.where(sst_data != -32767)
            
            # Apply quality flags if available
            if 'qual_sst' in data.data_vars:
                # VIIRS quality flag: 0 = best quality, 1 = good quality, 2 = questionable, 3 = bad
                good_quality = data['qual_sst'] <= 1
                sst_data = sst_data.where(good_quality)
                logger.info("Applied VIIRS SST quality flag filtering (qual_sst <= 1)")
            elif 'l2_flags' in data.data_vars:
                # Alternative quality flag format
                good_quality = (data['l2_flags'] & 1) == 0  # Check if first bit is not set
                sst_data = sst_data.where(good_quality)
                logger.info("Applied VIIRS SST quality flag filtering using l2_flags")
            
            # VIIRS SST data is typically already in Celsius
            # Convert from Kelvin to Celsius if needed
            if sst_data.attrs.get('units', '').lower() in ['k', 'kelvin']:
                sst_data = sst_data - 273.15
                logger.info("Converted SST from Kelvin to Celsius")
            
            # Remove physically unrealistic values (ocean temperatures typically -2°C to 35°C)
            sst_data = sst_data.where((sst_data >= -2) & (sst_data <= 35))
            
            # Create standardized dataset
            processed = xr.Dataset({
                'sst': sst_data
            })
            
            # Add metadata
            processed.attrs.update({
                'source': 'VIIRS NPP Level-3 mapped Sea Surface Temperature',
                'variable': sst_var,
                'units': '°C',
                'description': 'VIIRS NPP Level-3 mapped SST',
                'temporal_resolution': 'Daily',
                'spatial_resolution': '750m (at nadir)',
                'quality_control': 'VIIRS quality flags applied',
                'instrument': 'VIIRS'
            })
            
            # Regrid to common grid
            return self._regrid_to_common_grid(processed, 'sst')
            
        except Exception as e:
            logger.error(f"VIIRS SST processing failed: {e}")
            return data
    
    def _process_salinity(self, data: xr.Dataset) -> xr.Dataset:
        """Process OISSS L4 Multi-Mission Sea Surface Salinity data"""
        try:
            logger.info(f"Processing OISSS L4 salinity data. Available variables: {list(data.data_vars)}")
            logger.info(f"Available coordinates: {list(data.coords)}")
            logger.info(f"Dataset dimensions: {dict(data.dims)}")
            
            # OISSS L4 uses 'sss' as the primary variable for Sea Surface Salinity
            expected_var = 'sss'
            
            if expected_var in data.data_vars:
                sss_var = expected_var
                logger.info(f"Found OISSS L4 salinity variable: {sss_var}")
            else:
                # Fallback to other possible variable names for OISSS L4 salinity
                sss_vars = ['sss', 'salinity', 'sea_surface_salinity', 'sss_mean', 'salinity_mean']
                sss_var = None
                
                for var in sss_vars:
                    if var in data.data_vars:
                        sss_var = var
                        break
                
                if sss_var is None:
                    logger.warning(f"Salinity variable not found. Available variables: {list(data.data_vars)}")
                    if not data.data_vars:
                        logger.error("No data variables found in salinity dataset!")
                        return data
                    sss_var = list(data.data_vars)[0]
            
            # Extract salinity data
            sss_data = data[sss_var]
            
            # Handle fill values and invalid data for OISSS L4 salinity
            # OISSS L4 typically uses -999.0 as fill value
            if hasattr(sss_data, 'fill_value'):
                sss_data = sss_data.where(sss_data != sss_data.fill_value)
            else:
                # Common OISSS fill value
                sss_data = sss_data.where(sss_data != -999.0)
            
            # Apply quality flags if available
            if 'quality_flag' in data.data_vars:
                # OISSS quality flag: 0 = best quality, 1 = good quality, 2 = questionable, 3 = bad
                good_quality = data['quality_flag'] <= 1
                sss_data = sss_data.where(good_quality)
                logger.info("Applied OISSS L4 salinity quality flag filtering (quality_flag <= 1)")
            elif 'sss_quality' in data.data_vars:
                # Alternative quality flag format
                good_quality = data['sss_quality'] <= 1
                sss_data = sss_data.where(good_quality)
                logger.info("Applied OISSS L4 salinity quality flag filtering using sss_quality")
            
            # Remove physically unrealistic values (ocean salinity typically 0-40 psu)
            sss_data = sss_data.where((sss_data >= 0) & (sss_data <= 40))
            
            # Create standardized dataset
            processed = xr.Dataset({
                'salinity': sss_data
            })
            
            # Add metadata
            processed.attrs.update({
                'source': 'OISSS L4 Multi-Mission Sea Surface Salinity V2',
                'variable': sss_var,
                'units': 'psu',
                'description': 'Multi-Mission Optimally Interpolated Sea Surface Salinity Global Monthly',
                'temporal_resolution': 'Monthly',
                'spatial_resolution': '0.25°',
                'quality_control': 'OISSS quality flags applied',
                'missions': 'SMAP, SMOS, Aquarius'
            })
            
            # Regrid to common grid
            return self._regrid_to_common_grid(processed, 'salinity')
            
        except Exception as e:
            logger.error(f"OISSS L4 salinity processing failed: {e}")
            return data
    
    def _regrid_to_common_grid(self, data: xr.Dataset, var_name: str) -> xr.Dataset:
        """Regrid data to common global grid"""
        try:
            # Create target grid
            lats = np.arange(self.lat_range[0], self.lat_range[1] + self.grid_resolution, self.grid_resolution)
            lons = np.arange(self.lon_range[0], self.lon_range[1] + self.grid_resolution, self.grid_resolution)
            
            target_grid = xr.Dataset({
                'lat': (['lat'], lats),
                'lon': (['lon'], lons)
            })
            
            # Get coordinate names from data
            lat_coord = None
            lon_coord = None
            
            for coord in data.coords:
                if 'lat' in coord.lower():
                    lat_coord = coord
                elif 'lon' in coord.lower():
                    lon_coord = coord
            
            if lat_coord is None or lon_coord is None:
                logger.warning("Could not identify lat/lon coordinates, returning original data")
                return data
            
            # Rename coordinates for consistency
            data_renamed = data.rename({lat_coord: 'lat', lon_coord: 'lon'})
            
            # Interpolate to target grid
            regridded = data_renamed.interp(
                lat=target_grid.lat,
                lon=target_grid.lon,
                method='linear'
            )
            
            return regridded
            
        except Exception as e:
            logger.error(f"Regridding failed: {e}")
            return data
    
    def get_data_for_date(self, target_date: str, geographic_bounds: Dict = None) -> Dict[str, Optional[xr.Dataset]]:
        """Get all required datasets for a specific date with optional geographic filtering"""
        datasets = {}
        
        for dataset_name, config in self.datasets.items():
            logger.info(f"Fetching {config['description']} for {target_date}")
            datasets[dataset_name] = self.download_data(dataset_name, target_date, geographic_bounds)
        
        return datasets
    
    def get_data_for_date_with_adjacent(self, target_date: str, geographic_bounds: Dict = None) -> Dict[str, Optional[xr.Dataset]]:
        """
        Get all required datasets for a specific date, including adjacent time periods for complete coverage.
        This helps fill gaps in datasets like NASA-SSH that have limited coverage in certain regions.
        For salinity, uses latest available data since it's time-insensitive.
        """
        from datetime import datetime, timedelta
        
        logger.info(f"Fetching data for {target_date} with adjacent time periods for complete coverage")
        
        # Define adjacent time periods (7 days before and after for NASA-SSH compatibility)
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
        dates_to_try = [
            (target_dt - timedelta(days=7), "previous"),
            (target_dt, "current"),
            (target_dt + timedelta(days=7), "next")
        ]
        
        # Collect all datasets
        all_datasets = {}
        for dataset_name in self.datasets.keys():
            all_datasets[dataset_name] = []
        
        # Fetch data for each time period
        for date_dt, period_name in dates_to_try:
            date_str = date_dt.strftime('%Y-%m-%d')
            logger.info(f"Fetching data for {period_name} period: {date_str}")
            
            for dataset_name, config in self.datasets.items():
                # For salinity, always use the target date (will be converted to latest internally)
                fetch_date = date_str if dataset_name != 'salinity' else target_date
                data = self.download_data(dataset_name, fetch_date, geographic_bounds)
                if data is not None:
                    all_datasets[dataset_name].append(data)
                    logger.info(f"  {dataset_name}: Successfully fetched {period_name} data")
                else:
                    logger.warning(f"  {dataset_name}: No data available for {period_name} period")
        
        # Merge datasets to fill gaps
        merged_datasets = {}
        for dataset_name, data_list in all_datasets.items():
            if data_list:
                # For salinity, just take the first (and only) dataset since it's the same for all periods
                if dataset_name == 'salinity':
                    merged_datasets[dataset_name] = data_list[0]
                    logger.info(f"Using latest salinity data (time-insensitive)")
                else:
                    merged_datasets[dataset_name] = self._merge_datasets(data_list, dataset_name)
                    logger.info(f"Merged {dataset_name} data from {len(data_list)} time periods")
            else:
                merged_datasets[dataset_name] = None
                logger.warning(f"No data available for {dataset_name} from any time period")
        
        return merged_datasets
    
    def _merge_datasets(self, datasets: List[xr.Dataset], dataset_name: str) -> xr.Dataset:
        """
        Merge multiple datasets by filling gaps (NaN values) with data from other time periods.
        Prioritizes data from the target date, then fills gaps with adjacent periods.
        """
        if len(datasets) == 1:
            return datasets[0]
        
        logger.info(f"Merging {len(datasets)} {dataset_name} datasets to fill coverage gaps")
        
        # Start with the first dataset (should be the target date if available)
        merged = datasets[0].copy()
        
        # Get the main data variable name
        data_vars = list(merged.data_vars)
        if not data_vars:
            logger.warning(f"No data variables found in {dataset_name} dataset")
            return merged
        
        main_var = data_vars[0]  # Use the first (and typically only) data variable
        
        # Fill gaps with data from other time periods
        for i, dataset in enumerate(datasets[1:], 1):
            if main_var in dataset.data_vars:
                # Find where the merged dataset has NaN values
                nan_mask = np.isnan(merged[main_var].values)
                
                # Fill NaN values with data from this dataset
                merged_data = merged[main_var].values
                current_data = dataset[main_var].values
                
                # Only fill where we have NaN and the current dataset has valid data
                valid_mask = ~np.isnan(current_data)
                fill_mask = nan_mask & valid_mask
                
                merged_data[fill_mask] = current_data[fill_mask]
                merged[main_var].values = merged_data
                
                filled_count = np.sum(fill_mask)
                if filled_count > 0:
                    logger.info(f"  Filled {filled_count} gaps with data from period {i+1}")
        
        # Log final coverage statistics
        total_points = merged[main_var].size
        valid_points = np.sum(~np.isnan(merged[main_var].values))
        coverage_percent = 100 * valid_points / total_points
        logger.info(f"Final {dataset_name} coverage: {valid_points}/{total_points} points ({coverage_percent:.1f}%)")
        
        return merged
    
    
    def _apply_geographic_filter(self, data: xr.Dataset, geographic_bounds: Dict) -> xr.Dataset:
        """Apply geographic bounds to dataset"""
        try:
            if geographic_bounds is None:
                return data
            
            # Apply latitude bounds
            if 'lat' in data.coords:
                lat_mask = (data['lat'] >= geographic_bounds['south']) & (data['lat'] <= geographic_bounds['north'])
                data = data.where(lat_mask)
                logger.debug(f"Applied latitude filter: {geographic_bounds['south']} to {geographic_bounds['north']}")
            
            # Apply longitude bounds (handle 0-360 vs -180-180)
            if 'lon' in data.coords:
                if geographic_bounds['west'] < geographic_bounds['east']:
                    # Normal case: west < east
                    lon_mask = (data['lon'] >= geographic_bounds['west']) & (data['lon'] <= geographic_bounds['east'])
                else:
                    # Crosses dateline: west > east
                    lon_mask = (data['lon'] >= geographic_bounds['west']) | (data['lon'] <= geographic_bounds['east'])
                data = data.where(lon_mask)
                logger.debug(f"Applied longitude filter: {geographic_bounds['west']} to {geographic_bounds['east']}")
            
            return data
            
        except Exception as e:
            logger.error(f"Geographic filtering failed: {e}")
            return data
    
    def _cleanup_temp_file(self, file_path: str, max_retries: int = 3):
        """Clean up temporary file with retry logic"""
        import time
        
        for attempt in range(max_retries):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Successfully removed temporary file: {file_path}")
                    return
            except (OSError, PermissionError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Failed to remove {file_path} (attempt {attempt + 1}): {e}")
                    time.sleep(0.5)  # Wait 500ms before retry
                else:
                    logger.error(f"Failed to remove temporary file after {max_retries} attempts: {file_path}")
    
    def cleanup_temp_files(self):
        """Clean up all temporary files in the temp directory"""
        temp_dir = self.cache_dir / "temp"
        if temp_dir.exists():
            for file_path in temp_dir.glob("*.nc"):
                self._cleanup_temp_file(str(file_path))
    
    def check_sea_level_availability(self, target_date: str) -> Dict[str, Any]:
        """Check availability of sea level data around a target date"""
        try:
            logger.info(f"Checking sea level data availability for {target_date}")
            
            # Try different date ranges
            date_ranges = [
                ("7 days", 7),    # NASA-SSH L4 temporal resolution
                ("14 days", 14),
                ("30 days", 30),
                ("60 days", 60)
            ]
            
            results = {}
            for range_name, days in date_ranges:
                start_date = (datetime.strptime(target_date, '%Y-%m-%d') - timedelta(days=days)).strftime('%Y-%m-%d')
                end_date = (datetime.strptime(target_date, '%Y-%m-%d') + timedelta(days=days)).strftime('%Y-%m-%d')
                
                logger.info(f"Checking {range_name} range: {start_date} to {end_date}")
                granules = self.search_data('sea_level', start_date, end_date)
                
                results[range_name] = {
                    'count': len(granules),
                    'start_date': start_date,
                    'end_date': end_date,
                    'granules': granules[:5] if granules else []  # First 5 granules
                }
                
                if granules:
                    logger.info(f"Found {len(granules)} granules in {range_name} range")
                    break
            
            return results
            
        except Exception as e:
            logger.error(f"Error checking sea level availability: {e}")
            return {'error': str(e)}
    
    def get_dataset_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about available datasets"""
        return {
            dataset_name: {
                'short_name': config['short_name'],
                'description': config['description'],
                'variable': config['variable'],
                'units': config['units']
            }
            for dataset_name, config in self.datasets.items()
        }
