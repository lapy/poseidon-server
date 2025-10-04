"""
API Routes for Shark Foraging Hotspot Prediction
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, date
from typing import Optional, Dict, Any
import logging
import json

from models.hsi_model import HSIModel
from data.nasa_data import NASADataManager
from utils.geojson_converter import convert_hsi_to_geojson

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize models
hsi_model = HSIModel()
nasa_manager = NASADataManager()

@router.get("/hotspots")
async def get_hotspots(
    target_date: str = Query(..., description="Target date in YYYY-MM-DD format"),
    shark_species: str = Query(..., description="Shark species: 'great_white' or 'tiger_shark'"),
    format: str = Query("geojson", description="Output format: 'geojson' or 'raw'")
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
        
        logger.info(f"Processing request for {shark_species} on {target_date}")
        
        # Calculate lagged dates for trophic lag
        lagged_dates = hsi_model.calculate_lagged_dates(target_date, shark_species)
        logger.info(f"Lagged dates: {lagged_dates}")
        
        # Get current NASA satellite data
        datasets = nasa_manager.get_data_for_date(target_date)
        
        # Get lagged data if available
        lagged_chlorophyll_data = None
        lagged_sst_data = None
        
        try:
            # Try to get lagged chlorophyll data
            if lagged_dates['chlorophyll_lag_days'] > 0:
                lagged_chlorophyll_datasets = nasa_manager.get_data_for_date(
                    lagged_dates['chlorophyll_lag_date']
                )
                lagged_chlorophyll_data = lagged_chlorophyll_datasets.get('chlorophyll')
                if lagged_chlorophyll_data is not None:
                    logger.info(f"Successfully retrieved lagged chlorophyll data from {lagged_dates['chlorophyll_lag_date']}")
                else:
                    logger.warning(f"Could not retrieve lagged chlorophyll data from {lagged_dates['chlorophyll_lag_date']}")
        except Exception as e:
            logger.warning(f"Failed to retrieve lagged chlorophyll data: {e}")
        
        try:
            # Try to get lagged SST data
            if lagged_dates['temperature_lag_days'] > 0:
                lagged_sst_datasets = nasa_manager.get_data_for_date(
                    lagged_dates['temperature_lag_date']
                )
                lagged_sst_data = lagged_sst_datasets.get('sst')
                if lagged_sst_data is not None:
                    logger.info(f"Successfully retrieved lagged SST data from {lagged_dates['temperature_lag_date']}")
                else:
                    logger.warning(f"Could not retrieve lagged SST data from {lagged_dates['temperature_lag_date']}")
        except Exception as e:
            logger.warning(f"Failed to retrieve lagged SST data: {e}")
        
        # Check if all required current datasets are available
        missing_datasets = [name for name, data in datasets.items() if data is None]
        if missing_datasets:
            raise HTTPException(
                status_code=404,
                detail=f"Missing data for datasets: {missing_datasets}"
            )
        
        # Calculate HSI with lagged data
        sea_level_data = datasets.get('sea_level')
        
        hsi_result = hsi_model.calculate_hsi(
            chlorophyll_data=datasets['chlorophyll'],
            sea_level_data=sea_level_data,
            sst_data=datasets['sst'],
            shark_species=shark_species,
            target_date=target_date,
            lagged_chlorophyll_data=lagged_chlorophyll_data,
            lagged_sst_data=lagged_sst_data
        )
        
        # Calculate statistics
        stats = hsi_model.get_hsi_statistics(hsi_result)
        
        # Format response based on requested format
        if format.lower() == "geojson":
            # Convert to GeoJSON for map visualization
            geojson_data = convert_hsi_to_geojson(hsi_result)
            
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
                    }
                }
            }
            
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
                    }
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
