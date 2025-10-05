#!/usr/bin/env python3
"""
Test script for GeoJSON caching system
Demonstrates cache functionality and performance
"""

import sys
import os
import time
import logging
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from utils.geojson_cache import get_geojson_cache
from utils.cache_cleanup import run_maintenance_cleanup
import numpy as np
import xarray as xr

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_dataset():
    """Create a test dataset for caching demonstration"""
    # Create a small test dataset
    lats = np.linspace(-90, 90, 10)
    lons = np.linspace(-180, 180, 20)
    
    # Create test HSI data
    hsi_data = np.random.rand(len(lats), len(lons))
    
    dataset = xr.Dataset({
        'hsi': (['lat', 'lon'], hsi_data),
        'chlorophyll_suitability': (['lat', 'lon'], np.random.rand(len(lats), len(lons))),
        'sea_level_suitability': (['lat', 'lon'], np.random.rand(len(lats), len(lons))),
        'temperature_suitability': (['lat', 'lon'], np.random.rand(len(lats), len(lons))),
        'salinity_suitability': (['lat', 'lon'], np.random.rand(len(lats), len(lons)))
    }, coords={
        'lat': lats,
        'lon': lons
    })
    
    return dataset

def test_hsi_caching():
    """Test HSI GeoJSON caching"""
    logger.info("Testing HSI GeoJSON caching...")
    
    cache_manager = get_geojson_cache()
    
    # Create test data
    test_dataset = create_test_dataset()
    target_date = "2025-01-15"
    shark_species = "tiger_shark"
    geographic_bounds = {'north': 40, 'south': 30, 'east': -70, 'west': -80}
    
    # Test features (simplified)
    test_features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[-80, 30], [-70, 30], [-70, 40], [-80, 40], [-80, 30]]]
            },
            "properties": {
                "hsi": 0.8,
                "lat": 35.0,
                "lon": -75.0,
                "chlorophyll_suitability": 0.7,
                "sea_level_suitability": 0.6,
                "temperature_suitability": 0.9,
                "salinity_suitability": 0.5
            }
        }
    ]
    
    # Test caching
    start_time = time.time()
    success = cache_manager.cache_features(
        features=test_features,
        cache_type='hsi',
        target_date=target_date,
        shark_species=shark_species,
        geographic_bounds=geographic_bounds,
        threshold=0.5
    )
    cache_time = time.time() - start_time
    
    if success:
        logger.info(f"✓ Successfully cached HSI features in {cache_time:.3f}s")
    else:
        logger.error("✗ Failed to cache HSI features")
        return False
    
    # Test retrieval
    start_time = time.time()
    cached_features = cache_manager.get_cached_features(
        cache_type='hsi',
        target_date=target_date,
        shark_species=shark_species,
        geographic_bounds=geographic_bounds,
        threshold=0.5
    )
    retrieval_time = time.time() - start_time
    
    if cached_features:
        logger.info(f"✓ Successfully retrieved {len(cached_features)} cached features in {retrieval_time:.3f}s")
        logger.info(f"  First feature HSI value: {cached_features[0]['properties']['hsi']}")
    else:
        logger.error("✗ Failed to retrieve cached features")
        return False
    
    return True

def test_overlay_caching():
    """Test overlay GeoJSON caching"""
    logger.info("Testing overlay GeoJSON caching...")
    
    cache_manager = get_geojson_cache()
    
    # Test features for overlay
    test_features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[-80, 30], [-70, 30], [-70, 40], [-80, 40], [-80, 30]]]
            },
            "properties": {
                "chlorophyll": 2.5,
                "lat": 35.0,
                "lon": -75.0
            }
        }
    ]
    
    target_date = "2025-01-15"
    overlay_type = "chlorophyll"
    
    # Test caching
    success = cache_manager.cache_features(
        features=test_features,
        cache_type='overlay',
        target_date=target_date,
        overlay_type=overlay_type,
        threshold=0.0,
        density_factor=4
    )
    
    if success:
        logger.info("✓ Successfully cached overlay features")
    else:
        logger.error("✗ Failed to cache overlay features")
        return False
    
    # Test retrieval
    cached_features = cache_manager.get_cached_features(
        cache_type='overlay',
        target_date=target_date,
        overlay_type=overlay_type,
        threshold=0.0,
        density_factor=4
    )
    
    if cached_features:
        logger.info(f"✓ Successfully retrieved {len(cached_features)} cached overlay features")
        logger.info(f"  First feature chlorophyll value: {cached_features[0]['properties']['chlorophyll']}")
    else:
        logger.error("✗ Failed to retrieve cached overlay features")
        return False
    
    return True

def test_cache_management():
    """Test cache management functions"""
    logger.info("Testing cache management...")
    
    cache_manager = get_geojson_cache()
    
    # Get cache stats
    stats = cache_manager.get_cache_stats()
    logger.info(f"Cache stats: {stats}")
    
    # Test invalidation
    invalidated = cache_manager.invalidate_cache(cache_type='hsi')
    logger.info(f"✓ Invalidated {invalidated} HSI cache entries")
    
    # Test cleanup
    results = run_maintenance_cleanup()
    logger.info(f"✓ Maintenance cleanup results: {results}")
    
    return True

def main():
    """Run all cache tests"""
    logger.info("Starting GeoJSON cache system tests...")
    
    try:
        # Test HSI caching
        if not test_hsi_caching():
            logger.error("HSI caching test failed")
            return 1
        
        # Test overlay caching
        if not test_overlay_caching():
            logger.error("Overlay caching test failed")
            return 1
        
        # Test cache management
        if not test_cache_management():
            logger.error("Cache management test failed")
            return 1
        
        logger.info("✓ All cache tests passed successfully!")
        
        # Show final cache stats
        cache_manager = get_geojson_cache()
        final_stats = cache_manager.get_cache_stats()
        logger.info(f"Final cache stats: {final_stats}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
