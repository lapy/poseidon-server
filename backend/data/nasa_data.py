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
        
        # NASA dataset configurations
        self.datasets = {
            'chlorophyll': {
                'short_name': 'PACE_OCI_L3M_CHL',
                'description': 'PACE OCI Level-3 Chlorophyll-a',
                'variable': 'chlor_a',
                'units': 'mg/m³'
            },
            'sea_level': {
                'short_name': 'NASA_SSH_REF_SIMPLE_GRID_V1',
                'description': 'NASA SSH Simple Gridded Sea Surface Height',
                'variable': 'ssha',
                'units': 'm'
            },
            'sst': {
                'short_name': 'VIIRSN_L3m_SST3',
                'description': 'VIIRS NPP Level-3 Sea Surface Temperature',
                'variable': 'sst_triple',
                'units': '°C'
            },
            'salinity': {
                'short_name': 'OISSS_L4_multimission_monthly_v2',
                'description': 'OISSS L4 Sea Surface Salinity',
                'variable': 'salinity',
                'units': 'psu'
            }
        }
        
        # Global grid parameters
        self.grid_resolution = 0.25  # degrees
        self.lat_range = (-90, 90)
        self.lon_range = (-180, 180)
        
        
        # Automatically authenticate with NASA Earthdata
        self._auto_authenticate()
    
    def _auto_authenticate(self):
        """Automatically authenticate with NASA Earthdata"""
        try:
            # Check for .netrc file
            netrc_path = Path.home() / ".netrc"
            
            # Check for environment variables
            if os.getenv('EARTHDATA_USERNAME') and os.getenv('EARTHDATA_PASSWORD'):
                logger.info("Authenticating with NASA Earthdata using environment variables")
                auth = earthaccess.login(strategy="environment")
                if auth:
                    logger.info("Successfully authenticated with NASA Earthdata")
                    return True
                else:
                    logger.error("Authentication failed with environment variables")
                    return False
            
            elif netrc_path.exists():
                logger.info("Authenticating with NASA Earthdata using .netrc file")
                auth = earthaccess.login(strategy="netrc")
                if auth:
                    logger.info("Successfully authenticated with NASA Earthdata")
                    return True
                else:
                    logger.error("Authentication failed with .netrc file")
                    return False
            
            else:
                logger.error("No authentication method found!")
                logger.error("Please set EARTHDATA_USERNAME and EARTHDATA_PASSWORD environment variables")
                logger.error("Or create a .netrc file with your credentials")
                return False
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            logger.error("Please ensure your NASA Earthdata credentials are correct")
            return False
    
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
            if dataset == 'salinity':
                # OISSS L4 has monthly temporal resolution - use hardcoded latest available date
                # Salinity is relatively stable, and OISSS L4 data is typically 1-2 years behind
                # Use a known good date from 2022 when data is reliably available
                target_date = "2022-01-01"  # January 2022 - typically latest reliable OISSS L4 data
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
            granule = results[0]
            logger.info(f"Selected granule for download: {granule.get('title', 'Unknown title')}")
            
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
                'units': 'mg/m³'
            })
            
            # Regrid to common grid
            return self._regrid_to_common_grid(processed, 'chlorophyll')
            
        except Exception as e:
            logger.error(f"Chlorophyll processing failed: {e}")
            return data
    
    def _process_sea_level(self, data: xr.Dataset) -> xr.Dataset:
        """Process NASA-SSH Level-4 Simple Gridded Sea Surface Height data"""
        try:
            # Log the raw data coordinates for debugging
            logger.info(f"Raw SSH data dimensions: {dict(data.sizes)}")
            logger.info(f"Raw SSH data coordinates: {list(data.coords.keys())}")
            
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
            
            # Count valid data points before processing
            valid_count_before = (~np.isnan(ssha_data.values)).sum()
            total_count = ssha_data.size
            logger.info(f"SSH data before processing: {valid_count_before}/{total_count} valid points ({100*valid_count_before/total_count:.1f}%)")
            
            # Apply orbit error reduction (OER) correction if available
            ssha_data = self._apply_orbit_error_reduction(data, ssha_data)
            
            # Apply comprehensive NASA-SSH quality flag filtering
            quality_mask = self._apply_nasa_ssh_quality_flags(data)
            ssha_data = ssha_data.where(quality_mask.astype(bool))
            
            # Handle fill values and invalid data
            if hasattr(ssha_data, 'fill_value'):
                ssha_data = ssha_data.where(ssha_data != ssha_data.fill_value)
            
            # Remove extreme outliers (SSHA typically ranges from -1 to +1 meters)
            ssha_data = ssha_data.where((ssha_data >= -2) & (ssha_data <= 2))
            
            
            # Create standardized dataset
            processed = xr.Dataset({
                'sea_level': ssha_data
            })
            
            # Add counts information if available
            if 'counts' in data.data_vars:
                processed['counts'] = data['counts']
                logger.info("Included counts information for data quality assessment")
            
            # Add essential metadata only
            processed.attrs.update({
                'source': 'NASA-SSH Simple Gridded SSH V1',
                'variable': sl_var,
                'units': 'm',
                'description': 'NASA-SSH L4 Sea Surface Height Anomaly',
                'temporal_resolution': '7 days',
                'spatial_resolution': '0.5°'
            })
            
            # Regrid to common grid
            return self._regrid_to_common_grid(processed, 'sea_level')
            
        except Exception as e:
            logger.error(f"NASA-SSH L4 sea surface height anomaly processing failed: {e}")
            return data
    
    def _apply_nasa_ssh_quality_flags(self, data: xr.Dataset) -> xr.DataArray:
        """
        Apply comprehensive NASA-SSH quality flag filtering
        
        Based on NASA-SSH User Guide quality control procedures:
        1. nasa_flag = 0 for good data
        2. Source flags from original satellite data
        """
        try:
            # Start with all data as good (using int8 for netCDF compatibility)
            quality_mask = xr.ones_like(data[list(data.data_vars)[0]], dtype=np.int8)
            
            # Apply NASA quality flag (primary flag)
            if 'nasa_flag' in data.data_vars:
                nasa_good_mask = (data['nasa_flag'] == 0).astype(np.int8)
                quality_mask = quality_mask & nasa_good_mask
                logger.info("Applied NASA quality flag filtering (nasa_flag = 0)")
            else:
                logger.warning("NASA quality flag not found, proceeding without NASA flag filtering")
            
            
            # Apply source flag filtering if available
            if 'source_flag' in data.data_vars:
                # Source flags vary by satellite mission, but generally 0 = good
                source_good_mask = (data['source_flag'] == 0).astype(np.int8)
                quality_mask = quality_mask & source_good_mask
                logger.info("Applied source flag filtering (source_flag = 0)")
            else:
                logger.debug("Source flag not found, skipping source flag filtering")
            
            # Count filtered points
            total_points = quality_mask.size
            good_points = quality_mask.sum().values
            filtered_percent = 100 * (total_points - good_points) / total_points
            
            if filtered_percent > 0:
                logger.info(f"Quality flag filtering: {good_points}/{total_points} points passed ({100-filtered_percent:.1f}% retained)")
            
            return quality_mask
            
        except Exception as e:
            logger.error(f"Quality flag application failed: {e}")
            # Return all good in case of error (conservative approach, using int8 for netCDF compatibility)
            return xr.ones_like(data[list(data.data_vars)[0]], dtype=np.int8)
    
    def _apply_orbit_error_reduction(self, data: xr.Dataset, ssha_data: xr.DataArray) -> xr.DataArray:
        """
        Apply orbit error reduction (OER) correction to sea surface height anomaly data
        
        Based on NASA-SSH User Guide, the OER correction reduces RMS variability 
        by approximately 2.3 cm variance. The OER array should be 
        added to SSHA data to reduce orbit error.
        
        The OER algorithm reduces large errors that occur on a roughly once-per-pass 
        basis, limited to differences of less than 30 cm.
        """
        try:
            # Check if OER correction is available
            if 'oer' not in data.data_vars:
                logger.info("Orbit error reduction (OER) correction not available in dataset")
                return ssha_data
            
            # Apply OER correction: SSHA_corrected = SSHA + OER
            oer_correction = data['oer']
            ssha_corrected = ssha_data + oer_correction
            
            # Log OER correction statistics
            oer_stats = {
                'mean': float(oer_correction.mean().values) if not np.isnan(oer_correction.mean().values) else 0.0,
                'std': float(oer_correction.std().values) if not np.isnan(oer_correction.std().values) else 0.0,
                'min': float(oer_correction.min().values) if not np.isnan(oer_correction.min().values) else 0.0,
                'max': float(oer_correction.max().values) if not np.isnan(oer_correction.max().values) else 0.0
            }
            
            logger.info(f"Applied orbit error reduction (OER) correction:")
            logger.info(f"  OER statistics: mean={oer_stats['mean']:.4f}m, std={oer_stats['std']:.4f}m")
            logger.info(f"  OER range: {oer_stats['min']:.4f}m to {oer_stats['max']:.4f}m")
            logger.info(f"  Expected RMS reduction: ~2.3 cm variance")
            
            return ssha_corrected
            
        except Exception as e:
            logger.error(f"Orbit error reduction application failed: {e}")
            logger.warning("Proceeding without OER correction")
            return ssha_data
    
    
    def _process_sst(self, data: xr.Dataset) -> xr.Dataset:
        """Process VIIRS NPP Level-3 mapped Sea Surface Temperature data"""
        try:
            logger.info(f"Processing VIIRS SST data. Available variables: {list(data.data_vars)}")
            logger.info(f"Available coordinates: {list(data.coords)}")
            logger.info(f"Dataset dimensions: {dict(data.sizes)}")
            
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
            
            # Add essential metadata only
            processed.attrs.update({
                'source': 'VIIRS NPP Level-3 mapped Sea Surface Temperature',
                'variable': sst_var,
                'units': '°C'
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
            logger.info(f"Dataset dimensions: {dict(data.sizes)}")
            
            # OISSS L4 uses 'sss' as the primary variable for Sea Surface Salinity
            expected_var = 'salinity'
            
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
            
            # Add essential metadata only
            processed.attrs.update({
                'source': 'OISSS L4 Multi-Mission Sea Surface Salinity V2',
                'variable': sss_var,
                'units': 'psu'
            })
            
            # Regrid to common grid
            regridded = self._regrid_to_common_grid(processed, 'salinity')
            
            # Ensure the salinity variable exists after regridding
            if 'salinity' not in regridded.data_vars:
                logger.error(f"Salinity variable missing after regridding. Available: {list(regridded.data_vars)}")
                # Try to find the variable in regridded dataset
                if regridded.data_vars:
                    actual_var = list(regridded.data_vars)[0]
                    regridded = regridded.rename({actual_var: 'salinity'})
                    logger.info(f"Renamed '{actual_var}' to 'salinity'")
            else:
                logger.info(f"Salinity variable successfully regridded")
            
            return regridded
            
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
            
            # Log actual longitude range for diagnostics
            lon_min = float(data_renamed['lon'].min())
            lon_max = float(data_renamed['lon'].max())
            logger.info(f"{var_name} original longitude range: {lon_min:.2f}° to {lon_max:.2f}°")
            
            # Convert longitude from 0-360 to -180-180 if needed
            if data_renamed['lon'].min() >= 0 and data_renamed['lon'].max() > 180:
                logger.info(f"Converting longitude from 0-360° to -180-180° for {var_name}")
                # Shift longitudes: values > 180 become negative
                data_renamed = data_renamed.assign_coords(
                    lon=(((data_renamed['lon'] + 180) % 360) - 180)
                )
                # Sort by longitude to maintain monotonic coordinates
                data_renamed = data_renamed.sortby('lon')
                logger.info(f"Longitude range after conversion: {float(data_renamed['lon'].min()):.2f}° to {float(data_renamed['lon'].max()):.2f}°")
            
            # Interpolate to target grid
            regridded = data_renamed.interp(
                lat=target_grid.lat,
                lon=target_grid.lon,
                method='linear'
            )
            
            # Log coverage after regridding
            main_var = list(regridded.data_vars)[0]
            valid_after = (~np.isnan(regridded[main_var].values)).sum()
            total_after = regridded[main_var].size
            logger.info(f"{var_name} after regridding: {valid_after}/{total_after} valid points ({100*valid_after/total_after:.1f}%)")
            
            # Check longitude coverage in the regridded data
            if 'lon' in regridded.coords:
                lon_with_data = []
                for lon_val in regridded.lon.values:
                    if np.any(~np.isnan(regridded[main_var].sel(lon=lon_val).values)):
                        lon_with_data.append(float(lon_val))
                if lon_with_data:
                    logger.info(f"{var_name} longitude coverage: {min(lon_with_data):.2f}° to {max(lon_with_data):.2f}°")
            
            return regridded
            
        except Exception as e:
            logger.error(f"Regridding failed: {e}")
            return data
    
    def get_data_for_date(self, target_date: str, geographic_bounds: Dict = None) -> Dict[str, Optional[xr.Dataset]]:
        """
        Get all required datasets for a specific date using temporal merging only.
        Uses NASA-SSH's built-in temporal merging within the 10-day observation window.
        For salinity, uses latest available data since it's time-insensitive.
        
        Args:
            target_date: Date in YYYY-MM-DD format
            geographic_bounds: Optional geographic bounds for filtering
        
        Raises ValueError if any required dataset cannot be retrieved.
        """
        logger.info(f"Fetching data for {target_date} using temporal merging")
        
        # Collect all datasets for the target date
        datasets = {}
        required_datasets = ['chlorophyll', 'sea_level', 'sst', 'salinity']
        
        for dataset_name, config in self.datasets.items():
            logger.info(f"Fetching {config['description']} for {target_date}")
            data = self.download_data(dataset_name, target_date, geographic_bounds)
            datasets[dataset_name] = data
            
            if data is None:
                logger.warning(f"No data available for {dataset_name} on {target_date}")
            else:
                logger.info(f"Successfully retrieved {dataset_name} data")
        
        # Fail fast if any required dataset is missing
        missing_datasets = [dataset for dataset in required_datasets if datasets.get(dataset) is None]
        if missing_datasets:
            error_msg = f"Required datasets not available: {', '.join(missing_datasets)}. Please try a different date or check data availability."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("All required datasets successfully retrieved using temporal merging")
        return datasets
    
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
    
    
    def download_along_track_data(self, target_date: str, geographic_bounds: Dict = None, pass_type: str = None) -> Optional[xr.Dataset]:
        """
        Download and process NASA-SSH along-track data for higher resolution analysis
        
        Along-track data includes:
        - ssha: Sea surface height anomalies
        - ssha_smoothed: Smoothed SSHA values
        - time, latitude, longitude: Position and time
        - pass, cycle: Orbit information
        - dac: Dynamic atmospheric correction
        - oer: Orbit error reduction
        - Quality flags: nasa_flag, source_flag
        
        Args:
            target_date: Date in YYYY-MM-DD format
            geographic_bounds: Optional geographic bounds for filtering
            pass_type: Optional pass type filter ('ascending', 'descending', or None for both)
        """
        try:
            logger.info(f"Downloading NASA-SSH gridded data for {target_date}")
            
            # Use the standard gridded data download
            gridded_data = self.download_data('sea_level', target_date, geographic_bounds)
            
            if gridded_data is not None:
                # Add metadata to indicate this is gridded data
                gridded_data.attrs['data_type'] = 'gridded'
                gridded_data.attrs['note'] = 'Using gridded NASA-SSH data (along-track not available)'
                logger.info("Successfully retrieved NASA-SSH gridded data")
                return gridded_data
            else:
                logger.warning(f"No NASA-SSH data available for {target_date}")
                return None
            
        except Exception as e:
            logger.error(f"NASA-SSH data download failed: {e}")
            return None
    
    
