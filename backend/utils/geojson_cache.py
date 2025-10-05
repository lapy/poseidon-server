"""
GeoJSON Cache Manager
Handles file-based caching of computed GeoJSON features to avoid recomputation
"""

import json
import os
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)

class GeoJSONCacheManager:
    """Manages file-based caching of GeoJSON features"""
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the cache manager
        
        Args:
            cache_dir: Directory to store cache files (default: data_cache/geojson_cache)
        """
        if cache_dir is None:
            cache_dir = os.path.join(os.getenv("CACHE_DIR", "data_cache"), "geojson_cache")
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache configuration
        self.default_ttl_hours = 24  # Default cache TTL in hours
        self.max_cache_size_mb = 500  # Maximum cache size in MB
        
        logger.info(f"GeoJSON cache initialized at: {self.cache_dir}")
    
    def _generate_cache_key(self, 
                          cache_type: str,
                          target_date: str, 
                          shark_species: Optional[str] = None,
                          geographic_bounds: Optional[Dict] = None,
                          threshold: float = 0.5,
                          density_factor: int = 4,
                          overlay_type: Optional[str] = None) -> str:
        """
        Generate a unique cache key for the given parameters
        
        Args:
            cache_type: Type of cache ('hsi', 'overlay', 'heatmap')
            target_date: Target date for data
            shark_species: Shark species (for HSI cache)
            geographic_bounds: Geographic bounds dict
            threshold: HSI threshold value
            density_factor: Density reduction factor
            overlay_type: Overlay type (for overlay cache)
        
        Returns:
            Unique cache key string
        """
        # Create a dictionary of all parameters
        params = {
            'cache_type': cache_type,
            'target_date': target_date,
            'threshold': threshold,
            'density_factor': density_factor
        }
        
        # Add optional parameters
        if shark_species:
            params['shark_species'] = shark_species
        if overlay_type:
            params['overlay_type'] = overlay_type
        if geographic_bounds:
            # Sort bounds to ensure consistent keys
            params['bounds'] = {
                'north': geographic_bounds.get('north'),
                'south': geographic_bounds.get('south'),
                'east': geographic_bounds.get('east'),
                'west': geographic_bounds.get('west')
            }
        
        # Convert to JSON string and create hash
        params_str = json.dumps(params, sort_keys=True)
        cache_key = hashlib.md5(params_str.encode()).hexdigest()
        
        return cache_key
    
    def _get_cache_file_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key"""
        return self.cache_dir / f"{cache_key}.json"
    
    def _get_metadata_file_path(self, cache_key: str) -> Path:
        """Get the metadata file path for a cache key"""
        return self.cache_dir / f"{cache_key}.meta.json"
    
    def _is_cache_valid(self, cache_key: str, ttl_hours: Optional[int] = None) -> bool:
        """
        Check if cache entry is still valid
        
        Args:
            cache_key: Cache key to check
            ttl_hours: TTL in hours (uses default if None)
        
        Returns:
            True if cache is valid, False otherwise
        """
        metadata_path = self._get_metadata_file_path(cache_key)
        cache_path = self._get_cache_file_path(cache_key)
        
        # Check if both files exist
        if not metadata_path.exists() or not cache_path.exists():
            return False
        
        try:
            # Load metadata
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Check TTL
            created_time = datetime.fromisoformat(metadata['created_at'])
            ttl = timedelta(hours=ttl_hours or self.default_ttl_hours)
            
            if datetime.now() - created_time > ttl:
                logger.info(f"Cache expired for key: {cache_key}")
                return False
            
            # Check file size (ensure file wasn't corrupted)
            if cache_path.stat().st_size == 0:
                logger.warning(f"Cache file is empty for key: {cache_key}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking cache validity for {cache_key}: {e}")
            return False
    
    def get_cached_features(self, 
                          cache_type: str,
                          target_date: str,
                          shark_species: Optional[str] = None,
                          geographic_bounds: Optional[Dict] = None,
                          threshold: float = 0.5,
                          density_factor: int = 4,
                          overlay_type: Optional[str] = None,
                          ttl_hours: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve cached GeoJSON features
        
        Args:
            cache_type: Type of cache ('hsi', 'overlay', 'heatmap')
            target_date: Target date for data
            shark_species: Shark species (for HSI cache)
            geographic_bounds: Geographic bounds dict
            threshold: HSI threshold value
            density_factor: Density reduction factor
            overlay_type: Overlay type (for overlay cache)
            ttl_hours: TTL in hours (uses default if None)
        
        Returns:
            Cached features list or None if not found/invalid
        """
        cache_key = self._generate_cache_key(
            cache_type, target_date, shark_species, geographic_bounds,
            threshold, density_factor, overlay_type
        )
        
        if not self._is_cache_valid(cache_key, ttl_hours):
            return None
        
        try:
            cache_path = self._get_cache_file_path(cache_key)
            with open(cache_path, 'r') as f:
                features = json.load(f)
            
            logger.info(f"Retrieved {len(features)} cached features for {cache_type} on {target_date}")
            return features
            
        except Exception as e:
            logger.error(f"Error loading cached features for {cache_key}: {e}")
            return None
    
    def cache_features(self, 
                      features: List[Dict[str, Any]],
                      cache_type: str,
                      target_date: str,
                      shark_species: Optional[str] = None,
                      geographic_bounds: Optional[Dict] = None,
                      threshold: float = 0.5,
                      density_factor: int = 4,
                      overlay_type: Optional[str] = None) -> bool:
        """
        Cache GeoJSON features to disk
        
        Args:
            features: List of GeoJSON features to cache
            cache_type: Type of cache ('hsi', 'overlay', 'heatmap')
            target_date: Target date for data
            shark_species: Shark species (for HSI cache)
            geographic_bounds: Geographic bounds dict
            threshold: HSI threshold value
            density_factor: Density reduction factor
            overlay_type: Overlay type (for overlay cache)
        
        Returns:
            True if caching was successful, False otherwise
        """
        if not features:
            logger.warning("No features to cache")
            return False
        
        cache_key = self._generate_cache_key(
            cache_type, target_date, shark_species, geographic_bounds,
            threshold, density_factor, overlay_type
        )
        
        try:
            # Save features
            cache_path = self._get_cache_file_path(cache_key)
            with open(cache_path, 'w') as f:
                json.dump(features, f, separators=(',', ':'))  # Compact JSON
            
            # Save metadata
            metadata = {
                'cache_type': cache_type,
                'target_date': target_date,
                'shark_species': shark_species,
                'overlay_type': overlay_type,
                'threshold': threshold,
                'density_factor': density_factor,
                'geographic_bounds': geographic_bounds,
                'feature_count': len(features),
                'created_at': datetime.now().isoformat(),
                'cache_key': cache_key
            }
            
            metadata_path = self._get_metadata_file_path(cache_key)
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Cached {len(features)} {cache_type} features for {target_date}")
            
            # Check cache size and cleanup if necessary
            self._cleanup_if_needed()
            
            return True
            
        except Exception as e:
            logger.error(f"Error caching features for {cache_key}: {e}")
            return False
    
    def invalidate_cache(self, 
                        cache_type: Optional[str] = None,
                        target_date: Optional[str] = None,
                        shark_species: Optional[str] = None) -> int:
        """
        Invalidate cache entries matching the given criteria
        
        Args:
            cache_type: Cache type to invalidate (None for all)
            target_date: Target date to invalidate (None for all)
            shark_species: Shark species to invalidate (None for all)
        
        Returns:
            Number of cache entries invalidated
        """
        invalidated_count = 0
        
        try:
            for metadata_file in self.cache_dir.glob("*.meta.json"):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    # Check if this entry matches the criteria
                    should_invalidate = True
                    
                    if cache_type and metadata.get('cache_type') != cache_type:
                        should_invalidate = False
                    if target_date and metadata.get('target_date') != target_date:
                        should_invalidate = False
                    if shark_species and metadata.get('shark_species') != shark_species:
                        should_invalidate = False
                    
                    if should_invalidate:
                        cache_key = metadata.get('cache_key', metadata_file.stem.replace('.meta', ''))
                        self._remove_cache_entry(cache_key)
                        invalidated_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing metadata file {metadata_file}: {e}")
            
            logger.info(f"Invalidated {invalidated_count} cache entries")
            return invalidated_count
            
        except Exception as e:
            logger.error(f"Error during cache invalidation: {e}")
            return 0
    
    def _remove_cache_entry(self, cache_key: str):
        """Remove a specific cache entry"""
        cache_path = self._get_cache_file_path(cache_key)
        metadata_path = self._get_metadata_file_path(cache_key)
        
        try:
            if cache_path.exists():
                cache_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()
        except Exception as e:
            logger.error(f"Error removing cache entry {cache_key}: {e}")
    
    def _cleanup_if_needed(self):
        """Clean up cache if it exceeds size limits"""
        try:
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*") if f.is_file())
            total_size_mb = total_size / (1024 * 1024)
            
            if total_size_mb > self.max_cache_size_mb:
                logger.info(f"Cache size ({total_size_mb:.1f}MB) exceeds limit ({self.max_cache_size_mb}MB), cleaning up...")
                self._cleanup_oldest_entries()
                
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
    
    def _cleanup_oldest_entries(self):
        """Remove oldest cache entries to free up space"""
        try:
            # Get all metadata files with their creation times
            entries = []
            for metadata_file in self.cache_dir.glob("*.meta.json"):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    created_time = datetime.fromisoformat(metadata['created_at'])
                    cache_key = metadata.get('cache_key', metadata_file.stem.replace('.meta', ''))
                    cache_path = self._get_cache_file_path(cache_key)
                    
                    if cache_path.exists():
                        entries.append((created_time, cache_key, cache_path.stat().st_size))
                        
                except Exception as e:
                    logger.error(f"Error processing metadata file {metadata_file}: {e}")
            
            # Sort by creation time (oldest first)
            entries.sort(key=lambda x: x[0])
            
            # Remove oldest entries until we're under the limit
            current_size = sum(f.stat().st_size for f in self.cache_dir.glob("*") if f.is_file())
            target_size = self.max_cache_size_mb * 0.8 * 1024 * 1024  # 80% of limit
            
            removed_count = 0
            for created_time, cache_key, size in entries:
                if current_size <= target_size:
                    break
                
                self._remove_cache_entry(cache_key)
                current_size -= size
                removed_count += 1
            
            if removed_count > 0:
                logger.info(f"Removed {removed_count} oldest cache entries")
                
        except Exception as e:
            logger.error(f"Error during oldest entries cleanup: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            total_files = 0
            total_size = 0
            cache_types = {}
            date_range = {'earliest': None, 'latest': None}
            
            for metadata_file in self.cache_dir.glob("*.meta.json"):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    total_files += 1
                    
                    # Count by cache type
                    cache_type = metadata.get('cache_type', 'unknown')
                    cache_types[cache_type] = cache_types.get(cache_type, 0) + 1
                    
                    # Track date range
                    target_date = metadata.get('target_date')
                    if target_date:
                        if date_range['earliest'] is None or target_date < date_range['earliest']:
                            date_range['earliest'] = target_date
                        if date_range['latest'] is None or target_date > date_range['latest']:
                            date_range['latest'] = target_date
                    
                    # Add file size
                    cache_key = metadata.get('cache_key', metadata_file.stem.replace('.meta', ''))
                    cache_path = self._get_cache_file_path(cache_key)
                    if cache_path.exists():
                        total_size += cache_path.stat().st_size
                        
                except Exception as e:
                    logger.error(f"Error processing metadata file {metadata_file}: {e}")
            
            return {
                'total_entries': total_files,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'cache_types': cache_types,
                'date_range': date_range,
                'cache_dir': str(self.cache_dir),
                'max_size_mb': self.max_cache_size_mb,
                'default_ttl_hours': self.default_ttl_hours
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'error': str(e)}
    
    def clear_all_cache(self) -> int:
        """Clear all cached data"""
        try:
            removed_count = 0
            for file_path in self.cache_dir.glob("*"):
                if file_path.is_file():
                    file_path.unlink()
                    removed_count += 1
            
            logger.info(f"Cleared {removed_count} cache files")
            return removed_count
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0


# Global cache manager instance
_geojson_cache = GeoJSONCacheManager()

def get_geojson_cache() -> GeoJSONCacheManager:
    """Get the global GeoJSON cache manager instance"""
    return _geojson_cache
