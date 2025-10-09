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
from data.gfw_data import GFWDataManager
from utils.geojson_converter import convert_dataset_to_geojson, convert_hsi_to_geojson_cached, convert_dataset_to_geojson_cached
from utils.geojson_cache import get_geojson_cache
from utils.cache_cleanup import run_maintenance_cleanup, cleanup_expired_cache, cleanup_old_cache_by_date, cleanup_cache_by_size

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize models
hsi_model = HSIModel()
nasa_manager = NASADataManager()
gfw_manager = GFWDataManager()

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

@router.get("/hotspots")
async def get_hotspots(
    target_date: str = Query(..., description="Target date in YYYY-MM-DD format"),
    shark_species: str = Query(..., description="Shark species: 'great_white', 'tiger_shark', or 'bull_shark'"),
    format: str = Query("geojson", description="Output format: 'geojson' or 'raw'"),
    threshold: float = Query(0.0, description="Minimum HSI threshold for inclusion (0.0-1.0, default 0.0 returns all grid points)")
):
    """
    Get shark foraging hotspots for a specific date and species

    Args:
        target_date: Date in YYYY-MM-DD format
        shark_species: Species identifier
        format: Output format (geojson or raw)

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
        
        logger.info(f"Processing request for {shark_species} on {target_date} - calculating HSI for entire dataset")
        
        # Calculate lagged dates for trophic lag
        lagged_dates = hsi_model.calculate_lagged_dates(target_date, shark_species)
        logger.info(f"Lagged dates: {lagged_dates}")
        
        # Fetch datasets efficiently - only get lagged data for chlorophyll and SST
        datasets = {}
        lagged_chlorophyll_data = None
        lagged_sst_data = None
        
        # Always fetch sea_level and salinity for current date (no lag)
        try:
            sea_level_data = nasa_manager.download_data('sea_level', target_date)
            salinity_data = nasa_manager.download_data('salinity', target_date)
            
            if sea_level_data is not None:
                datasets['sea_level'] = sea_level_data
                logger.info("Successfully retrieved sea level data")
            else:
                raise ValueError("Failed to retrieve sea level data")
                
            if salinity_data is not None:
                datasets['salinity'] = salinity_data
                logger.info("Successfully retrieved salinity data")
            else:
                raise ValueError("Failed to retrieve salinity data")
                
        except Exception as e:
            logger.error(f"Failed to retrieve required datasets: {e}")
            raise HTTPException(status_code=404, detail=str(e))
        
        # Fetch lagged chlorophyll data (preferred over current date)
        try:
            if lagged_dates['chlorophyll_lag_days'] > 0:
                lagged_chlorophyll_data = nasa_manager.download_data(
                    'chlorophyll', lagged_dates['chlorophyll_lag_date']
                )
                if lagged_chlorophyll_data is not None:
                    datasets['chlorophyll'] = lagged_chlorophyll_data
                    logger.info(f"Successfully retrieved lagged chlorophyll data from {lagged_dates['chlorophyll_lag_date']}")
                else:
                    # Fallback to current date chlorophyll
                    logger.warning(f"Could not retrieve lagged chlorophyll data, trying current date")
                    datasets['chlorophyll'] = nasa_manager.download_data('chlorophyll', target_date)
            else:
                # No lag needed, fetch current date
                datasets['chlorophyll'] = nasa_manager.download_data('chlorophyll', target_date)
        except Exception as e:
            logger.error(f"Failed to retrieve chlorophyll data: {e}")
            raise HTTPException(status_code=404, detail=f"Chlorophyll data retrieval failed: {e}")
        
        # Fetch lagged SST data (preferred over current date)
        try:
            if lagged_dates['temperature_lag_days'] > 0:
                lagged_sst_data = nasa_manager.download_data(
                    'sst', lagged_dates['temperature_lag_date']
                )
                if lagged_sst_data is not None:
                    datasets['sst'] = lagged_sst_data
                    logger.info(f"Successfully retrieved lagged SST data from {lagged_dates['temperature_lag_date']}")
                else:
                    # Fallback to current date SST
                    logger.warning(f"Could not retrieve lagged SST data, trying current date")
                    datasets['sst'] = nasa_manager.download_data('sst', target_date)
            else:
                # No lag needed, fetch current date
                datasets['sst'] = nasa_manager.download_data('sst', target_date)
        except Exception as e:
            logger.error(f"Failed to retrieve SST data: {e}")
            raise HTTPException(status_code=404, detail=f"SST data retrieval failed: {e}")
        
        # Cache datasets for overlay reuse
        _cache_data(target_date, None, datasets)
        logger.info("All required datasets successfully retrieved with optimized lag-based fetching")
        
        # Fetch anthropogenic pressure data (GFW)
        logger.info("--- Fetching Anthropogenic Pressure Data (GFW) ---")
        fishing_pressure_data = None
        shipping_density_data = None
        gfw_data_available = {'fishing': False, 'shipping': False}
        
        try:
            # Fetch fishing pressure data
            fishing_pressure_data = gfw_manager.fetch_fishing_effort(target_date, target_date)
            if fishing_pressure_data is not None:
                gfw_data_available['fishing'] = True
                logger.info("Successfully retrieved fishing pressure data from GFW")
            else:
                logger.warning("Fishing pressure data unavailable - using neutral values")
        except Exception as e:
            logger.error(f"Error fetching fishing pressure data: {e}")
            logger.warning("Continuing with neutral fishing pressure")
        
        try:
            # Fetch shipping density data
            shipping_density_data = gfw_manager.fetch_vessel_density(target_date, target_date)
            if shipping_density_data is not None:
                gfw_data_available['shipping'] = True
                logger.info("Successfully retrieved shipping density data from GFW")
            else:
                logger.warning("Shipping density data unavailable - using neutral values")
        except Exception as e:
            logger.error(f"Error fetching shipping density data: {e}")
            logger.warning("Continuing with neutral shipping density")
        
        logger.info(f"GFW data availability: fishing={gfw_data_available['fishing']}, shipping={gfw_data_available['shipping']}")
        
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
        
        # Calculate HSI with optimized data (lagged data already in datasets)
        try:
            hsi_result = hsi_model.calculate_hsi(
                chlorophyll_data=datasets['chlorophyll'],
                sea_level_data=datasets['sea_level'],
                sst_data=datasets['sst'],
                salinity_data=datasets['salinity'],
                shark_species=shark_species,
                target_date=target_date,
                lagged_chlorophyll_data=lagged_chlorophyll_data,
                lagged_sst_data=lagged_sst_data,
                fishing_pressure_data=fishing_pressure_data,
                shipping_density_data=shipping_density_data,
                use_enhanced_model=True
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
            # Convert to GeoJSON for map visualization with caching
            geojson_data = convert_hsi_to_geojson_cached(
                hsi_result,
                target_date=target_date,
                shark_species=shark_species,
                threshold=threshold
            )
            
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
                    "anthropogenic_data_available": gfw_data_available,
                    "anthropogenic_data_source": gfw_manager.get_data_attribution(),
                    "processing_area": "Global",
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
                    "anthropogenic_data_available": gfw_data_available,
                    "anthropogenic_data_source": gfw_manager.get_data_attribution(),
                    "processing_area": "Global"
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
    target_date: str = Query(..., description="Target date in YYYY-MM-DD format")
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

        # Download along-track data (no geographic filtering)
        along_track_data = nasa_manager.download_along_track_data(target_date)
        
        if along_track_data is None:
            raise HTTPException(
                status_code=404,
                detail=f"No along-track data available for {target_date}"
            )
        
        # Convert to GeoJSON for visualization
        geojson_data = convert_dataset_to_geojson(
            along_track_data,
            'sea_level',
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
    target_date: str = Query(..., description="Target date in YYYY-MM-DD format")
):
    """
    Get NASA-SSH combined ascending and descending pass data for enhanced coverage

    This endpoint fetches both ascending and descending pass data and combines them
    to provide improved spatial coverage, particularly in the western hemisphere.

    Args:
        target_date: Date in YYYY-MM-DD format

    Returns:
        GeoJSON representation of combined pass sea level data
    """
    try:
        # Validate inputs
        try:
            datetime.strptime(target_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        # Download sea level data (no geographic filtering)
        logger.info(f"Downloading NASA-SSH data for {target_date}")
        data = nasa_manager.download_data('sea_level', target_date)
        
        if data is None:
            raise HTTPException(
                status_code=404,
                detail=f"No sea level data available for {target_date}"
            )
        
        # Convert to GeoJSON
        geojson_data = convert_dataset_to_geojson(
            data,
            'sea_level',
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

@router.get("/cache/stats")
async def get_cache_stats():
    """Get GeoJSON cache statistics"""
    try:
        cache_manager = get_geojson_cache()
        stats = cache_manager.get_cache_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cache statistics")

@router.delete("/cache/invalidate")
async def invalidate_cache(
    cache_type: Optional[str] = Query(None, description="Cache type to invalidate (hsi, overlay, heatmap)"),
    target_date: Optional[str] = Query(None, description="Target date to invalidate (YYYY-MM-DD)"),
    shark_species: Optional[str] = Query(None, description="Shark species to invalidate")
):
    """Invalidate GeoJSON cache entries"""
    try:
        cache_manager = get_geojson_cache()
        count = cache_manager.invalidate_cache(cache_type, target_date, shark_species)
        return {"status": "success", "invalidated_entries": count}
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to invalidate cache")

@router.delete("/cache/clear")
async def clear_cache():
    """Clear all GeoJSON cache data"""
    try:
        cache_manager = get_geojson_cache()
        count = cache_manager.clear_all_cache()
        return {"status": "success", "cleared_files": count}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")

@router.post("/cache/cleanup")
async def cleanup_cache(
    cleanup_type: str = Query("maintenance", description="Type of cleanup: 'maintenance', 'expired', 'old', 'size'"),
    days_old: int = Query(7, description="Days old threshold for 'old' cleanup"),
    max_size_mb: int = Query(500, description="Maximum size in MB for 'size' cleanup"),
    ttl_hours: int = Query(24, description="TTL in hours for 'expired' cleanup")
):
    """Clean up GeoJSON cache data"""
    try:
        if cleanup_type == "maintenance":
            results = run_maintenance_cleanup()
            return {"status": "success", "results": results}
        elif cleanup_type == "expired":
            count = cleanup_expired_cache(ttl_hours)
            return {"status": "success", "cleaned_entries": count}
        elif cleanup_type == "old":
            count = cleanup_old_cache_by_date(days_old)
            return {"status": "success", "cleaned_entries": count}
        elif cleanup_type == "size":
            count = cleanup_cache_by_size(max_size_mb)
            return {"status": "success", "cleaned_entries": count}
        else:
            raise HTTPException(status_code=400, detail="Invalid cleanup type. Use: maintenance, expired, old, size")
    except Exception as e:
        logger.error(f"Error during cache cleanup: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup cache: {str(e)}")
