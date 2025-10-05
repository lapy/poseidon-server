"""
GeoJSON Converter for HSI Data
Converts HSI grid data to GeoJSON format for map visualization
"""

import numpy as np
import xarray as xr
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def _apply_geographic_filter(data: xr.Dataset, geographic_bounds: Dict) -> xr.Dataset:
    """Apply geographic bounds to dataset"""
    try:
        if geographic_bounds is None:
            return data
        
        # Handle longitude wrapping (e.g., Pacific crossing)
        west = geographic_bounds['west']
        east = geographic_bounds['east']
        
        if west > east:  # Crosses dateline
            # Split into two regions
            data1 = data.sel(
                lat=slice(geographic_bounds['south'], geographic_bounds['north']),
                lon=slice(west, 180)
            )
            data2 = data.sel(
                lat=slice(geographic_bounds['south'], geographic_bounds['north']),
                lon=slice(-180, east)
            )
            # Combine the two regions
            data = xr.concat([data1, data2], dim='lon')
        else:
            # Normal case - no dateline crossing
            data = data.sel(
                lat=slice(geographic_bounds['south'], geographic_bounds['north']),
                lon=slice(west, east)
            )
        
        return data
        
    except Exception as e:
        logger.warning(f"Geographic filtering failed: {e}")
        return data

def convert_hsi_to_geojson(hsi_data: xr.Dataset, threshold: float = 0.5, geographic_bounds: Dict = None) -> List[Dict[str, Any]]:
    """
    Convert HSI data to GeoJSON format for map visualization
    
    Args:
        hsi_data: HSI dataset with lat, lon, and hsi values
        threshold: Minimum HSI value to include in output
        geographic_bounds: Optional geographic bounds dict with 'north', 'south', 'east', 'west'
    
    Returns:
        List of GeoJSON features
    """
    try:
        features = []
        
        # Apply geographic filtering if bounds provided
        if geographic_bounds:
            hsi_data = _apply_geographic_filter(hsi_data, geographic_bounds)
            logger.info(f"Applied geographic filtering to HSI data: {geographic_bounds}")
        
        # Extract coordinates and all suitability values
        hsi = hsi_data['hsi']
        lats = hsi.lat.values
        lons = hsi.lon.values
        
        # Extract suitability values if available
        chlorophyll_suitability = hsi_data.get('chlorophyll_suitability', None)
        sea_level_suitability = hsi_data.get('sea_level_suitability', None)
        temperature_suitability = hsi_data.get('temperature_suitability', None)
        salinity_suitability = hsi_data.get('salinity_suitability', None)
        
        # Create grid cells as polygons
        for i, lat in enumerate(lats[:-1]):
            for j, lon in enumerate(lons[:-1]):
                hsi_raw = hsi.isel(lat=i, lon=j).values
                
                # Skip NaN values
                if np.isnan(hsi_raw):
                    continue
                
                hsi_value = float(hsi_raw)
                
                # Only include cells above threshold
                if hsi_value >= threshold:
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
                    
                    # Create properties with all suitability values
                    properties = {
                        "hsi": hsi_value,
                        "lat": float(lat + lat_step/2),
                        "lon": float(lon + lon_step/2)
                    }
                    
                    # Add suitability values if available
                    if chlorophyll_suitability is not None:
                        chl_val = chlorophyll_suitability.isel(lat=i, lon=j).values
                        properties["chlorophyll_suitability"] = float(chl_val) if not np.isnan(chl_val) else 0.0
                    
                    if sea_level_suitability is not None:
                        sl_val = sea_level_suitability.isel(lat=i, lon=j).values
                        properties["sea_level_suitability"] = float(sl_val) if not np.isnan(sl_val) else 0.0
                    
                    if temperature_suitability is not None:
                        temp_val = temperature_suitability.isel(lat=i, lon=j).values
                        properties["temperature_suitability"] = float(temp_val) if not np.isnan(temp_val) else 0.0
                    
                    if salinity_suitability is not None:
                        sal_val = salinity_suitability.isel(lat=i, lon=j).values
                        properties["salinity_suitability"] = float(sal_val) if not np.isnan(sal_val) else 0.0
                    
                    # Create feature
                    feature = {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": coordinates
                        },
                        "properties": properties
                    }
                    
                    features.append(feature)
        
        logger.info(f"Converted HSI data to {len(features)} GeoJSON features")
        return features
        
    except Exception as e:
        logger.error(f"GeoJSON conversion failed: {e}")
        return []

def convert_dataset_to_geojson(dataset: xr.Dataset, variable: str, geographic_bounds: Dict = None, threshold: float = 0.0, density_factor: int = 4) -> List[Dict[str, Any]]:
    """
    Convert raw dataset to GeoJSON format for overlay visualization
    
    Args:
        dataset: Raw dataset with lat, lon, and variable values
        variable: Variable name to extract (e.g., 'chlorophyll', 'sea_level', 'salinity')
        geographic_bounds: Optional geographic bounds dict with 'north', 'south', 'east', 'west'
        threshold: Minimum value to include in output (default 0.0 for all data)
        density_factor: Factor to reduce density (every Nth point, default 4)
    
    Returns:
        List of GeoJSON features
    """
    try:
        features = []
        
        # Apply geographic filtering if bounds provided
        if geographic_bounds:
            dataset = _apply_geographic_filter(dataset, geographic_bounds)
            logger.info(f"Applied geographic filtering to {variable} data: {geographic_bounds}")
        
        # Extract coordinates and variable values
        data_var = dataset[variable]
        lats = data_var.lat.values
        lons = data_var.lon.values
        
        # Create grid cells as polygons with reduced density
        for i, lat in enumerate(lats[:-1]):
            # Skip rows based on density factor
            if i % density_factor != 0:
                continue
                
            for j, lon in enumerate(lons[:-1]):
                # Skip columns based on density factor
                if j % density_factor != 0:
                    continue
                
                value_raw = data_var.isel(lat=i, lon=j).values
                
                # Skip NaN values
                if np.isnan(value_raw):
                    continue
                
                value = float(value_raw)
                
                # Only include cells above threshold
                if value >= threshold:
                    # Create polygon coordinates with larger step size
                    lat_step = (lats[i+1] - lat) * density_factor
                    lon_step = (lons[j+1] - lon) * density_factor
                    
                    coordinates = [
                        [
                            [lon, lat],
                            [lon + lon_step, lat],
                            [lon + lon_step, lat + lat_step],
                            [lon, lat + lat_step],
                            [lon, lat]
                        ]
                    ]
                    
                    # Create properties
                    properties = {
                        variable: value,
                        "lat": float(lat + lat_step/2),
                        "lon": float(lon + lon_step/2)
                    }
                    
                    # Create feature
                    feature = {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": coordinates
                        },
                        "properties": properties
                    }
                    
                    features.append(feature)
        
        logger.info(f"Converted {variable} data to {len(features)} GeoJSON features (density factor: {density_factor})")
        return features
        
    except Exception as e:
        logger.error(f"GeoJSON conversion failed for {variable}: {e}")
        return []

def convert_hsi_to_heatmap_data(hsi_data: xr.Dataset, max_points: int = 10000, geographic_bounds: Dict = None) -> List[Dict[str, Any]]:
    """
    Convert HSI data to heatmap format for efficient visualization
    
    Args:
        hsi_data: HSI dataset
        max_points: Maximum number of points to return
        geographic_bounds: Optional geographic bounds dict with 'north', 'south', 'east', 'west'
    
    Returns:
        List of heatmap points
    """
    try:
        points = []
        
        # Apply geographic filtering if bounds provided
        if geographic_bounds:
            hsi_data = _apply_geographic_filter(hsi_data, geographic_bounds)
            logger.info(f"Applied geographic filtering to HSI heatmap data: {geographic_bounds}")
        
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
                    hsi_raw = hsi.isel(lat=i, lon=j).values
                    
                    # Skip NaN values
                    if np.isnan(hsi_raw):
                        count += 1
                        continue
                    
                    hsi_value = float(hsi_raw)
                    
                    if hsi_value > 0:
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
