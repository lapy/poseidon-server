"""
GeoJSON Converter for HSI Data
Converts HSI grid data to GeoJSON format for map visualization
"""

import numpy as np
import xarray as xr
from models.hsi_model import HSIModel
from typing import List, Dict, Any
import logging

from .geojson_cache import get_geojson_cache
logger = logging.getLogger(__name__)


def convert_hsi_to_geojson_cached(hsi_data: xr.Dataset, target_date: str, shark_species: str, threshold: float = 0.5) -> List[Dict[str, Any]]:
    """
    Convert HSI data to GeoJSON format with caching support
    
    Args:
        hsi_data: HSI dataset with lat, lon, and hsi values
        target_date: Target date for caching
        shark_species: Shark species for caching
        threshold: Minimum HSI value to include in output
    
    Returns:
        List of GeoJSON features
    """
    cache_manager = get_geojson_cache()
    
    # Try to get from cache first
    cached_features = cache_manager.get_cached_features(
        cache_type='hsi',
        target_date=target_date,
        shark_species=shark_species,
        threshold=threshold
    )
    
    if cached_features is not None:
        logger.info(f"Using cached HSI GeoJSON features for {shark_species} on {target_date}")
        return cached_features
    
    # Generate features if not cached
    logger.info(f"Generating new HSI GeoJSON features for {shark_species} on {target_date}")
    features = convert_hsi_to_geojson(hsi_data, threshold, shark_species)
    
    # Cache the results
    cache_manager.cache_features(
        features=features,
        cache_type='hsi',
        target_date=target_date,
        shark_species=shark_species,
        threshold=threshold
    )
    
    return features

def convert_hsi_to_geojson(hsi_data: xr.Dataset, threshold: float = 0.5, shark_species: str = None) -> List[Dict[str, Any]]:
    """
    Convert HSI data to GeoJSON format for map visualization

    Args:
        hsi_data: HSI dataset with lat, lon, and hsi values
        threshold: Minimum HSI value to include in output
        shark_species: Shark species for component contribution calculation

    Returns:
        List of GeoJSON features
    """
    try:
        features = []
        
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
                    chl_val = 0.0
                    sl_val = 0.0
                    temp_val = 0.0

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

                    # Calculate component contributions if we have valid suitability values and shark species
                    if shark_species and chl_val > 0 and sl_val > 0 and temp_val > 0:
                        try:
                            hsi_model = HSIModel()
                            profile = hsi_model.shark_profiles.get(shark_species)
                            if profile:
                                contributions = hsi_model.calculate_component_contributions(
                                    chl_val, sl_val, temp_val, profile
                                )
                                properties["component_contributions"] = contributions
                        except Exception as e:
                            logger.warning(f"Could not calculate component contributions: {e}")
                    
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

def convert_dataset_to_geojson_cached(dataset: xr.Dataset, variable: str, target_date: str, overlay_type: str, threshold: float = 0.0, density_factor: int = 4) -> List[Dict[str, Any]]:
    """
    Convert raw dataset to GeoJSON format with caching support
    
    Args:
        dataset: Raw dataset with lat, lon, and variable values
        variable: Variable name to extract (e.g., 'chlorophyll', 'sea_level', 'salinity')
        target_date: Target date for caching
        overlay_type: Type of overlay for caching
        threshold: Minimum value to include in output (default 0.0 for all data)
        density_factor: Factor to reduce density (every Nth point, default 4)
    
    Returns:
        List of GeoJSON features
    """
    cache_manager = get_geojson_cache()
    
    # Try to get from cache first
    cached_features = cache_manager.get_cached_features(
        cache_type='overlay',
        target_date=target_date,
        overlay_type=overlay_type,
        threshold=threshold,
        density_factor=density_factor
    )
    
    if cached_features is not None:
        logger.info(f"Using cached {overlay_type} GeoJSON features for {target_date}")
        return cached_features
    
    # Generate features if not cached
    logger.info(f"Generating new {overlay_type} GeoJSON features for {target_date}")
    features = convert_dataset_to_geojson(dataset, variable, threshold, density_factor)
    
    # Cache the results
    cache_manager.cache_features(
        features=features,
        cache_type='overlay',
        target_date=target_date,
        overlay_type=overlay_type,
        threshold=threshold,
        density_factor=density_factor
    )
    
    return features

def convert_dataset_to_geojson(dataset: xr.Dataset, variable: str, threshold: float = 0.0, density_factor: int = 4) -> List[Dict[str, Any]]:
    """
    Convert raw dataset to GeoJSON format for overlay visualization
    
    Args:
        dataset: Raw dataset with lat, lon, and variable values
        variable: Variable name to extract (e.g., 'chlorophyll', 'sea_level', 'salinity')
        threshold: Minimum value to include in output (default 0.0 for all data)
        density_factor: Factor to reduce density (every Nth point, default 4)
    
    Returns:
        List of GeoJSON features
    """
    try:
        features = []
        
        # Extract coordinates and variable values
        # Handle special case for oceanographic overlay
        if variable == 'oceanographic':
            # For oceanographic overlay, use sea_level data but name it oceanographic
            data_var = dataset['sea_level']
            output_variable = 'oceanographic'
        else:
            data_var = dataset[variable]
            output_variable = variable
            
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
                        output_variable: value,
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

def convert_hsi_to_heatmap_data_cached(hsi_data: xr.Dataset, target_date: str, shark_species: str, max_points: int = 10000) -> List[Dict[str, Any]]:
    """
    Convert HSI data to heatmap format with caching support
    
    Args:
        hsi_data: HSI dataset
        target_date: Target date for caching
        shark_species: Shark species for caching
        max_points: Maximum number of points to return
    
    Returns:
        List of heatmap points
    """
    cache_manager = get_geojson_cache()
    
    # Try to get from cache first
    cached_features = cache_manager.get_cached_features(
        cache_type='heatmap',
        target_date=target_date,
        shark_species=shark_species,
        threshold=0.0,  # Heatmap doesn't use threshold
        density_factor=max_points  # Use max_points as density factor for cache key
    )
    
    if cached_features is not None:
        logger.info(f"Using cached heatmap data for {shark_species} on {target_date}")
        return cached_features
    
    # Generate features if not cached
    logger.info(f"Generating new heatmap data for {shark_species} on {target_date}")
    features = convert_hsi_to_heatmap_data(hsi_data, max_points)
    
    # Cache the results
    cache_manager.cache_features(
        features=features,
        cache_type='heatmap',
        target_date=target_date,
        shark_species=shark_species,
        threshold=0.0,
        density_factor=max_points
    )
    
    return features

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
