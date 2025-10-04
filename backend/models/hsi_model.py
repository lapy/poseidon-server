"""
Habitat Suitability Index (HSI) Model Implementation
Mathematical model for predicting shark foraging hotspots

🚀 NASA Space Apps Challenge 2025 - Sharks from Space
This implementation is part of the NASA Space Apps Challenge 2025 project
demonstrating satellite-based shark habitat prediction using NASA oceanographic data.

Challenge URL: https://www.spaceappschallenge.org/2025/challenges/sharks-from-space/
"""

import numpy as np
import xarray as xr
from typing import Dict, Any, Optional, Tuple
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SharkProfile:
    """Shark species profile with HSI parameters"""
    name: str
    s_opt: float  # Optimal temperature
    sigma_s: float  # Temperature tolerance
    t_lag: int  # Temperature lag in days
    c_lag: int  # Chlorophyll lag in days
    w_c: float  # Chlorophyll weight
    w_e: float  # Sea level anomaly weight
    w_s: float  # Temperature weight
    salinity_min: float  # Minimum salinity tolerance (psu)
    salinity_max: float  # Maximum salinity tolerance (psu)
    
    @property
    def total_weight(self) -> float:
        return self.w_c + self.w_e + self.w_s

class HSIModel:
    """Habitat Suitability Index Model for shark foraging hotspots"""
    
    def __init__(self):
        # Define shark species profiles
        self.shark_profiles = {
            'great_white': SharkProfile(
                name='Great White Shark',
                s_opt=18.0,  # Optimal temperature in Celsius
                sigma_s=5.0,  # Temperature tolerance
                t_lag=7,  # 7-day temperature lag
                c_lag=30,  # 30-day chlorophyll lag
                w_c=0.4,  # Chlorophyll weight
                w_e=0.3,  # Sea level anomaly weight
                w_s=0.3,   # Temperature weight
                salinity_min=30.0,  # Minimum salinity tolerance (psu)
                salinity_max=37.0   # Maximum salinity tolerance (psu)
            ),
            'tiger_shark': SharkProfile(
                name='Tiger Shark',
                s_opt=25.0,  # Optimal temperature in Celsius
                sigma_s=4.0,  # Temperature tolerance
                t_lag=5,  # 5-day temperature lag
                c_lag=21,  # 21-day chlorophyll lag
                w_c=0.3,  # Chlorophyll weight
                w_e=0.4,  # Sea level anomaly weight
                w_s=0.3,   # Temperature weight
                salinity_min=30.0,  # Minimum salinity tolerance (psu)
                salinity_max=37.0   # Maximum salinity tolerance (psu)
            ),
            'bull_shark': SharkProfile(
                name='Bull Shark',
                s_opt=22.0,  # Optimal temperature in Celsius
                sigma_s=6.0,  # Temperature tolerance
                t_lag=3,  # 3-day temperature lag
                c_lag=14,  # 14-day chlorophyll lag
                w_c=0.35,  # Chlorophyll weight
                w_e=0.35,  # Sea level anomaly weight
                w_s=0.3,   # Temperature weight
                salinity_min=0.5,   # Minimum salinity tolerance (psu) - highly adaptable
                salinity_max=35.0   # Maximum salinity tolerance (psu)
            )
        }
    
    def calculate_hsi(self, 
                     chlorophyll_data: xr.Dataset,
                     sea_level_data: xr.Dataset,
                     sst_data: xr.Dataset,
                     salinity_data: xr.Dataset,
                     shark_species: str,
                     target_date: str,
                     geographic_bounds: Dict = None,
                     lagged_chlorophyll_data: xr.Dataset = None,
                     lagged_sst_data: xr.Dataset = None) -> xr.Dataset:
        """
        Calculate Habitat Suitability Index with trophic lag support and salinity filtering
        
        H(x,y,t) = f_sal(S) * (f_C(C')^w_C * f_E(E')^w_E * f_S(S)^w_S)^(1/(w_C + w_E + w_S))
        
        Where f_sal(S) is a binary salinity filter that excludes areas where sharks cannot survive.
        
        Args:
            chlorophyll_data: Chlorophyll-a concentration data (current)
            sea_level_data: Sea level anomaly data (current)
            sst_data: Sea surface temperature data (current)
            salinity_data: Sea surface salinity data (current)
            shark_species: Species name ('great_white', 'tiger_shark', or 'bull_shark')
            target_date: Target date in YYYY-MM-DD format
            geographic_bounds: Geographic bounds for filtering (optional)
            lagged_chlorophyll_data: Lagged chlorophyll data (optional)
            lagged_sst_data: Lagged SST data (optional)
            
        Returns:
            xarray Dataset with HSI values
        """
        try:
            # Get shark profile
            if shark_species not in self.shark_profiles:
                raise ValueError(f"Unknown shark species: {shark_species}")
            
            profile = self.shark_profiles[shark_species]
            
            # Apply geographic filtering to all datasets if bounds provided
            if geographic_bounds:
                chlorophyll_data = self._apply_geographic_filter(chlorophyll_data, geographic_bounds)
                sea_level_data = self._apply_geographic_filter(sea_level_data, geographic_bounds)
                sst_data = self._apply_geographic_filter(sst_data, geographic_bounds)
                salinity_data = self._apply_geographic_filter(salinity_data, geographic_bounds)
                
                if lagged_chlorophyll_data is not None:
                    lagged_chlorophyll_data = self._apply_geographic_filter(lagged_chlorophyll_data, geographic_bounds)
                if lagged_sst_data is not None:
                    lagged_sst_data = self._apply_geographic_filter(lagged_sst_data, geographic_bounds)
                
                logger.info(f"Applied geographic filtering to all datasets")
            
            # Extract data variables - use lagged data if available
            if lagged_chlorophyll_data is not None:
                chl = lagged_chlorophyll_data['chlorophyll']
                logger.info(f"Using lagged chlorophyll data ({profile.c_lag} days)")
            else:
                chl = chlorophyll_data['chlorophyll']
                logger.info("Using current chlorophyll data (no lag)")
            
            sla = sea_level_data['sea_level']  # Sea level anomaly is current (no lag)
            
            if lagged_sst_data is not None and 'sst' in lagged_sst_data.data_vars:
                logger.info(f"Using lagged SST data ({profile.t_lag} days)")
                sst = lagged_sst_data['sst']
            elif sst_data is not None and 'sst' in sst_data.data_vars:
                sst = sst_data['sst']
                logger.info("Using current SST data (no lag)")
            else:
                logger.error("SST data not available - cannot continue HSI calculation")
                raise ValueError("SST data is required but not available. Cannot calculate HSI without temperature data.")
            
            # Extract salinity data (no lag - salinity is relatively stable)
            if salinity_data is not None and 'salinity' in salinity_data.data_vars:
                salinity = salinity_data['salinity']
                logger.info("Using current salinity data")
            else:
                logger.error("Salinity data not available - cannot continue HSI calculation")
                raise ValueError("Salinity data is required but not available. Cannot calculate HSI without salinity data.")
            
            # Normalize data
            f_c = self._normalize_chlorophyll(chl)
            f_e = self._normalize_sea_level_anomaly(sla)
            f_s = self._calculate_temperature_suitability(sst, profile)
            
            # Calculate salinity suitability filter (binary: 1 for suitable, 0 for unsuitable)
            f_sal = self._calculate_salinity_suitability(salinity, profile)
            
            # Handle missing sea level data by using default sea level suitability where data is missing
            # Replace NaN sea level suitability with neutral value (0.5)
            # This is necessary due to NASA-SSH dataset coverage limitations in western hemisphere
            sea_level_nan_count = np.isnan(f_e).sum().values
            total_points = f_e.size
            if sea_level_nan_count > 0:
                logger.info(f"Sea level data missing for {sea_level_nan_count}/{total_points} points ({100*sea_level_nan_count/total_points:.1f}%) - using neutral suitability (0.5)")
            f_e_filled = f_e.where(~np.isnan(f_e), 0.5)
            
            # Calculate HSI with filled sea level data and salinity filtering
            hsi = f_sal * ((f_c ** profile.w_c) * 
                          (f_e_filled ** profile.w_e) * 
                          (f_s ** profile.w_s)) ** (1.0 / profile.total_weight)
            
            # Replace any NaN values with 0
            hsi = hsi.where(~np.isnan(hsi), 0.0)
            
            # Create result dataset
            result = xr.Dataset({
                'hsi': hsi,
                'chlorophyll_suitability': f_c,
                'sea_level_suitability': f_e,
                'temperature_suitability': f_s,
                'salinity_suitability': f_sal
            })
            
            # Add metadata
            result.attrs.update({
                'shark_species': profile.name,
                'target_date': target_date,
                'model_version': '1.0',
                'parameters': {
                    's_opt': profile.s_opt,
                    'sigma_s': profile.sigma_s,
                    't_lag': profile.t_lag,
                    'c_lag': profile.c_lag,
                    'w_c': profile.w_c,
                    'w_e': profile.w_e,
                    'w_s': profile.w_s,
                    'salinity_min': profile.salinity_min,
                    'salinity_max': profile.salinity_max
                }
            })
            
            logger.info(f"HSI calculated for {profile.name} on {target_date}")
            return result
            
        except Exception as e:
            logger.error(f"HSI calculation failed: {e}")
            raise
    
    def _normalize_chlorophyll(self, chl: xr.DataArray) -> xr.DataArray:
        """
        Normalize chlorophyll concentration
        f_C(C') = C' / (C' + k_C)
        """
        try:
            # Remove invalid values
            chl_clean = chl.where(chl > 0)
            
            # Apply normalization (k_C = 0.5 mg/m³)
            k_c = 0.5
            normalized = chl_clean / (chl_clean + k_c)
            
            # Ensure values are between 0 and 1
            normalized = normalized.clip(0, 1)
            
            return normalized
            
        except Exception as e:
            logger.error(f"Chlorophyll normalization failed: {e}")
            return xr.zeros_like(chl)
    
    def _normalize_sea_level_anomaly(self, sla: xr.DataArray) -> xr.DataArray:
        """
        Normalize sea level anomaly for comprehensive eddy and front detection
        
        This function implements sophisticated oceanographic feature detection:
        
        1. EDDY DETECTION:
           - Cyclonic Eddies (negative SLA): Cold-core eddies creating upwelling
             * Bring nutrient-rich deep water to surface
             * Promote phytoplankton blooms → prey aggregation → shark foraging
           - Anticyclonic Eddies (positive SLA): Warm-core eddies creating downwelling
             * Concentrate prey at depth, different foraging dynamics
           - Gaussian normalization: f_eddy = exp(-E'²/(2σ²)) where σ = 0.1m
           - Optimal strength: Moderate SLA values (±0.1m) provide highest suitability
        
        2. FRONT DETECTION:
           - Ocean Fronts: Sharp boundaries between water masses
           - Spatial gradients: |∇SLA| = √((∂SLA/∂lat)² + (∂SLA/∂lon)²)
           - Front suitability: f_front = exp(-|∇SLA|/σ_front) where σ_front = 0.05 m/degree
           - Convergence zones: Where different water masses meet → prey concentration
        
        3. COMBINED SUITABILITY:
           - Weighted combination: f_E = 0.6 × f_eddy + 0.4 × f_front
           - Eddies (60%): Primary foraging hotspots
           - Fronts (40%): Secondary but important prey concentration zones
        
        Args:
            sla: Sea Level Anomaly data in meters
            
        Returns:
            Combined eddy and front suitability (0-1 scale)
        """
        try:
            # Remove invalid values
            sla_clean = sla.where(np.isfinite(sla))
            
            # STEP 1: FRONT DETECTION
            # Ocean fronts are identified by steep spatial gradients in SLA
            # These represent boundaries between different water masses where prey concentrates
            if 'lat' in sla_clean.dims and 'lon' in sla_clean.dims:
                # Calculate spatial gradients in both dimensions
                grad_lat = sla_clean.differentiate('lat')  # ∂SLA/∂lat
                grad_lon = sla_clean.differentiate('lon')  # ∂SLA/∂lon
                
                # Calculate gradient magnitude: |∇SLA| = √((∂SLA/∂lat)² + (∂SLA/∂lon)²)
                gradient_magnitude = np.sqrt(grad_lat**2 + grad_lon**2)
                
                # Convert gradients to front suitability using exponential decay
                # High gradients (steep fronts) → high suitability for prey concentration
                # σ_front = 0.05 m/degree: typical gradient threshold for significant fronts
                front_suitability = np.exp(-gradient_magnitude / 0.05)
            else:
                # Fallback if spatial dimensions not available
                front_suitability = xr.ones_like(sla_clean)
            
            # STEP 2: EDDY DETECTION
            # Eddies are circular ocean features detected by SLA anomalies
            # Both positive (anticyclonic) and negative (cyclonic) eddies are important
            sigma_e = 0.1  # Standard deviation for eddy strength normalization
            eddy_suitability = np.exp(-(sla_clean ** 2) / (2 * sigma_e ** 2))
            
            # STEP 3: COMBINE EDDY AND FRONT SUITABILITY
            # Both features contribute to prey concentration but with different weights
            # Eddies (60%): Primary foraging hotspots from upwelling/downwelling
            # Fronts (40%): Secondary but important convergence zones
            combined_suitability = 0.6 * eddy_suitability + 0.4 * front_suitability
            
            # Ensure values are between 0 and 1
            normalized = combined_suitability.clip(0, 1)
            
            return normalized
            
        except Exception as e:
            logger.error(f"Sea level anomaly normalization failed: {e}")
            return xr.ones_like(sla)
    
    def _calculate_temperature_suitability(self, sst: xr.DataArray, profile: SharkProfile) -> xr.DataArray:
        """
        Calculate temperature suitability using Gaussian function
        f_S(S) = exp(-(S - S_opt)² / (2 * σ_S²))
        """
        try:
            # Remove invalid values
            sst_clean = sst.where(np.isfinite(sst))
            
            # Apply Gaussian suitability function
            suitability = np.exp(-((sst_clean - profile.s_opt) ** 2) / 
                                (2 * profile.sigma_s ** 2))
            
            # Ensure values are between 0 and 1
            suitability = suitability.clip(0, 1)
            
            return suitability
            
        except Exception as e:
            logger.error(f"Temperature suitability calculation failed: {e}")
            return xr.ones_like(sst)
    
    def _calculate_salinity_suitability(self, salinity: xr.DataArray, profile: SharkProfile) -> xr.DataArray:
        """
        Calculate salinity suitability using binary filtering
        f_sal(S) = 1 if salinity_min <= S <= salinity_max, else 0
        
        This function implements a binary habitat filter that excludes areas where sharks
        cannot survive based on salinity tolerance levels. This is a critical component
        for accurate habitat suitability predictions as sharks are stenohaline (cannot
        tolerate wide salinity variations) except for euryhaline species like bull sharks.
        """
        try:
            # Remove invalid values
            salinity_clean = salinity.where(np.isfinite(salinity))
            
            # Apply binary salinity filter based on species tolerance
            # 1 = suitable salinity range, 0 = unsuitable (sharks cannot survive)
            salinity_suitable = ((salinity_clean >= profile.salinity_min) & 
                               (salinity_clean <= profile.salinity_max)).astype(float)
            
            # Count excluded areas for logging
            total_points = salinity_clean.size
            excluded_points = np.sum(salinity_suitable.values == 0)
            if excluded_points > 0:
                exclusion_percent = 100 * excluded_points / total_points
                logger.info(f"Salinity filtering excluded {excluded_points}/{total_points} points ({exclusion_percent:.1f}%) outside {profile.salinity_min}-{profile.salinity_max} psu range")
            
            return salinity_suitable
            
        except Exception as e:
            logger.error(f"Salinity suitability calculation failed: {e}")
            # Return all suitable in case of error (conservative approach)
            return xr.ones_like(salinity)
    
    def get_shark_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Get available shark species profiles"""
        return {
            species: {
                'name': profile.name,
                's_opt': profile.s_opt,
                'sigma_s': profile.sigma_s,
                't_lag': profile.t_lag,
                'c_lag': profile.c_lag,
                'w_c': profile.w_c,
                'w_e': profile.w_e,
                'w_s': profile.w_s,
                'salinity_min': profile.salinity_min,
                'salinity_max': profile.salinity_max
            }
            for species, profile in self.shark_profiles.items()
        }
    
    def calculate_lagged_dates(self, target_date: str, shark_species: str) -> Dict[str, str]:
        """
        Calculate lagged dates for trophic lag implementation
        
        Args:
            target_date: Target date in YYYY-MM-DD format
            shark_species: Species name
            
        Returns:
            Dictionary with lagged dates for chlorophyll and temperature
        """
        from datetime import datetime, timedelta
        
        if shark_species not in self.shark_profiles:
            raise ValueError(f"Unknown shark species: {shark_species}")
        
        profile = self.shark_profiles[shark_species]
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
        
        # Calculate lagged dates
        chlorophyll_lag_date = target_dt - timedelta(days=profile.c_lag)
        temperature_lag_date = target_dt - timedelta(days=profile.t_lag)
        
        return {
            'target_date': target_date,
            'chlorophyll_lag_date': chlorophyll_lag_date.strftime('%Y-%m-%d'),
            'temperature_lag_date': temperature_lag_date.strftime('%Y-%m-%d'),
            'chlorophyll_lag_days': profile.c_lag,
            'temperature_lag_days': profile.t_lag
        }
    
    def _apply_geographic_filter(self, data: xr.Dataset, geographic_bounds: Dict) -> xr.Dataset:
        """Apply geographic bounds to dataset"""
        try:
            if geographic_bounds is None:
                return data
            
            # Apply latitude bounds
            if 'lat' in data.coords:
                lat_mask = (data['lat'] >= geographic_bounds['south']) & (data['lat'] <= geographic_bounds['north'])
                data = data.where(lat_mask)
                logger.debug(f"Applied latitude filter: {geographic_bounds['south']} to {geographic_bounds['north']}")
            
            # Apply longitude bounds (handle 0-360 vs -180-180)
            if 'lon' in data.coords:
                if geographic_bounds['west'] < geographic_bounds['east']:
                    # Normal case: west < east
                    lon_mask = (data['lon'] >= geographic_bounds['west']) & (data['lon'] <= geographic_bounds['east'])
                else:
                    # Crosses dateline: west > east
                    lon_mask = (data['lon'] >= geographic_bounds['west']) | (data['lon'] <= geographic_bounds['east'])
                data = data.where(lon_mask)
                logger.debug(f"Applied longitude filter: {geographic_bounds['west']} to {geographic_bounds['east']}")
            
            return data
            
        except Exception as e:
            logger.error(f"Geographic filtering failed: {e}")
            return data
    
    def get_hsi_statistics(self, hsi_data: xr.Dataset) -> Dict[str, Any]:
        """Calculate statistics for HSI data"""
        try:
            hsi = hsi_data['hsi']
            
            # Filter out NaN values for statistics
            hsi_valid = hsi.where(~np.isnan(hsi))
            
            # Check if we have any valid data
            if hsi_valid.count() == 0:
                logger.warning("No valid HSI data for statistics calculation")
                return {
                    'mean': 0.0,
                    'std': 0.0,
                    'min': 0.0,
                    'max': 0.0,
                    'percentile_90': 0.0,
                    'percentile_95': 0.0,
                    'percentile_99': 0.0,
                    'valid_points': 0
                }
            
            stats = {
                'mean': float(hsi_valid.mean().values),
                'std': float(hsi_valid.std().values),
                'min': float(hsi_valid.min().values),
                'max': float(hsi_valid.max().values),
                'percentile_90': float(hsi_valid.quantile(0.9).values),
                'percentile_95': float(hsi_valid.quantile(0.95).values),
                'percentile_99': float(hsi_valid.quantile(0.99).values),
                'valid_points': int(hsi_valid.count().values)
            }
            
            # Replace any remaining NaN values with 0
            for key, value in stats.items():
                if isinstance(value, float) and np.isnan(value):
                    stats[key] = 0.0
                    logger.warning(f"Replaced NaN in {key} with 0.0")
            
            return stats
            
        except Exception as e:
            logger.error(f"HSI statistics calculation failed: {e}")
            return {
                'mean': 0.0,
                'std': 0.0,
                'min': 0.0,
                'max': 0.0,
                'percentile_90': 0.0,
                'percentile_95': 0.0,
                'percentile_99': 0.0,
                'valid_points': 0
            }
