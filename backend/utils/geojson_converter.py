"""
GeoJSON Converter for HSI Data
Converts HSI grid data to GeoJSON format for map visualization
"""

import numpy as np
import xarray as xr
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def convert_hsi_to_geojson(hsi_data: xr.Dataset, threshold: float = 0.5) -> List[Dict[str, Any]]:
    """
    Convert HSI data to GeoJSON format for map visualization
    
    Args:
        hsi_data: HSI dataset with lat, lon, and hsi values
        threshold: Minimum HSI value to include in output
    
    Returns:
        List of GeoJSON features
    """
    try:
        features = []
        
        # Extract coordinates and HSI values
        hsi = hsi_data['hsi']
        lats = hsi.lat.values
        lons = hsi.lon.values
        
        # Create grid cells as polygons
        for i, lat in enumerate(lats[:-1]):
            for j, lon in enumerate(lons[:-1]):
                hsi_value = float(hsi.isel(lat=i, lon=j).values)
                
                # Only include cells above threshold
                if hsi_value >= threshold and not np.isnan(hsi_value):
                    # Create polygon coordinates
                    lat_step = lats[i+1] - lat
                    lon_step = lons[j+1] - lon
                    
                    coordinates = [
                        [
                            [lon, lat],
                            [lon + lon_step, lat],
                            [lon + lon_step, lat + lat_step],
                            [lon, lat + lat_step],
                            [lon, lat]
                        ]
                    ]
                    
                    # Create feature
                    feature = {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": coordinates
                        },
                        "properties": {
                            "hsi": hsi_value,
                            "lat": float(lat + lat_step/2),
                            "lon": float(lon + lon_step/2)
                        }
                    }
                    
                    features.append(feature)
        
        logger.info(f"Converted HSI data to {len(features)} GeoJSON features")
        return features
        
    except Exception as e:
        logger.error(f"GeoJSON conversion failed: {e}")
        return []

def convert_hsi_to_heatmap_data(hsi_data: xr.Dataset, max_points: int = 10000) -> List[Dict[str, Any]]:
    """
    Convert HSI data to heatmap format for efficient visualization
    
    Args:
        hsi_data: HSI dataset
        max_points: Maximum number of points to return
    
    Returns:
        List of heatmap points
    """
    try:
        points = []
        
        # Extract coordinates and HSI values
        hsi = hsi_data['hsi']
        lats = hsi.lat.values
        lons = hsi.lon.values
        
        # Sample points if dataset is too large
        total_points = len(lats) * len(lons)
        step = max(1, total_points // max_points)
        
        count = 0
        for i, lat in enumerate(lats):
            for j, lon in enumerate(lons):
                if count % step == 0:
                    hsi_value = float(hsi.isel(lat=i, lon=j).values)
                    
                    if not np.isnan(hsi_value) and hsi_value > 0:
                        point = {
                            "lat": float(lat),
                            "lng": float(lon),
                            "intensity": hsi_value
                        }
                        points.append(point)
                
                count += 1
        
        logger.info(f"Converted HSI data to {len(points)} heatmap points")
        return points
        
    except Exception as e:
        logger.error(f"Heatmap conversion failed: {e}")
        return []

def get_hsi_color_scale() -> Dict[str, Any]:
    """Get color scale for HSI visualization"""
    return {
        "colors": [
            {"value": 0.0, "color": "rgba(0, 0, 255, 0.1)"},    # Blue for low suitability
            {"value": 0.2, "color": "rgba(0, 255, 255, 0.3)"},  # Cyan
            {"value": 0.4, "color": "rgba(0, 255, 0, 0.5)"},    # Green
            {"value": 0.6, "color": "rgba(255, 255, 0, 0.7)"},  # Yellow
            {"value": 0.8, "color": "rgba(255, 165, 0, 0.8)"},  # Orange
            {"value": 1.0, "color": "rgba(255, 0, 0, 1.0)"}     # Red for high suitability
        ],
        "min": 0.0,
        "max": 1.0
    }
