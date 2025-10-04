"""
Habitat Suitability Index (HSI) Model Implementation
Mathematical model for predicting shark foraging hotspots
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
                w_s=0.3   # Temperature weight
            ),
            'tiger_shark': SharkProfile(
                name='Tiger Shark',
                s_opt=25.0,  # Optimal temperature in Celsius
                sigma_s=4.0,  # Temperature tolerance
                t_lag=5,  # 5-day temperature lag
                c_lag=21,  # 21-day chlorophyll lag
                w_c=0.3,  # Chlorophyll weight
                w_e=0.4,  # Sea level anomaly weight
                w_s=0.3   # Temperature weight
            )
        }
    
    def calculate_hsi(self, 
                     chlorophyll_data: xr.Dataset,
                     sea_level_data: xr.Dataset,
                     sst_data: xr.Dataset,
                     shark_species: str,
                     target_date: str,
                     lagged_chlorophyll_data: xr.Dataset = None,
                     lagged_sst_data: xr.Dataset = None) -> xr.Dataset:
        """
        Calculate Habitat Suitability Index with trophic lag support
        
        H(x,y,t) = (f_C(C')^w_C * f_E(E')^w_E * f_S(S)^w_S)^(1/(w_C + w_E + w_S))
        
        Args:
            chlorophyll_data: Chlorophyll-a concentration data (current)
            sea_level_data: Sea level anomaly data (current)
            sst_data: Sea surface temperature data (current)
            shark_species: Species name ('great_white' or 'tiger_shark')
            target_date: Target date in YYYY-MM-DD format
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
            
            # Extract data variables - use lagged data if available
            if lagged_chlorophyll_data is not None:
                chl = lagged_chlorophyll_data['chlorophyll']
                logger.info(f"Using lagged chlorophyll data ({profile.c_lag} days)")
            else:
                chl = chlorophyll_data['chlorophyll']
                logger.info("Using current chlorophyll data (no lag)")
            
            sla = sea_level_data['sea_level']  # Sea level anomaly is current (no lag)
            
            if lagged_sst_data is not None:
                sst = lagged_sst_data['sst']
                logger.info(f"Using lagged SST data ({profile.t_lag} days)")
            else:
                sst = sst_data['sst']
                logger.info("Using current SST data (no lag)")
            
            # Normalize data
            f_c = self._normalize_chlorophyll(chl)
            f_e = self._normalize_sea_level_anomaly(sla)
            f_s = self._calculate_temperature_suitability(sst, profile)
            
            # Calculate HSI
            hsi = ((f_c ** profile.w_c) * 
                   (f_e ** profile.w_e) * 
                   (f_s ** profile.w_s)) ** (1.0 / profile.total_weight)
            
            # Create result dataset
            result = xr.Dataset({
                'hsi': hsi,
                'chlorophyll_suitability': f_c,
                'sea_level_suitability': f_e,
                'temperature_suitability': f_s
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
                    'w_s': profile.w_s
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
        Normalize sea level anomaly for eddy and front detection
        f_E(E') = exp(-E'² / (2 * σ_E²))
        
        Large positive SLA values (hills) represent warm-core, anticyclonic eddies
        Large negative SLA values (valleys) represent cold-core, cyclonic eddies
        Steep gradients indicate ocean fronts
        """
        try:
            # Remove invalid values
            sla_clean = sla.where(np.isfinite(sla))
            
            # Calculate gradient magnitude for front detection
            # Fronts are areas with steep gradients in SLA
            if 'lat' in sla_clean.dims and 'lon' in sla_clean.dims:
                # Calculate spatial gradients
                grad_lat = sla_clean.differentiate('lat')
                grad_lon = sla_clean.differentiate('lon')
                gradient_magnitude = np.sqrt(grad_lat**2 + grad_lon**2)
                
                # Normalize gradient magnitude (fronts have high gradients)
                front_suitability = np.exp(-gradient_magnitude / 0.05)  # σ_front = 0.05 m/degree
            else:
                front_suitability = xr.ones_like(sla_clean)
            
            # Apply Gaussian normalization for eddy detection (σ_E = 0.1 m)
            # This captures both warm-core (positive) and cold-core (negative) eddies
            sigma_e = 0.1
            eddy_suitability = np.exp(-(sla_clean ** 2) / (2 * sigma_e ** 2))
            
            # Combine eddy and front suitability
            # Eddies and fronts are both important for prey concentration
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
                'w_s': profile.w_s
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
    
    def get_hsi_statistics(self, hsi_data: xr.Dataset) -> Dict[str, Any]:
        """Calculate statistics for HSI data"""
        try:
            hsi = hsi_data['hsi']
            
            stats = {
                'mean': float(hsi.mean().values),
                'std': float(hsi.std().values),
                'min': float(hsi.min().values),
                'max': float(hsi.max().values),
                'percentile_90': float(hsi.quantile(0.9).values),
                'percentile_95': float(hsi.quantile(0.95).values),
                'percentile_99': float(hsi.quantile(0.99).values)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"HSI statistics calculation failed: {e}")
            return {}
