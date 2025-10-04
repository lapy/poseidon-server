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

from models.hsi_model import HSIModel
from data.nasa_data import NASADataManager
from utils.geojson_converter import convert_hsi_to_geojson

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize models
hsi_model = HSIModel()
nasa_manager = NASADataManager()

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
        
        # Get current NASA satellite data with adjacent time periods for complete coverage
        datasets = nasa_manager.get_data_for_date_with_adjacent(target_date, geographic_bounds)
        
        # Get lagged data if available
        lagged_chlorophyll_data = None
        lagged_sst_data = None
        
        try:
            # Try to get lagged chlorophyll data with adjacent time periods
            if lagged_dates['chlorophyll_lag_days'] > 0:
                lagged_chlorophyll_datasets = nasa_manager.get_data_for_date_with_adjacent(
                    lagged_dates['chlorophyll_lag_date'], geographic_bounds
                )
                lagged_chlorophyll_data = lagged_chlorophyll_datasets.get('chlorophyll')
                if lagged_chlorophyll_data is not None:
                    logger.info(f"Successfully retrieved lagged chlorophyll data from {lagged_dates['chlorophyll_lag_date']} with adjacent periods")
                else:
                    logger.warning(f"Could not retrieve lagged chlorophyll data from {lagged_dates['chlorophyll_lag_date']}")
        except Exception as e:
            logger.warning(f"Failed to retrieve lagged chlorophyll data: {e}")
        
        try:
            # Try to get lagged SST data with adjacent time periods
            if lagged_dates['temperature_lag_days'] > 0:
                lagged_sst_datasets = nasa_manager.get_data_for_date_with_adjacent(
                    lagged_dates['temperature_lag_date'], geographic_bounds
                )
                lagged_sst_data = lagged_sst_datasets.get('sst')
                if lagged_sst_data is not None:
                    logger.info(f"Successfully retrieved lagged SST data from {lagged_dates['temperature_lag_date']} with adjacent periods")
                else:
                    logger.warning(f"Could not retrieve lagged SST data from {lagged_dates['temperature_lag_date']}")
        except Exception as e:
            logger.warning(f"Failed to retrieve lagged SST data: {e}")
        
        # Check if all required current datasets are available
        missing_datasets = []
        for name, data in datasets.items():
            if data is None:
                missing_datasets.append(name)
            elif name == 'sst' and (not hasattr(data, 'data_vars') or not data.data_vars or 'sst' not in data.data_vars):
                missing_datasets.append(name)
                logger.error(f"SST dataset is empty or missing 'sst' variable - HSI calculation cannot proceed")
            elif name == 'chlorophyll' and (not hasattr(data, 'data_vars') or not data.data_vars or 'chlorophyll' not in data.data_vars):
                missing_datasets.append(name)
                logger.warning(f"Chlorophyll dataset is empty or missing 'chlorophyll' variable")
            elif name == 'sea_level' and (not hasattr(data, 'data_vars') or not data.data_vars or 'sea_level' not in data.data_vars):
                missing_datasets.append(name)
                logger.warning(f"Sea level dataset is empty or missing 'sea_level' variable")
        
        if missing_datasets:
            raise HTTPException(
                status_code=404,
                detail=f"Missing or invalid data for datasets: {missing_datasets}"
            )
        
        # Calculate HSI with lagged data
        sea_level_data = datasets.get('sea_level')
        salinity_data = datasets.get('salinity')
        
        # Check if salinity data is available
        if salinity_data is None:
            logger.error("Salinity data not available - cannot calculate HSI without salinity filtering")
            raise HTTPException(
                status_code=422,
                detail="Salinity data is required but not available. Cannot calculate HSI without salinity filtering."
            )
        
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
                        "sea_level_coverage": "Limited in western hemisphere due to NASA-SSH satellite tracks and ocean basin separation",
                        "missing_data_handling": "Adjacent time periods (±7 days) used to fill coverage gaps, neutral sea level suitability (0.5) for remaining gaps",
                        "temporal_merge": "Data from target date ±7 days merged to maximize global coverage"
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
