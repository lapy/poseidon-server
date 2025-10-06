"""
Cache Cleanup Utilities
Handles automatic cleanup and maintenance of cache files
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .geojson_cache import get_geojson_cache

logger = logging.getLogger(__name__)

def cleanup_expired_cache(ttl_hours: Optional[int] = None) -> int:
    """
    Clean up expired cache entries
    
    Args:
        ttl_hours: TTL in hours (uses cache manager default if None)
    
    Returns:
        Number of entries cleaned up
    """
    try:
        cache_manager = get_geojson_cache()
        
        # Get all metadata files
        cache_dir = cache_manager.cache_dir
        cleaned_count = 0
        
        for metadata_file in cache_dir.glob("*.meta.json"):
            try:
                import json
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Check if cache is expired
                created_time = datetime.fromisoformat(metadata['created_at'])
                ttl = timedelta(hours=ttl_hours or cache_manager.default_ttl_hours)
                
                if datetime.now() - created_time > ttl:
                    cache_key = metadata.get('cache_key', metadata_file.stem.replace('.meta', ''))
                    cache_manager._remove_cache_entry(cache_key)
                    cleaned_count += 1
                    logger.info(f"Cleaned up expired cache entry: {cache_key}")
                    
            except Exception as e:
                logger.error(f"Error processing metadata file {metadata_file}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired cache entries")
        
        return cleaned_count
        
    except Exception as e:
        logger.error(f"Error during cache cleanup: {e}")
        return 0

def cleanup_old_cache_by_date(days_old: int = 7) -> int:
    """
    Clean up cache entries older than specified days
    
    Args:
        days_old: Remove entries older than this many days
    
    Returns:
        Number of entries cleaned up
    """
    try:
        cache_manager = get_geojson_cache()
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        cleaned_count = 0
        
        for metadata_file in cache_manager.cache_dir.glob("*.meta.json"):
            try:
                import json
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Check if cache is older than cutoff
                created_time = datetime.fromisoformat(metadata['created_at'])
                
                if created_time < cutoff_date:
                    cache_key = metadata.get('cache_key', metadata_file.stem.replace('.meta', ''))
                    cache_manager._remove_cache_entry(cache_key)
                    cleaned_count += 1
                    logger.info(f"Cleaned up old cache entry: {cache_key} (created: {created_time.isoformat()})")
                    
            except Exception as e:
                logger.error(f"Error processing metadata file {metadata_file}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old cache entries (>{days_old} days old)")
        
        return cleaned_count
        
    except Exception as e:
        logger.error(f"Error during old cache cleanup: {e}")
        return 0

def cleanup_cache_by_size(max_size_mb: int = 500) -> int:
    """
    Clean up cache entries to stay under size limit
    
    Args:
        max_size_mb: Maximum cache size in MB
    
    Returns:
        Number of entries cleaned up
    """
    try:
        cache_manager = get_geojson_cache()
        
        # Get current cache size
        total_size = sum(f.stat().st_size for f in cache_manager.cache_dir.glob("*") if f.is_file())
        total_size_mb = total_size / (1024 * 1024)
        
        if total_size_mb <= max_size_mb:
            logger.info(f"Cache size ({total_size_mb:.1f}MB) is within limit ({max_size_mb}MB)")
            return 0
        
        logger.info(f"Cache size ({total_size_mb:.1f}MB) exceeds limit ({max_size_mb}MB), cleaning up...")
        
        # Use the cache manager's built-in cleanup
        cache_manager._cleanup_oldest_entries()
        
        # Count how many were actually removed
        new_size = sum(f.stat().st_size for f in cache_manager.cache_dir.glob("*") if f.is_file())
        removed_size_mb = (total_size - new_size) / (1024 * 1024)
        
        logger.info(f"Removed {removed_size_mb:.1f}MB from cache")
        return int(removed_size_mb * 1024 / 1024)  # Approximate file count
        
    except Exception as e:
        logger.error(f"Error during size-based cache cleanup: {e}")
        return 0

def run_maintenance_cleanup() -> dict:
    """
    Run comprehensive cache maintenance
    
    Returns:
        Dictionary with cleanup results
    """
    results = {
        'expired_cleaned': 0,
        'old_cleaned': 0,
        'size_cleaned': 0,
        'total_files_before': 0,
        'total_files_after': 0
    }
    
    try:
        cache_manager = get_geojson_cache()
        
        # Count files before cleanup
        results['total_files_before'] = len(list(cache_manager.cache_dir.glob("*")))
        
        # Clean up expired entries
        results['expired_cleaned'] = cleanup_expired_cache()
        
        # Clean up old entries (older than 7 days)
        results['old_cleaned'] = cleanup_old_cache_by_date(days_old=7)
        
        # Clean up by size if needed
        results['size_cleaned'] = cleanup_cache_by_size(max_size_mb=500)
        
        # Count files after cleanup
        results['total_files_after'] = len(list(cache_manager.cache_dir.glob("*")))
        
        logger.info(f"Cache maintenance completed: {results}")
        
    except Exception as e:
        logger.error(f"Error during maintenance cleanup: {e}")
        results['error'] = str(e)
    
    return results

