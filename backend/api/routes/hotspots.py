"""
API Routes for Shark Foraging Hotspot Prediction
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, date
from typing import Optional, Dict, Any
import logging
import json
import numpy as np
import xarray as xr

from models.hsi_model import HSIModel
from data.nasa_data import NASADataManager
from utils.geojson_converter import convert_hsi_to_geojson, convert_dataset_to_geojson

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize models
hsi_model = HSIModel()
nasa_manager = NASADataManager()

# Global cache for shared data between HSI and overlays
_data_cache = {}

def _clean_response_data(data):
    """Clean response data to remove NaN values for JSON serialization"""
    if isinstance(data, dict):
        return {k: _clean_response_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_clean_response_data(item) for item in data]
    elif isinstance(data, float) and np.isnan(data):
        return 0.0
    elif isinstance(data, np.floating) and np.isnan(data):
        return 0.0
    else:
        return data

def _cache_data(target_date: str, bounds: Optional[Dict], datasets: Dict):
    """Cache datasets for reuse by overlay endpoints"""
    cache_key = f"{target_date}_{hash(str(bounds)) if bounds else 'global'}"
    _data_cache[cache_key] = {
        'datasets': datasets,
        'timestamp': datetime.now()
    }
    logger.info(f"Cached datasets for {target_date} for overlay reuse")

def _get_cached_data(target_date: str, bounds: Optional[Dict]) -> Optional[Dict]:
    """Get cached datasets if available and recent"""
    cache_key = f"{target_date}_{hash(str(bounds)) if bounds else 'global'}"
    
    if cache_key in _data_cache:
        cached = _data_cache[cache_key]
        # Cache valid for 5 minutes
        if (datetime.now() - cached['timestamp']).seconds < 300:
            logger.info(f"Using cached datasets for {target_date}")
            return cached['datasets']
        else:
            # Remove expired cache
            del _data_cache[cache_key]
    
    return None

async def _get_overlay_dataset(overlay_type: str, target_date: str, bounds: Optional[Dict]) -> tuple[Optional[xr.Dataset], str]:
    """
    Get dataset for overlay, reusing cached data from HSI calculation when possible
    
    Args:
        overlay_type: Type of overlay (chlorophyll, oceanographic, salinity)
        target_date: Target date for data retrieval
        bounds: Optional geographic bounds
        
    Returns:
        Tuple of (dataset, variable_name)
    """
    # Try to get cached data first
    datasets = _get_cached_data(target_date, bounds)
    
    if datasets is None:
        # No cached data, fetch using temporal merging
        try:
            datasets = nasa_manager.get_data_for_date(target_date, bounds)
            logger.info(f"Successfully retrieved {overlay_type} data using temporal merging with combined passes for overlay")
        except ValueError as e:
            # Fallback to single dataset if temporal merging fails
            logger.warning(f"Failed to get {overlay_type} data using temporal merging: {e}. Trying single dataset.")
            datasets = {overlay_type: nasa_manager.download_data(overlay_type, target_date, bounds)}
    
    if overlay_type == 'chlorophyll':
        dataset = datasets.get('chlorophyll')
        variable = 'chlorophyll'
        
    elif overlay_type == 'oceanographic':
        # For oceanographic overlay, process sea level data using HSI method
        # Use the same merged sea level data that HSI calculation uses
        sea_level_data = datasets.get('sea_level')
        if sea_level_data is None:
            return None, None
            
        # Process the sea level data using the same method as HSI calculation
        from models.hsi_model import HSIModel
        hsi_processor = HSIModel()
        
        # Extract sea level anomaly from temporally merged data (same as HSI calculation)
        # The data uses NASA-SSH's built-in temporal merging within the 10-day observation window
        sla_data = sea_level_data['sea_level']
        processed_oceanographic = hsi_processor._normalize_sea_level_anomaly(sla_data)
        
        # Check coverage statistics
        sea_level_nan_count = np.isnan(processed_oceanographic).sum().values
        total_points = processed_oceanographic.size
        if sea_level_nan_count > 0:
            logger.info(f"Oceanographic overlay: {sea_level_nan_count}/{total_points} points still missing ({100*sea_level_nan_count/total_points:.1f}%) after temporal merging")
        
        # Create a dataset with the processed oceanographic suitability
        dataset = xr.Dataset({
            'oceanographic': processed_oceanographic
        })
        variable = 'oceanographic'
        
    elif overlay_type == 'salinity':
        dataset = datasets.get('salinity')
        variable = 'salinity'  # Sea Surface Salinity variable name (renamed during processing)
    
    else:
        return None, None
    
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"No {overlay_type} data available for overlay on {target_date}")
    
    return dataset, variable

@router.get("/hotspots")
async def get_hotspots(
    target_date: str = Query(..., description="Target date in YYYY-MM-DD format"),
    shark_species: str = Query(..., description="Shark species: 'great_white', 'tiger_shark', or 'bull_shark'"),
    format: str = Query("geojson", description="Output format: 'geojson' or 'raw'"),
    north: float = Query(None, description="Northern boundary (latitude)"),
    south: float = Query(None, description="Southern boundary (latitude)"),
    east: float = Query(None, description="Eastern boundary (longitude)"),
    west: float = Query(None, description="Western boundary (longitude)")
):
    """
    Get shark foraging hotspots for a specific date and species
    
    Args:
        target_date: Date in YYYY-MM-DD format
        shark_species: Species identifier
        format: Output format (geojson or raw)
        north: Northern boundary (latitude) for geographic filtering
        south: Southern boundary (latitude) for geographic filtering
        east: Eastern boundary (longitude) for geographic filtering
        west: Western boundary (longitude) for geographic filtering
    
    Returns:
        GeoJSON or raw HSI data
    """
    try:
        # Validate inputs
        try:
            datetime.strptime(target_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        if shark_species not in hsi_model.shark_profiles:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid shark species. Available: {list(hsi_model.shark_profiles.keys())}"
            )
        
        logger.info(f"Processing request for {shark_species} on {target_date}")
        
        # Validate and apply geographic bounds
        geographic_bounds = None
        if all([north, south, east, west]):
            # # Validate bounds
            # if not (-90 <= south <= north <= 90):
            #     raise HTTPException(status_code=400, detail="Invalid latitude bounds")
            # if not (-180 <= west <= 180 and -180 <= east <= 180):
            #     raise HTTPException(status_code=400, detail="Invalid longitude bounds")
            
            geographic_bounds = {
                'north': north,
                'south': south,
                'east': east,
                'west': west
            }
            logger.info(f"Applying geographic filter: {geographic_bounds}")
        else:
            logger.info("No geographic bounds provided, processing global data")
        
        # Calculate lagged dates for trophic lag
        lagged_dates = hsi_model.calculate_lagged_dates(target_date, shark_species)
        logger.info(f"Lagged dates: {lagged_dates}")
        
        # Get current NASA satellite data using temporal merging
        # This will fail fast at the NASA data retrieval step if any dataset is missing
        try:
            datasets = nasa_manager.get_data_for_date(target_date, geographic_bounds)
            logger.info("All required datasets successfully retrieved from NASA with combined pass enhancement")
            
            # Cache datasets for overlay reuse
            _cache_data(target_date, geographic_bounds, datasets)
            
        except ValueError as e:
            logger.error(f"NASA data retrieval failed: {e}")
            raise HTTPException(
                status_code=404,
                detail=str(e)
            )
        
        # Get lagged data if available
        lagged_chlorophyll_data = None
        lagged_sst_data = None
        
        try:
            # Try to get lagged chlorophyll data using temporal merging with combined passes
            if lagged_dates['chlorophyll_lag_days'] > 0:
                lagged_chlorophyll_datasets = nasa_manager.get_data_for_date(
                    lagged_dates['chlorophyll_lag_date'], geographic_bounds
                )
                lagged_chlorophyll_data = lagged_chlorophyll_datasets.get('chlorophyll')
                if lagged_chlorophyll_data is not None:
                    logger.info(f"Successfully retrieved lagged chlorophyll data from {lagged_dates['chlorophyll_lag_date']}")
                else:
                    logger.warning(f"Could not retrieve lagged chlorophyll data from {lagged_dates['chlorophyll_lag_date']}")
        except Exception as e:
            logger.warning(f"Failed to retrieve lagged chlorophyll data: {e}")
        
        try:
            # Try to get lagged SST data using temporal merging with combined passes
            if lagged_dates['temperature_lag_days'] > 0:
                lagged_sst_datasets = nasa_manager.get_data_for_date(
                    lagged_dates['temperature_lag_date'], geographic_bounds
                )
                lagged_sst_data = lagged_sst_datasets.get('sst')
                if lagged_sst_data is not None:
                    logger.info(f"Successfully retrieved lagged SST data from {lagged_dates['temperature_lag_date']}")
                else:
                    logger.warning(f"Could not retrieve lagged SST data from {lagged_dates['temperature_lag_date']}")
        except Exception as e:
            logger.warning(f"Failed to retrieve lagged SST data: {e}")
        
        # Validate dataset content (fail-fast check already done above, this is for additional validation)
        for name, data in datasets.items():
            if name == 'sst' and (not hasattr(data, 'data_vars') or not data.data_vars or 'sst' not in data.data_vars):
                logger.error(f"SST dataset is empty or missing 'sst' variable - HSI calculation cannot proceed")
                raise HTTPException(
                    status_code=422,
                    detail="SST dataset is empty or missing required 'sst' variable"
                )
            elif name == 'chlorophyll' and (not hasattr(data, 'data_vars') or not data.data_vars or 'chlorophyll' not in data.data_vars):
                logger.warning(f"Chlorophyll dataset is empty or missing 'chlorophyll' variable")
                raise HTTPException(
                    status_code=422,
                    detail="Chlorophyll dataset is empty or missing required 'chlorophyll' variable"
                )
            elif name == 'sea_level' and (not hasattr(data, 'data_vars') or not data.data_vars or 'sea_level' not in data.data_vars):
                logger.warning(f"Sea level dataset is empty or missing 'sea_level' variable")
                raise HTTPException(
                    status_code=422,
                    detail="Sea level dataset is empty or missing required 'sea_level' variable"
                )
            elif name == 'salinity' and (not hasattr(data, 'data_vars') or not data.data_vars or 'salinity' not in data.data_vars):
                logger.error(f"Salinity dataset is empty or missing 'salinity' variable - HSI calculation cannot proceed")
                raise HTTPException(
                    status_code=422,
                    detail="Salinity dataset is empty or missing required 'salinity' variable"
                )
        
        # Calculate HSI with lagged data
        sea_level_data = datasets.get('sea_level')
        salinity_data = datasets.get('salinity')
        
        # Note: Salinity data validation already done in fail-fast check above
        
        try:
            hsi_result = hsi_model.calculate_hsi(
                chlorophyll_data=datasets['chlorophyll'],
                sea_level_data=sea_level_data,
                sst_data=datasets['sst'],
                salinity_data=salinity_data,
                shark_species=shark_species,
                target_date=target_date,
                geographic_bounds=geographic_bounds,
                lagged_chlorophyll_data=lagged_chlorophyll_data,
                lagged_sst_data=lagged_sst_data
            )
        except ValueError as e:
            logger.error(f"HSI calculation failed: {e}")
            raise HTTPException(
                status_code=422,
                detail=f"HSI calculation failed: {str(e)}"
            )
        
        # Calculate statistics
        stats = hsi_model.get_hsi_statistics(hsi_result)
        
        # Format response based on requested format
        if format.lower() == "geojson":
            # Convert to GeoJSON for map visualization
            geojson_data = convert_hsi_to_geojson(hsi_result, geographic_bounds=geographic_bounds)
            
            response_data = {
                "type": "FeatureCollection",
                "features": geojson_data,
                "metadata": {
                    "shark_species": shark_species,
                    "target_date": target_date,
                    "statistics": stats,
                    "model_parameters": hsi_model.shark_profiles[shark_species].__dict__,
                    "data_source": "NASA-SSH L4",
                    "lagged_dates": lagged_dates,
                    "lagged_data_available": {
                        "chlorophyll": lagged_chlorophyll_data is not None,
                        "temperature": lagged_sst_data is not None
                    },
                    "geographic_bounds": geographic_bounds,
                    "processing_area": "Viewport" if geographic_bounds else "Global",
                    "data_limitations": {
                        "sea_level_coverage": "Enhanced coverage using combined ascending and descending passes, with fallback to gridded data",
                        "missing_data_handling": "NASA-SSH built-in temporal merging within 10-day observation window, dual-pass geometry for improved spatial coverage",
                        "temporal_merge": "NASA-SSH uses 10-day observations per grid with Gaussian weighted spatial averaging",
                        "pass_combination": "Ascending and descending passes combined using xarray.concat for enhanced western hemisphere coverage"
                    },
                    "oceanographic_features": {
                        "eddy_detection": {
                            "method": "Gaussian normalization of Sea Level Anomaly (SLA)",
                            "formula": "f_eddy = exp(-E'²/(2σ²)) where σ = 0.1m",
                            "types": {
                                "cyclonic_eddies": "Negative SLA, cold-core, upwelling, nutrient-rich",
                                "anticyclonic_eddies": "Positive SLA, warm-core, downwelling, prey concentration"
                            },
                            "optimal_strength": "Moderate SLA values (±0.1m) provide highest shark foraging suitability",
                            "size_range": "50-300 km diameter, captured by 0.5° grid resolution"
                        },
                        "front_detection": {
                            "method": "Spatial gradient analysis of SLA",
                            "formula": "|∇SLA| = √((∂SLA/∂lat)² + (∂SLA/∂lon)²)",
                            "suitability": "f_front = exp(-|∇SLA|/σ_front) where σ_front = 0.05 m/degree",
                            "characteristics": "Sharp boundaries between water masses, convergence zones where prey concentrates",
                            "additional_fronts": "Thermal fronts detected through Sea Surface Temperature gradients"
                        },
                        "combined_suitability": {
                            "formula": "f_E = 0.6 × f_eddy + 0.4 × f_front",
                            "weighting": {
                                "eddies": "60% - Primary foraging hotspots",
                                "fronts": "40% - Secondary but important prey concentration zones"
                            },
                            "ecological_significance": "Both features drive prey aggregation through upwelling, convergence, and nutrient cycling"
                        }
                    },
                    "nasa_challenge": {
                        "challenge_name": "Sharks from Space",
                        "challenge_year": "2025",
                        "challenge_url": "https://www.spaceappschallenge.org/2025/challenges/sharks-from-space/",
                        "nasa_mission": "Earth Science Division",
                        "data_sources": "NASA Earthdata Cloud",
                        "project_alignment": "Satellite-based shark habitat prediction using NASA oceanographic data"
                    },
                    "nasa_ssh_enhancements": {
                        "user_guide_compliance": "Full implementation of NASA-SSH User Guide specifications",
                        "quality_control": "Comprehensive flag handling (nasa_flag, median_filter_flag, source_flag)",
                        "orbit_error_reduction": "OER correction applied for improved data quality",
                        "basin_aware_processing": "Ocean basin connectivity rules implemented",
                        "crossover_analysis": "Pass-to-pass validation for data quality assessment",
                        "dual_pass_geometry": "Combined ascending and descending passes for enhanced spatial coverage",
                        "basin_connectivity": "266 ocean basins with connectivity rules for geographically correlated regions",
                        "dtu21_reference": "DTU21 Mean Sea Surface (1993-2012) reference information",
                        "along_track_support": "High-resolution along-track data processing available",
                        "oceanographic_features": "Enhanced eddy and front detection using NASA-SSH specifications"
                    }
                }
            }
            
            # Ensure no NaN values in response
            response_data = _clean_response_data(response_data)
            return JSONResponse(content=response_data)
            
        else:
            # Return raw data
            response_data = {
                "hsi_data": hsi_result.to_dict(),
                "metadata": {
                    "shark_species": shark_species,
                    "target_date": target_date,
                    "statistics": stats,
                    "model_parameters": hsi_model.shark_profiles[shark_species].__dict__,
                    "data_source": "NASA-SSH L4",
                    "lagged_dates": lagged_dates,
                    "lagged_data_available": {
                        "chlorophyll": lagged_chlorophyll_data is not None,
                        "temperature": lagged_sst_data is not None
                    },
                    "geographic_bounds": geographic_bounds,
                    "processing_area": "Viewport" if geographic_bounds else "Global"
                }
            }
            
            return JSONResponse(content=response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing hotspots request: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/species")
async def get_shark_species():
    """Get available shark species profiles"""
    try:
        profiles = hsi_model.get_shark_profiles()
        return JSONResponse(content=profiles)
    except Exception as e:
        logger.error(f"Error getting shark species: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/overlay/{overlay_type}")
async def get_overlay_data(
    overlay_type: str,
    target_date: str = Query(..., description="Target date in YYYY-MM-DD format"),
    geographic_bounds: Optional[str] = Query(None, description="Geographic bounds as JSON string"),
    threshold: float = Query(0.0, description="Minimum value threshold for data inclusion"),
    density_factor: int = Query(4, description="Density reduction factor (higher = less dense, default 4)")
):
    """Get overlay data for visualization"""
    try:
        # Parse geographic bounds if provided
        bounds = None
        if geographic_bounds:
            try:
                bounds = json.loads(geographic_bounds)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid geographic bounds format")
        
        # Validate overlay type
        valid_overlays = ['chlorophyll', 'oceanographic', 'salinity']
        if overlay_type not in valid_overlays:
            raise HTTPException(status_code=400, detail=f"Invalid overlay type. Must be one of: {valid_overlays}")
        
        # Get dataset - reuse HSI data if available, otherwise fetch separately
        dataset, variable = await _get_overlay_dataset(overlay_type, target_date, bounds)
        
        if dataset is None:
            raise HTTPException(status_code=404, detail=f"No data available for {overlay_type} on {target_date}")
        
        # Convert to GeoJSON with density reduction
        geojson_data = convert_dataset_to_geojson(dataset, variable, bounds, threshold, density_factor)
        
        response_data = {
            "type": "FeatureCollection",
            "features": geojson_data,
            "metadata": {
                "overlay_type": overlay_type,
                "variable": variable,
                "target_date": target_date,
                "threshold": threshold,
                "density_factor": density_factor,
                "feature_count": len(geojson_data),
                "geographic_bounds": bounds,
                "data_source": "NASA Earthdata"
            }
        }
        
        return _clean_response_data(response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get overlay data for {overlay_type}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve {overlay_type} overlay data")

@router.get("/datasets")
async def get_dataset_info():
    """Get information about NASA datasets used"""
    try:
        dataset_info = nasa_manager.get_dataset_info()
        return JSONResponse(content=dataset_info)
    except Exception as e:
        logger.error(f"Error getting dataset info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def health_check():
    """Health check for the hotspots API"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@router.post("/authenticate")
async def authenticate_nasa(
    username: Optional[str] = None,
    password: Optional[str] = None
):
    """Authenticate with NASA Earthdata"""
    try:
        success = nasa_manager.authenticate(username, password)
        if success:
            return {"status": "authenticated", "message": "Successfully authenticated with NASA Earthdata"}
        else:
            raise HTTPException(status_code=401, detail="Authentication failed")
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=500, detail="Authentication error")

@router.post("/cleanup")
async def cleanup_temp_files():
    """Clean up temporary files"""
    try:
        nasa_manager.cleanup_temp_files()
        return {"status": "success", "message": "Temporary files cleaned up"}
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        raise HTTPException(status_code=500, detail="Cleanup failed")

@router.get("/sea-level-availability")
async def check_sea_level_availability(
    target_date: str = Query(..., description="Target date in YYYY-MM-DD format")
):
    """Check availability of sea level data around a target date"""
    try:
        # Validate date format
        try:
            datetime.strptime(target_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        availability = nasa_manager.check_sea_level_availability(target_date)
        return JSONResponse(content=availability)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking sea level availability: {e}")
        raise HTTPException(status_code=500, detail=f"Error checking availability: {str(e)}")

@router.get("/along-track-data")
async def get_along_track_data(
    target_date: str = Query(..., description="Target date in YYYY-MM-DD format"),
    north: float = Query(None, description="Northern boundary (latitude)"),
    south: float = Query(None, description="Southern boundary (latitude)"),
    east: float = Query(None, description="Eastern boundary (longitude)"),
    west: float = Query(None, description="Western boundary (longitude)")
):
    """
    Get NASA-SSH along-track data for higher resolution analysis
    
    Along-track data provides once-per-second sampling with 5-10 km diameter
    nadir measurements, offering higher resolution than gridded products.
    """
    try:
        # Validate date format
        try:
            datetime.strptime(target_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Validate and apply geographic bounds
        geographic_bounds = None
        if all([north, south, east, west]):
            geographic_bounds = {
                'north': north,
                'south': south,
                'east': east,
                'west': west
            }
            logger.info(f"Applying geographic filter for along-track data: {geographic_bounds}")
        
        # Download along-track data
        along_track_data = nasa_manager.download_along_track_data(target_date, geographic_bounds)
        
        if along_track_data is None:
            raise HTTPException(
                status_code=404,
                detail=f"No along-track data available for {target_date}"
            )
        
        # Convert to GeoJSON for visualization
        geojson_data = convert_dataset_to_geojson(
            along_track_data, 
            'sea_level', 
            geographic_bounds, 
            threshold=0.0, 
            density_factor=2  # Higher density for along-track data
        )
        
        response_data = {
            "type": "FeatureCollection",
            "features": geojson_data,
            "metadata": {
                "data_type": "along_track",
                "target_date": target_date,
                "feature_count": len(geojson_data),
                "geographic_bounds": geographic_bounds,
                "data_source": "NASA-SSH Along-Track Data V1",
                "resolution": "once-per-second sampling, 5-10 km diameter",
                "processing": "19-point Gaussian-like normalized filter",
                "quality_control": "Comprehensive flag handling and orbit error reduction",
                "reference_surface": "DTU21 Mean Sea Surface (1993-2012)",
                "satellite_missions": "TOPEX/Poseidon, Jason-1, Jason-2, Jason-3, Sentinel-6",
                "along_track_features": {
                    "pass_information": "Orbit pass numbers for crossover analysis",
                    "cycle_information": "Orbit cycle numbers for temporal correlation",
                    "dynamic_atmospheric_correction": "DAC correction for atmospheric effects",
                    "orbit_error_reduction": "OER correction for systematic orbit errors",
                    "high_resolution": "Once-per-second sampling for detailed feature detection"
                }
            }
        }
        
        return _clean_response_data(response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving along-track data: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving along-track data: {str(e)}")

@router.get("/combined-pass-data")
async def get_combined_pass_data(
    target_date: str = Query(..., description="Target date in YYYY-MM-DD format"),
    north: float = Query(None, description="Northern boundary (latitude)"),
    south: float = Query(None, description="Southern boundary (latitude)"),
    east: float = Query(None, description="Eastern boundary (longitude)"),
    west: float = Query(None, description="Western boundary (longitude)")
):
    """
    Get NASA-SSH combined ascending and descending pass data for enhanced coverage
    
    This endpoint fetches both ascending and descending pass data and combines them
    to provide improved spatial coverage, particularly in the western hemisphere.
    
    Args:
        target_date: Date in YYYY-MM-DD format
        north: Northern boundary (latitude) for geographic filtering
        south: Southern boundary (latitude) for geographic filtering
        east: Eastern boundary (longitude) for geographic filtering
        west: Western boundary (longitude) for geographic filtering
    
    Returns:
        GeoJSON representation of combined pass sea level data
    """
    try:
        # Validate inputs
        try:
            datetime.strptime(target_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Build geographic bounds if provided
        geographic_bounds = None
        if all(param is not None for param in [north, south, east, west]):
            geographic_bounds = [west, south, east, north]
        
        # Download sea level data
        logger.info(f"Downloading NASA-SSH data for {target_date}")
        data = nasa_manager.download_data('sea_level', target_date, geographic_bounds)
        
        if data is None:
            raise HTTPException(
                status_code=404,
                detail=f"No sea level data available for {target_date}"
            )
        
        # Convert to GeoJSON
        geojson_data = convert_dataset_to_geojson(
            data, 
            'sea_level', 
            geographic_bounds, 
            threshold=0.0, 
            density_factor=2  # Higher density for combined pass data
        )
        
        response_data = {
            "type": "FeatureCollection",
            "features": geojson_data,
            "metadata": {
                "data_type": "combined_pass",
                "target_date": target_date,
                "feature_count": len(geojson_data),
                "geographic_bounds": geographic_bounds,
                "data_source": "NASA-SSH Combined Pass Data V1",
                "resolution": "once-per-second sampling, 5-10 km diameter",
                "processing": "19-point Gaussian-like normalized filter",
                "quality_control": "Comprehensive flag handling and orbit error reduction",
                "reference_surface": "DTU21 Mean Sea Surface (1993-2012)",
                "satellite_missions": "TOPEX/Poseidon, Jason-1, Jason-2, Jason-3, Sentinel-6",
                "pass_combination": data.attrs.get('pass_combination', 'unknown'),
                "ascending_points": data.attrs.get('ascending_points', 0),
                "descending_points": data.attrs.get('descending_points', 0),
                "total_points": data.attrs.get('total_points', 0),
                "coverage_enhancement": "Dual pass geometry for improved spatial coverage",
                "combined_pass_features": {
                    "dual_geometry": "Ascending and descending passes combined for complete coverage",
                    "western_hemisphere": "Enhanced coverage in western hemisphere through dual pass geometry",
                    "spatial_resolution": "Improved spatial sampling through multiple viewing angles",
                    "data_quality": "Cross-validation between ascending and descending measurements"
                }
            }
        }
        
        return _clean_response_data(response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving combined pass data: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving combined pass data: {str(e)}")
