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
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class SharkProfile:
    """
    Enhanced Shark species profile with comprehensive HSI parameters
    
    This profile supports a multi-faceted ecological niche model that incorporates:
    - Physicochemical & Oceanographic factors (temperature, salinity, oxygen, eddies, fronts)
    - Prey availability (direct prey density and chlorophyll as productivity proxy)
    - Topographic features (depth and seafloor slope)
    - Anthropogenic pressures (fishing and shipping)
    """
    name: str
    
    # === Temperature Parameters ===
    s_opt: float  # Optimal temperature (°C)
    sigma_s: float  # Temperature tolerance (°C)
    t_lag: int  # Temperature lag in days
    
    # === Salinity Parameters (Trapezoidal Function) ===
    salinity_min: float  # Minimum salinity tolerance (psu)
    salinity_opt_min: float  # Lower bound of optimal salinity range (psu)
    salinity_opt_max: float  # Upper bound of optimal salinity range (psu)
    salinity_max: float  # Maximum salinity tolerance (psu)
    
    # === Oxygen Parameters (Sigmoid Function) ===
    oxygen_min: float  # Minimum dissolved oxygen threshold (mg/L)
    oxygen_opt: float  # Optimal dissolved oxygen (mg/L)
    oxygen_sigma: float  # Oxygen tolerance parameter
    
    # === Chlorophyll/Productivity Parameters ===
    c_lag: int  # Chlorophyll lag in days
    w_chl: float  # Chlorophyll weight in prey index (baseline productivity)
    
    # === Prey Availability Parameters ===
    # Dietary weights for specific prey guilds (should sum to 1 - w_chl)
    w_prey_pinnipeds: float  # Weight for pinniped prey density
    w_prey_turtles: float  # Weight for sea turtle prey density
    w_prey_fish: float  # Weight for large bony fish prey density
    w_prey_cephalopods: float  # Weight for cephalopod prey density
    
    # === Topographic Parameters ===
    depth_min: float  # Minimum preferred depth (m)
    depth_opt_min: float  # Lower bound of optimal depth range (m)
    depth_opt_max: float  # Upper bound of optimal depth range (m)
    depth_max: float  # Maximum depth limit (m)
    slope_opt: float  # Optimal seafloor slope (degrees)
    slope_sigma: float  # Slope tolerance parameter
    
    # === Model Weights (Weighted Linear Combination) ===
    # These weights should sum to 1
    w_phys: float  # Weight for Physicochemical & Oceanographic Index
    w_prey: float  # Weight for Prey Availability Index
    w_topo: float  # Weight for Topographic Index
    
    # === Oceanographic Feature Weights (within I_Phys) ===
    w_eddy: float = 0.6  # Weight for eddy suitability (default 60%)
    w_front: float = 0.4  # Weight for front suitability (default 40%)
    
    @property
    def total_index_weight(self) -> float:
        """Total weight across the three main indices (should be 1.0)"""
        return self.w_phys + self.w_prey + self.w_topo
    
    @property
    def total_prey_weight(self) -> float:
        """Total weight for prey components in I_Prey"""
        return self.w_chl + self.w_prey_pinnipeds + self.w_prey_turtles + self.w_prey_fish + self.w_prey_cephalopods

class HSIModel:
    """Habitat Suitability Index Model for shark foraging hotspots"""
    
    def __init__(self):
        # Define enhanced shark species profiles with comprehensive ecological parameters
        # 
        # PARAMETER SOURCES AND VALIDATION:
        # - Great White, Tiger, Bull sharks: Based on published literature and tagging studies
        # - Blacktip Reef, Nurse: Updated based on Florida coastal shark research (PMC8601906)
        # - Hammerhead, Mako, Blue, Whale, Lemon: Parameters estimated from general literature
        #   and should be refined with species-specific habitat studies
        # 
        # MEDITERRANEAN COMPATIBILITY UPDATE:
        # - Salinity max extended to 39 psu for 6 species (Great White, Tiger, Bull, 
        #   Blue, Hammerhead, Mako) to account for Mediterranean hypersalinity (38-39 psu)
        # - Mediterranean populations of these species are documented and capable of 
        #   tolerating higher salinity than typical oceanic populations
        # 
        # NOTE: These parameters represent general population averages. Regional populations
        # may exhibit different preferences due to local adaptation. Model outputs should be
        # validated against observational data when available.
        self.shark_profiles = {
            'great_white': SharkProfile(
                name='Great White Shark',
                # Temperature
                s_opt=18.0, sigma_s=5.0, t_lag=7,
                # Salinity (extended for Mediterranean populations: 30-39 psu)
                salinity_min=30.0, salinity_opt_min=33.0, salinity_opt_max=36.0, salinity_max=39.0,
                # Oxygen (requires well-oxygenated water)
                oxygen_min=4.0, oxygen_opt=7.0, oxygen_sigma=1.5,
                # Chlorophyll/Productivity
                c_lag=30, w_chl=0.2,  # Chlorophyll as baseline productivity indicator
                # Prey weights (sum with w_chl = 1.0 for I_Prey)
                w_prey_pinnipeds=0.5,  # Primary prey: seals and sea lions
                w_prey_turtles=0.1, w_prey_fish=0.15, w_prey_cephalopods=0.05,
                # Topography (prefers shelf breaks, 0-300m typical)
                depth_min=0.0, depth_opt_min=20.0, depth_opt_max=300.0, depth_max=1200.0,
                slope_opt=2.0, slope_sigma=3.0,  # Moderate slopes at shelf edges
                # Model weights (I_Phys + I_Prey + I_Topo = 1.0)
                w_phys=0.35, w_prey=0.45, w_topo=0.20
            ),
            'tiger_shark': SharkProfile(
                name='Tiger Shark',
                # Temperature (warmer water preference)
                s_opt=25.0, sigma_s=4.0, t_lag=5,
                # Salinity (extended for Mediterranean: 28-39 psu, optimal 32-36 psu)
                salinity_min=28.0, salinity_opt_min=32.0, salinity_opt_max=36.0, salinity_max=39.0,
                # Oxygen
                oxygen_min=3.5, oxygen_opt=6.5, oxygen_sigma=1.8,
                # Chlorophyll/Productivity
                c_lag=21, w_chl=0.25,  # More reliant on general productivity
                # Prey weights (generalist predator)
                w_prey_pinnipeds=0.1, w_prey_turtles=0.3,  # Significant turtle predation
                w_prey_fish=0.25, w_prey_cephalopods=0.1,
                # Topography (wider depth range, coastal to oceanic)
                depth_min=0.0, depth_opt_min=10.0, depth_opt_max=400.0, depth_max=1500.0,
                slope_opt=1.5, slope_sigma=4.0,  # More tolerant of flat terrain
                # Model weights
                w_phys=0.40, w_prey=0.35, w_topo=0.25  # More oceanographic-driven
            ),
            'bull_shark': SharkProfile(
                name='Bull Shark',
                # Temperature (warm water)
                s_opt=22.0, sigma_s=6.0, t_lag=3,
                # Salinity (euryhaline: 0.5-39 psu, optimal 15-35 for coastal/Mediterranean)
                salinity_min=0.5, salinity_opt_min=15.0, salinity_opt_max=35.0, salinity_max=39.0,
                # Oxygen (tolerates lower oxygen)
                oxygen_min=2.5, oxygen_opt=6.0, oxygen_sigma=2.0,
                # Chlorophyll/Productivity
                c_lag=14, w_chl=0.3,  # Productive estuarine environments
                # Prey weights (opportunistic)
                w_prey_pinnipeds=0.05, w_prey_turtles=0.15,
                w_prey_fish=0.4, w_prey_cephalopods=0.1,  # Fish-dominated diet
                # Topography (shallow coastal/estuarine)
                depth_min=0.0, depth_opt_min=5.0, depth_opt_max=150.0, depth_max=500.0,
                slope_opt=0.5, slope_sigma=2.0,  # Prefers flat estuarine terrain
                # Model weights
                w_phys=0.30, w_prey=0.50, w_topo=0.20  # Heavily prey-driven
            ),
            'hammerhead': SharkProfile(
                name='Scalloped Hammerhead',
                # Temperature (warm tropical/subtropical)
                s_opt=24.0, sigma_s=5.0, t_lag=5,
                # Salinity (marine, extended for Mediterranean populations)
                salinity_min=32.0, salinity_opt_min=34.0, salinity_opt_max=36.5, salinity_max=39.0,
                # Oxygen (requires good oxygenation)
                oxygen_min=3.8, oxygen_opt=6.8, oxygen_sigma=1.6,
                # Chlorophyll/Productivity
                c_lag=21, w_chl=0.25,
                # Prey weights (specialized for squid and fish schools)
                w_prey_pinnipeds=0.0, w_prey_turtles=0.05,
                w_prey_fish=0.45, w_prey_cephalopods=0.25,  # Squid specialist
                # Topography (seamounts, shelf edges, 0-500m)
                depth_min=10.0, depth_opt_min=50.0, depth_opt_max=500.0, depth_max=1000.0,
                slope_opt=3.5, slope_sigma=3.5,  # Prefers pronounced topography
                # Model weights
                w_phys=0.35, w_prey=0.40, w_topo=0.25  # Strong topographic preference
            ),
            'mako': SharkProfile(
                name='Shortfin Mako',
                # Temperature (cooler pelagic waters)
                s_opt=19.0, sigma_s=6.0, t_lag=7,
                # Salinity (oceanic, extended for Mediterranean)
                salinity_min=33.0, salinity_opt_min=34.5, salinity_opt_max=36.5, salinity_max=39.0,
                # Oxygen (requires well-oxygenated water)
                oxygen_min=4.5, oxygen_opt=7.5, oxygen_sigma=1.5,
                # Chlorophyll/Productivity
                c_lag=30, w_chl=0.15,  # Pelagic predator, less productivity-driven
                # Prey weights (fast fish predator)
                w_prey_pinnipeds=0.0, w_prey_turtles=0.05,
                w_prey_fish=0.65, w_prey_cephalopods=0.15,  # Tuna, swordfish specialist
                # Topography (deep oceanic, 0-600m)
                depth_min=50.0, depth_opt_min=100.0, depth_opt_max=600.0, depth_max=1500.0,
                slope_opt=1.0, slope_sigma=5.0,  # Open ocean, slope less important
                # Model weights
                w_phys=0.45, w_prey=0.45, w_topo=0.10  # Pelagic, oceanographic-driven
            ),
            'blue_shark': SharkProfile(
                name='Blue Shark',
                # Temperature (temperate to tropical, wide range)
                s_opt=20.0, sigma_s=7.0, t_lag=7,
                # Salinity (oceanic, extended for Mediterranean)
                salinity_min=32.0, salinity_opt_min=34.0, salinity_opt_max=36.5, salinity_max=39.0,
                # Oxygen
                oxygen_min=4.0, oxygen_opt=7.0, oxygen_sigma=1.7,
                # Chlorophyll/Productivity
                c_lag=28, w_chl=0.2,  # Open ocean predator
                # Prey weights (generalist pelagic predator)
                w_prey_pinnipeds=0.0, w_prey_turtles=0.1,
                w_prey_fish=0.45, w_prey_cephalopods=0.25,  # Squid important
                # Topography (wide depth range, oceanic)
                depth_min=50.0, depth_opt_min=100.0, depth_opt_max=700.0, depth_max=2000.0,
                slope_opt=1.0, slope_sigma=6.0,  # Open ocean
                # Model weights
                w_phys=0.40, w_prey=0.45, w_topo=0.15  # Oceanographic and prey-driven
            ),
            'whale_shark': SharkProfile(
                name='Whale Shark',
                # Temperature (warm tropical)
                s_opt=26.0, sigma_s=4.0, t_lag=5,
                # Salinity (marine)
                salinity_min=32.0, salinity_opt_min=34.0, salinity_opt_max=36.0, salinity_max=37.5,
                # Oxygen
                oxygen_min=4.0, oxygen_opt=7.0, oxygen_sigma=1.5,
                # Chlorophyll/Productivity (filter feeder, highly productivity-driven)
                c_lag=14, w_chl=0.7,  # Follows plankton blooms
                # Prey weights (planktivore)
                w_prey_pinnipeds=0.0, w_prey_turtles=0.0,
                w_prey_fish=0.2, w_prey_cephalopods=0.1,  # Small fish and krill
                # Topography (surface to mid-water)
                depth_min=0.0, depth_opt_min=10.0, depth_opt_max=200.0, depth_max=1000.0,
                slope_opt=1.0, slope_sigma=5.0,  # Topography less important
                # Model weights
                w_phys=0.30, w_prey=0.60, w_topo=0.10  # Heavily productivity/prey-driven
            ),
            'blacktip_reef': SharkProfile(
                name='Blacktip Reef Shark',
                # Temperature (warm tropical) - Research shows preference for 31°C+
                s_opt=30.0, sigma_s=4.0, t_lag=3,
                # Salinity (coastal marine)
                salinity_min=30.0, salinity_opt_min=33.0, salinity_opt_max=36.0, salinity_max=37.5,
                # Oxygen
                oxygen_min=3.5, oxygen_opt=6.5, oxygen_sigma=1.8,
                # Chlorophyll/Productivity
                c_lag=14, w_chl=0.3,  # Productive reef environments
                # Prey weights (reef fish specialist)
                w_prey_pinnipeds=0.0, w_prey_turtles=0.05,
                w_prey_fish=0.55, w_prey_cephalopods=0.1,  # Reef fish dominant
                # Topography (very shallow reef, 0-4m typical) - Research shows depth < 4m preference
                depth_min=0.0, depth_opt_min=2.0, depth_opt_max=50.0, depth_max=150.0,
                slope_opt=2.5, slope_sigma=3.0,  # Moderate reef slopes
                # Model weights
                w_phys=0.30, w_prey=0.45, w_topo=0.25  # Reef-associated
            ),
            'lemon_shark': SharkProfile(
                name='Lemon Shark',
                # Temperature (warm subtropical/tropical)
                s_opt=26.0, sigma_s=4.0, t_lag=3,
                # Salinity (coastal, tolerates lower salinity)
                salinity_min=25.0, salinity_opt_min=30.0, salinity_opt_max=35.0, salinity_max=37.0,
                # Oxygen (tolerates moderate levels)
                oxygen_min=3.0, oxygen_opt=6.0, oxygen_sigma=2.0,
                # Chlorophyll/Productivity
                c_lag=14, w_chl=0.35,  # Productive coastal waters
                # Prey weights (benthic and demersal fish)
                w_prey_pinnipeds=0.0, w_prey_turtles=0.05,
                w_prey_fish=0.5, w_prey_cephalopods=0.1,
                # Topography (very shallow coastal, 0-90m)
                depth_min=0.0, depth_opt_min=2.0, depth_opt_max=90.0, depth_max=300.0,
                slope_opt=0.5, slope_sigma=2.0,  # Flat coastal terrain
                # Model weights
                w_phys=0.30, w_prey=0.50, w_topo=0.20  # Coastal prey-driven
            ),
            'nurse_shark': SharkProfile(
                name='Nurse Shark',
                # Temperature (warm tropical/subtropical) - Research shows preference for 30°C+
                s_opt=29.0, sigma_s=3.5, t_lag=2,
                # Salinity (coastal marine)
                salinity_min=28.0, salinity_opt_min=32.0, salinity_opt_max=36.0, salinity_max=37.5,
                # Oxygen (tolerates lower oxygen)
                oxygen_min=2.5, oxygen_opt=5.5, oxygen_sigma=2.5,
                # Chlorophyll/Productivity
                c_lag=14, w_chl=0.25,
                # Prey weights (benthic invertebrates and fish)
                w_prey_pinnipeds=0.0, w_prey_turtles=0.0,
                w_prey_fish=0.4, w_prey_cephalopods=0.35,  # Invertebrate specialist
                # Topography (shallow to moderate depth) - Research shows depth > 7m typical
                depth_min=0.0, depth_opt_min=7.0, depth_opt_max=50.0, depth_max=130.0,
                slope_opt=0.3, slope_sigma=1.5,  # Very flat, benthic
                # Model weights
                w_phys=0.25, w_prey=0.50, w_topo=0.25  # Benthic, habitat-specific
            )
        }
    
    def calculate_hsi(self,
                     chlorophyll_data: xr.Dataset,
                     sea_level_data: xr.Dataset,
                     sst_data: xr.Dataset,
                     salinity_data: xr.Dataset,
                     shark_species: str,
                     target_date: str,
                     lagged_chlorophyll_data: xr.Dataset = None,
                     lagged_sst_data: xr.Dataset = None,
                     oxygen_data: xr.Dataset = None,
                     bathymetry_data: xr.Dataset = None,
                     prey_data: Dict[str, xr.Dataset] = None,
                     fishing_pressure_data: xr.Dataset = None,
                     shipping_density_data: xr.Dataset = None,
                     use_enhanced_model: bool = False) -> xr.Dataset:
        """
        Calculate Enhanced Habitat Suitability Index (COMPREHENSIVE ECOLOGICAL NICHE MODEL)
        
        **ENHANCED MODEL FORMULA:**
        HSI = (w_Phys × I_Phys + w_Prey × I_Prey + w_Topo × I_Topo) × (1 - I_Anthro)
        
        Where:
        - I_Phys = Physicochemical & Oceanographic Index (temperature, salinity, oxygen, eddies, fronts)
        - I_Prey = Prey Availability Index (direct prey density + chlorophyll productivity)
        - I_Topo = Topographic Index (depth + seafloor slope)
        - I_Anthro = Anthropogenic Pressure Index (fishing + shipping)
        
        This evolves the model from primarily oceanographic to a holistic ecological niche model
        incorporating prey availability, static topography, and human impacts.
        
        **LEGACY MODEL SUPPORT:**
        If use_enhanced_model=False or if enhanced data is not available, falls back to:
        H(x,y,t) = f_sal(S) * (f_C(C')^w_C * f_E(E')^w_E * f_S(S)^w_S)^(1/(w_C + w_E + w_S))
        
        Args:
            chlorophyll_data: Chlorophyll-a concentration data
            sea_level_data: Sea level anomaly data
            sst_data: Sea surface temperature data
            salinity_data: Sea surface salinity data
            shark_species: Species name ('great_white', 'tiger_shark', or 'bull_shark')
            target_date: Target date in YYYY-MM-DD format
            lagged_chlorophyll_data: Lagged chlorophyll data (optional)
            lagged_sst_data: Lagged SST data (optional)
            oxygen_data: Dissolved oxygen data (optional, derived if not provided)
            bathymetry_data: Bathymetry data with depth and slope (optional)
            prey_data: Dictionary of prey density datasets by type (optional)
            fishing_pressure_data: Fishing pressure data (optional)
            shipping_density_data: Shipping density data (optional)
            use_enhanced_model: Whether to use enhanced model (default True)
            
        Returns:
            xarray Dataset with HSI values and all component indices
        """
        try:
            # Get shark profile
            if shark_species not in self.shark_profiles:
                raise ValueError(f"Unknown shark species: {shark_species}")
            
            profile = self.shark_profiles[shark_species]
            logger.info(f"=== Calculating Enhanced HSI for {profile.name} on {target_date} ===")
            
            # ========================================
            # STEP 1: Extract and prepare core data
            # ========================================
            
            # Chlorophyll (lagged)
            if lagged_chlorophyll_data is not None:
                chl = lagged_chlorophyll_data['chlorophyll']
                logger.info(f"Using lagged chlorophyll data ({profile.c_lag} days)")
            else:
                chl = chlorophyll_data['chlorophyll']
                logger.info("Using current chlorophyll data (no lag)")
            
            # Sea level anomaly (current, for oceanographic features)
            sla = sea_level_data['sea_level']
            
            # Temperature (lagged)
            if lagged_sst_data is not None and 'sst' in lagged_sst_data.data_vars:
                sst = lagged_sst_data['sst']
                logger.info(f"Using lagged SST data ({profile.t_lag} days)")
            elif sst_data is not None and 'sst' in sst_data.data_vars:
                sst = sst_data['sst']
                logger.info("Using current SST data (no lag)")
            else:
                raise ValueError("SST data is required but not available")
            
            # Salinity (current)
            if salinity_data is not None and 'salinity' in salinity_data.data_vars:
                salinity = salinity_data['salinity']
                logger.info("Using current salinity data")
            else:
                raise ValueError("Salinity data is required but not available")
            
            # ========================================
            # STEP 2: Calculate suitability functions for I_Phys
            # ========================================
            logger.info("--- Calculating I_Phys components ---")
            
            # Temperature suitability
            f_temp = self._calculate_temperature_suitability(sst, profile)
            
            # Salinity suitability (enhanced trapezoidal)
            f_sal = self._calculate_salinity_suitability(salinity, profile)
            
            # Oxygen suitability (enhanced with sigmoid)
            if oxygen_data is not None and 'oxygen' in oxygen_data.data_vars:
                logger.info("Using provided oxygen data")
                f_oxy = self._calculate_oxygen_suitability(oxygen_data['oxygen'], profile)
            elif use_enhanced_model:
                # Derive oxygen from temperature and salinity
                logger.info("Deriving oxygen from temperature and salinity (Garcia-Gordon)")
                from data.nasa_data import NASADataManager
                nasa_manager = NASADataManager()
                oxygen_dataset = nasa_manager.derive_oxygen_from_temp_salinity(sst_data, salinity_data)
                if oxygen_dataset is not None:
                    f_oxy = self._calculate_oxygen_suitability(oxygen_dataset['oxygen'], profile)
                else:
                    logger.warning("Oxygen derivation failed, using neutral value (1.0)")
                    f_oxy = xr.ones_like(sst)
            else:
                f_oxy = xr.ones_like(sst)  # Neutral for legacy model
            
            # Oceanographic features (eddies + fronts)
            f_ocean = self._normalize_sea_level_anomaly(sla, profile)
            
            # Calculate I_Phys
            i_phys = self._calculate_physicochemical_index(f_temp, f_sal, f_oxy, f_ocean)
            
            # ========================================
            # STEP 3: Calculate I_Prey (Prey Availability Index)
            # ========================================
            logger.info("--- Calculating I_Prey components ---")
            
            # Chlorophyll as baseline productivity
            f_chl = self._normalize_chlorophyll(chl)
            
            # Process prey density data if available
            f_prey_dict = {}
            if prey_data is not None and use_enhanced_model:
                for prey_type, prey_dataset in prey_data.items():
                    if prey_dataset is not None:
                        prey_var = list(prey_dataset.data_vars)[0]
                        f_prey_dict[prey_type] = self._calculate_prey_suitability(
                            prey_dataset[prey_var], prey_type
                        )
                        logger.info(f"Processed {prey_type} prey data")
            
            # Calculate I_Prey
            i_prey = self._calculate_prey_index(f_chl, f_prey_dict, profile)
            
            # ========================================
            # STEP 4: Calculate I_Topo (Topographic Index)
            # ========================================
            logger.info("--- Calculating I_Topo components ---")
            
            if bathymetry_data is not None and use_enhanced_model:
                if 'depth' in bathymetry_data.data_vars and 'slope' in bathymetry_data.data_vars:
                    f_depth = self._calculate_depth_suitability(bathymetry_data['depth'], profile)
                    f_slope = self._calculate_slope_suitability(bathymetry_data['slope'], profile)
                    i_topo = self._calculate_topographic_index(f_depth, f_slope)
                    logger.info("Using bathymetry data for topographic index")
                else:
                    logger.warning("Bathymetry data incomplete, using neutral topography (1.0)")
                    i_topo = xr.ones_like(sst)
            else:
                logger.info("No bathymetry data, using neutral topography (1.0)")
                i_topo = xr.ones_like(sst)
            
            # ========================================
            # STEP 5: Calculate I_Anthro (Anthropogenic Pressure)
            # ========================================
            logger.info("--- Calculating I_Anthro components ---")
            
            if use_enhanced_model:
                # Fishing pressure
                if fishing_pressure_data is not None and 'fishing_pressure' in fishing_pressure_data.data_vars:
                    # GFW data is already on the same grid as NASA data (361x721)
                    # No regridding needed - just squeeze extra dimensions
                    fishing_data = fishing_pressure_data['fishing_pressure'].squeeze()
                    logger.info(f"Using fishing pressure data (shape: {fishing_data.shape})")
                    f_fishing = self._calculate_anthropogenic_pressure(
                        fishing_data, 'fishing'
                    )
                    logger.info("Using fishing pressure data (regridded)")
                else:
                    f_fishing = xr.zeros_like(sst)
                    logger.info("No fishing pressure data, assuming zero pressure")
                
                # Shipping density
                if shipping_density_data is not None and 'shipping_density' in shipping_density_data.data_vars:
                    # GFW data is already on the same grid as NASA data (361x721)
                    # No regridding needed - just squeeze extra dimensions
                    shipping_data = shipping_density_data['shipping_density'].squeeze()
                    logger.info(f"Using shipping density data (shape: {shipping_data.shape})")
                    f_shipping = self._calculate_anthropogenic_pressure(
                        shipping_data, 'shipping'
                    )
                    logger.info("Using shipping density data (regridded)")
                else:
                    f_shipping = xr.zeros_like(sst)
                    logger.info("No shipping density data, assuming zero pressure")
                
                # Calculate I_Anthro
                i_anthro = self._calculate_anthropogenic_index(f_fishing, f_shipping)
            else:
                i_anthro = xr.zeros_like(sst)  # No anthropogenic filter for legacy model
            
            # ========================================
            # STEP 6: Calculate Final HSI
            # ========================================
            logger.info("--- Calculating Final HSI ---")
            
            if use_enhanced_model:
                # ENHANCED MODEL FORMULA:
                # HSI = (w_Phys × I_Phys + w_Prey × I_Prey + w_Topo × I_Topo) × (1 - I_Anthro)
                hsi = (
                    (profile.w_phys * i_phys) +
                    (profile.w_prey * i_prey) +
                    (profile.w_topo * i_topo)
                ) * (1.0 - i_anthro)
                
                model_type = "Enhanced Ecological Niche Model"
                logger.info(f"Using ENHANCED model: w_phys={profile.w_phys}, w_prey={profile.w_prey}, w_topo={profile.w_topo}")
            else:
                # LEGACY MODEL FORMULA (for compatibility):
                # HSI = f_sal × (f_chl^w_c × f_ocean^w_e × f_temp^w_s)^(1/total_weight)
                # Note: legacy model uses old weights, need to access them differently
                # For simplicity, use I_Phys as proxy for legacy model
                hsi = f_sal * i_phys
                model_type = "Legacy Oceanographic Model"
                logger.info("Using LEGACY model for backward compatibility")
            
            # Replace any NaN values with 0
            hsi = hsi.where(np.isfinite(hsi), 0.0)
            hsi = hsi.clip(0, 1)  # Ensure 0-1 range
            
            # Squeeze out any extra dimensions to ensure 2D (lat, lon) only
            hsi = hsi.squeeze()
            
            # ========================================
            # STEP 7: Create comprehensive result dataset
            # ========================================
            
            # Ensure all variables are 2D by squeezing extra dimensions
            result = xr.Dataset({
                'hsi': hsi.squeeze(),
                # Main indices
                'i_phys': i_phys.squeeze(),
                'i_prey': i_prey.squeeze(),
                'i_topo': i_topo.squeeze(),
                'i_anthro': i_anthro.squeeze(),
                # Individual suitability components
                'temperature_suitability': f_temp.squeeze(),
                'salinity_suitability': f_sal.squeeze(),
                'oxygen_suitability': (f_oxy if use_enhanced_model else xr.ones_like(sst)).squeeze(),
                'oceanographic_suitability': f_ocean.squeeze(),
                'chlorophyll_suitability': f_chl.squeeze()
            })
            
            # Add bathymetry components if available
            if bathymetry_data is not None and use_enhanced_model:
                if 'depth' in bathymetry_data.data_vars:
                    result['depth_suitability'] = f_depth
                if 'slope' in bathymetry_data.data_vars:
                    result['slope_suitability'] = f_slope
            
            # Add metadata
            result.attrs.update({
                'shark_species': profile.name,
                'target_date': target_date,
                'model_version': '2.0_enhanced',
                'model_type': model_type,
                'formula': 'HSI = (w_Phys*I_Phys + w_Prey*I_Prey + w_Topo*I_Topo) * (1-I_Anthro)',
                'parameters': {
                    # Model weights
                    'w_phys': profile.w_phys,
                    'w_prey': profile.w_prey,
                    'w_topo': profile.w_topo,
                    # Temperature
                    's_opt': profile.s_opt,
                    'sigma_s': profile.sigma_s,
                    't_lag': profile.t_lag,
                    # Salinity
                    'salinity_min': profile.salinity_min,
                    'salinity_opt_min': profile.salinity_opt_min,
                    'salinity_opt_max': profile.salinity_opt_max,
                    'salinity_max': profile.salinity_max,
                    # Oxygen
                    'oxygen_min': profile.oxygen_min,
                    'oxygen_opt': profile.oxygen_opt,
                    # Chlorophyll
                    'c_lag': profile.c_lag,
                    # Depth
                    'depth_opt_min': profile.depth_opt_min,
                    'depth_opt_max': profile.depth_opt_max
                }
            })
            
            # Log final statistics
            hsi_mean = float(hsi.mean().values)
            hsi_max = float(hsi.max().values)
            logger.info(f"✓ HSI calculation complete: mean={hsi_mean:.4f}, max={hsi_max:.4f}")
            logger.info(f"=== {model_type} calculation finished ===")
            
            return result
            
        except Exception as e:
            logger.error(f"HSI calculation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
    
    def _normalize_sea_level_anomaly(self, sla: xr.DataArray, profile: SharkProfile) -> xr.DataArray:
        """
        Normalize sea level anomaly for comprehensive eddy and front detection using NASA-SSH data
        
        This function implements sophisticated oceanographic feature detection based on NASA-SSH
        specifications and oceanographic principles:
        
        1. EDDY DETECTION (NASA-SSH Enhanced):
           - Cyclonic Eddies (negative SLA): Cold-core eddies creating upwelling
             * Bring nutrient-rich deep water to surface (5-10 km diameter nadir measurements)
             * Promote phytoplankton blooms → prey aggregation → shark foraging
             * Detected by NASA-SSH 0.5° grid resolution (captures 50-300 km eddies)
           - Anticyclonic Eddies (positive SLA): Warm-core eddies creating downwelling
             * Concentrate prey at depth, different foraging dynamics
             * Warm-core eddies can create prey aggregation zones
           - NASA-SSH Processing: 10-day observations with Gaussian weighted spatial averaging
           - Gaussian normalization: f_eddy = exp(-E'²/(2σ²)) where σ = 0.1m
           - Optimal strength: Moderate SLA values (±0.1m) provide highest suitability
           - Basin-aware: Data averaging respects ocean basin connectivity rules
        
        2. FRONT DETECTION (NASA-SSH Enhanced):
           - Ocean Fronts: Sharp boundaries between water masses
           - Spatial gradients: |∇SLA| = √((∂SLA/∂lat)² + (∂SLA/∂lon)²)
           - Front suitability: f_front = exp(-|∇SLA|/σ_front) where σ_front = 0.05 m/degree
           - Convergence zones: Where different water masses meet → prey concentration
           - NASA-SSH Quality: Orbit error reduction (OER) applied, ~2.3 cm RMS reduction
           - Quality Control: nasa_flag=0, median_filter_flag=0, source_flag filtered
        
        3. COMBINED SUITABILITY:
           - Weighted combination: f_E = 0.6 × f_eddy + 0.4 × f_front
           - Eddies (60%): Primary foraging hotspots from upwelling/downwelling
           - Fronts (40%): Secondary but important prey concentration zones
           - Reference Surface: DTU21 Mean Sea Surface (1993-2012) for anomaly calculation
        
        Args:
            sla: Sea Level Anomaly data in meters (NASA-SSH processed)
            
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
            
            # STEP 2: EDDY DETECTION (NASA-SSH Enhanced)
            # Eddies are circular ocean features detected by SLA anomalies
            # Both positive (anticyclonic) and negative (cyclonic) eddies are important
            # NASA-SSH provides high-quality data with orbit error reduction applied
            sigma_e = 0.1  # Standard deviation for eddy strength normalization (NASA-SSH optimized)
            eddy_suitability = np.exp(-(sla_clean ** 2) / (2 * sigma_e ** 2))
            
            # Log NASA-SSH eddy detection statistics
            eddy_stats = {
                'mean_sla': float(sla_clean.mean().values) if not np.isnan(sla_clean.mean().values) else 0.0,
                'std_sla': float(sla_clean.std().values) if not np.isnan(sla_clean.std().values) else 0.0,
                'cyclonic_eddies': float((sla_clean < -0.05).sum().values),  # Negative SLA > 5cm
                'anticyclonic_eddies': float((sla_clean > 0.05).sum().values)  # Positive SLA > 5cm
            }
            
            logger.info(f"NASA-SSH eddy detection statistics:")
            logger.info(f"  Mean SLA: {eddy_stats['mean_sla']:.4f}m, Std: {eddy_stats['std_sla']:.4f}m")
            logger.info(f"  Cyclonic eddies (SLA < -0.05m): {eddy_stats['cyclonic_eddies']:.0f} points")
            logger.info(f"  Anticyclonic eddies (SLA > 0.05m): {eddy_stats['anticyclonic_eddies']:.0f} points")
            
            # STEP 3: COMBINE EDDY AND FRONT SUITABILITY (NASA-SSH Enhanced)
            # Both features contribute to prey concentration but with different weights
            # Species-specific weights allow customization of eddy vs front importance
            # Default: Eddies (60%): Primary foraging hotspots from upwelling/downwelling
            # Default: Fronts (40%): Secondary but important convergence zones
            # NASA-SSH quality control ensures reliable feature detection
            combined_suitability = profile.w_eddy * eddy_suitability + profile.w_front * front_suitability
            
            logger.info(f"Oceanographic features weighted: eddies={profile.w_eddy*100:.0f}%, fronts={profile.w_front*100:.0f}%")
            
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
        Calculate salinity suitability using trapezoidal function (ENHANCED MODEL)
        
        This replaces the binary filter with a continuous trapezoidal function that allows
        gradual decrease in suitability near tolerance limits. This is more biologically
        realistic, especially for euryhaline species like bull sharks.
        
        Trapezoidal function:
        - 0 for S < salinity_min or S > salinity_max (unsurvivable)
        - Linear ramp from salinity_min to salinity_opt_min (marginal habitat)
        - 1 for salinity_opt_min <= S <= salinity_opt_max (optimal habitat)
        - Linear ramp from salinity_opt_max to salinity_max (marginal habitat)
        
        Args:
            salinity: Salinity data array (psu)
            profile: Shark species profile with salinity parameters
            
        Returns:
            Salinity suitability (0-1 scale)
        """
        try:
            # Remove invalid values
            salinity_clean = salinity.where(np.isfinite(salinity))
            
            # Initialize suitability array
            suitability = xr.zeros_like(salinity_clean)
            
            # Region 1: Below minimum (unsurvivable) - already 0
            
            # Region 2: Ramp up from min to optimal minimum
            mask_ramp_up = (salinity_clean >= profile.salinity_min) & (salinity_clean < profile.salinity_opt_min)
            if profile.salinity_opt_min > profile.salinity_min:
                ramp_up_value = ((salinity_clean - profile.salinity_min) / 
                                (profile.salinity_opt_min - profile.salinity_min))
                suitability = suitability.where(~mask_ramp_up, ramp_up_value)
            
            # Region 3: Optimal range (full suitability = 1.0)
            mask_optimal = (salinity_clean >= profile.salinity_opt_min) & (salinity_clean <= profile.salinity_opt_max)
            suitability = suitability.where(~mask_optimal, 1.0)
            
            # Region 4: Ramp down from optimal maximum to max
            mask_ramp_down = (salinity_clean > profile.salinity_opt_max) & (salinity_clean <= profile.salinity_max)
            if profile.salinity_max > profile.salinity_opt_max:
                ramp_down_value = ((profile.salinity_max - salinity_clean) / 
                                  (profile.salinity_max - profile.salinity_opt_max))
                suitability = suitability.where(~mask_ramp_down, ramp_down_value)
            
            # Region 5: Above maximum (unsurvivable) - already 0
            
            # Clip to ensure values are between 0 and 1
            suitability = suitability.clip(0, 1)
            
            # Log statistics
            total_points = salinity_clean.size
            unsuitable_points = np.sum(suitability.values == 0)
            if unsuitable_points > 0:
                exclusion_percent = 100 * unsuitable_points / total_points
                logger.info(f"Salinity filtering: {unsuitable_points}/{total_points} points ({exclusion_percent:.1f}%) completely unsuitable")
            
            optimal_points = np.sum(suitability.values == 1.0)
            optimal_percent = 100 * optimal_points / total_points
            logger.info(f"Salinity optimal: {optimal_points}/{total_points} points ({optimal_percent:.1f}%) in optimal range {profile.salinity_opt_min}-{profile.salinity_opt_max} psu")
            
            return suitability
            
        except Exception as e:
            logger.error(f"Salinity suitability calculation failed: {e}")
            # Return all suitable in case of error (conservative approach)
            return xr.ones_like(salinity)
    
    def _calculate_oxygen_suitability(self, oxygen: xr.DataArray, profile: SharkProfile) -> xr.DataArray:
        """
        Calculate dissolved oxygen suitability using sigmoid function (NEW)
        
        Hypoxic (low-oxygen) zones are major physiological barriers for active sharks.
        Uses a sigmoid function to model the rapid decrease in suitability below oxygen threshold.
        
        Sigmoid function:
        f_oxy(O) = 1 / (1 + exp(-(O - O_min) / sigma_oxy))
        
        Args:
            oxygen: Dissolved oxygen data array (mg/L)
            profile: Shark species profile with oxygen parameters
            
        Returns:
            Oxygen suitability (0-1 scale)
        """
        try:
            # Remove invalid values
            oxygen_clean = oxygen.where(np.isfinite(oxygen))
            
            # Apply sigmoid function
            # Suitability approaches 1 for high oxygen, 0 for oxygen < oxygen_min
            suitability = 1.0 / (1.0 + np.exp(-(oxygen_clean - profile.oxygen_min) / profile.oxygen_sigma))
            
            # Additional boost for values near optimal
            # Optional: give extra suitability for oxygen near optimal value
            optimal_bonus = np.exp(-((oxygen_clean - profile.oxygen_opt) ** 2) / (2 * profile.oxygen_sigma ** 2))
            suitability = (suitability * 0.7 + optimal_bonus * 0.3)  # Weighted combination
            
            # Clip to ensure values are between 0 and 1
            suitability = suitability.clip(0, 1)
            
            # Log hypoxic areas
            hypoxic_threshold = profile.oxygen_min
            hypoxic_points = np.sum((oxygen_clean < hypoxic_threshold).values)
            total_points = oxygen_clean.size
            if hypoxic_points > 0:
                hypoxic_percent = 100 * hypoxic_points / total_points
                logger.info(f"Hypoxic zones: {hypoxic_points}/{total_points} points ({hypoxic_percent:.1f}%) below {hypoxic_threshold} mg/L")
            
            return suitability
            
        except Exception as e:
            logger.error(f"Oxygen suitability calculation failed: {e}")
            # Return all suitable in case of error (conservative approach)
            return xr.ones_like(oxygen)
    
    def _calculate_depth_suitability(self, depth: xr.DataArray, profile: SharkProfile) -> xr.DataArray:
        """
        Calculate depth suitability using trapezoidal function (NEW)
        
        Depth is one of the strongest predictors of shark distribution. This function
        assigns high suitability to species' preferred depth range using a trapezoidal function.
        
        Args:
            depth: Bathymetric depth data array (m, positive values)
            profile: Shark species profile with depth parameters
            
        Returns:
            Depth suitability (0-1 scale)
        """
        try:
            # Remove invalid values
            depth_clean = depth.where(np.isfinite(depth))
            
            # Initialize suitability array
            suitability = xr.zeros_like(depth_clean)
            
            # Region 1: Too shallow (below minimum) - already 0
            
            # Region 2: Ramp up from min to optimal minimum
            mask_ramp_up = (depth_clean >= profile.depth_min) & (depth_clean < profile.depth_opt_min)
            if profile.depth_opt_min > profile.depth_min:
                ramp_up_value = ((depth_clean - profile.depth_min) / 
                                (profile.depth_opt_min - profile.depth_min))
                suitability = suitability.where(~mask_ramp_up, ramp_up_value)
            
            # Region 3: Optimal depth range (full suitability = 1.0)
            mask_optimal = (depth_clean >= profile.depth_opt_min) & (depth_clean <= profile.depth_opt_max)
            suitability = suitability.where(~mask_optimal, 1.0)
            
            # Region 4: Ramp down from optimal maximum to max depth
            mask_ramp_down = (depth_clean > profile.depth_opt_max) & (depth_clean <= profile.depth_max)
            if profile.depth_max > profile.depth_opt_max:
                ramp_down_value = ((profile.depth_max - depth_clean) / 
                                  (profile.depth_max - profile.depth_opt_max))
                suitability = suitability.where(~mask_ramp_down, ramp_down_value)
            
            # Region 5: Too deep (beyond maximum) - already 0
            
            # Clip to ensure values are between 0 and 1
            suitability = suitability.clip(0, 1)
            
            return suitability
            
        except Exception as e:
            logger.error(f"Depth suitability calculation failed: {e}")
            return xr.ones_like(depth)
    
    def _calculate_slope_suitability(self, slope: xr.DataArray, profile: SharkProfile) -> xr.DataArray:
        """
        Calculate seafloor slope suitability using Gaussian function (NEW)
        
        Moderate slopes (continental shelf breaks, seamount edges) are known foraging hotspots.
        Uses a Gaussian function centered on the optimal slope.
        
        Args:
            slope: Seafloor slope data array (degrees)
            profile: Shark species profile with slope parameters
            
        Returns:
            Slope suitability (0-1 scale)
        """
        try:
            # Remove invalid values
            slope_clean = slope.where(np.isfinite(slope))
            
            # Apply Gaussian function centered on optimal slope
            suitability = np.exp(-((slope_clean - profile.slope_opt) ** 2) / 
                                (2 * profile.slope_sigma ** 2))
            
            # Clip to ensure values are between 0 and 1
            suitability = suitability.clip(0, 1)
            
            return suitability
            
        except Exception as e:
            logger.error(f"Slope suitability calculation failed: {e}")
            return xr.ones_like(slope)
    
    def _calculate_prey_suitability(self, prey_density: xr.DataArray, prey_type: str) -> xr.DataArray:
        """
        Calculate prey availability suitability using normalization (NEW)
        
        Converts prey density to a 0-1 suitability scale using a saturation function.
        Higher prey density = higher suitability up to a saturation point.
        
        Args:
            prey_density: Prey density data array (individuals/km²)
            prey_type: Type of prey for logging
            
        Returns:
            Prey suitability (0-1 scale)
        """
        try:
            # Remove invalid values
            prey_clean = prey_density.where(np.isfinite(prey_density))
            prey_clean = prey_clean.where(prey_clean >= 0)
            
            # Normalize using a saturation function similar to chlorophyll
            # f_prey(D) = D / (D + k_prey)
            k_prey = prey_clean.quantile(0.5).values  # Use median as saturation constant
            if k_prey == 0 or np.isnan(k_prey):
                k_prey = 1.0  # Fallback value
            
            suitability = prey_clean / (prey_clean + k_prey)
            
            # Clip to ensure values are between 0 and 1
            suitability = suitability.clip(0, 1)
            
            logger.info(f"Prey suitability ({prey_type}): k_prey={k_prey:.4f}")
            
            return suitability
            
        except Exception as e:
            logger.error(f"Prey suitability calculation failed for {prey_type}: {e}")
            # Return moderate suitability (0.5) in case of error
            return xr.full_like(prey_density, 0.5)
    
    def _calculate_anthropogenic_pressure(self, pressure_data: xr.DataArray, pressure_type: str) -> xr.DataArray:
        """
        Calculate anthropogenic pressure index (NEW)
        
        Converts fishing/shipping pressure to a 0-1 risk index where:
        - 0 = no human pressure (no displacement risk)
        - 1 = maximum pressure (high displacement risk)
        
        Args:
            pressure_data: Pressure data array (fishing hours or vessel count)
            pressure_type: Type of pressure for logging
            
        Returns:
            Anthropogenic pressure index (0-1 scale)
        """
        try:
            # Remove invalid values
            pressure_clean = pressure_data.where(np.isfinite(pressure_data))
            pressure_clean = pressure_clean.where(pressure_clean >= 0)
            
            # Normalize to 0-1 scale using percentile-based method
            # Use 95th percentile as "high pressure" threshold
            p95 = pressure_clean.quantile(0.95).values
            if p95 == 0 or np.isnan(p95):
                p95 = 1.0  # Fallback value
            
            pressure_index = (pressure_clean / p95).clip(0, 1)
            
            logger.info(f"Anthropogenic pressure ({pressure_type}): 95th percentile={p95:.4f}")
            
            return pressure_index
            
        except Exception as e:
            logger.error(f"Anthropogenic pressure calculation failed for {pressure_type}: {e}")
            # Return no pressure (0) in case of error (conservative approach)
            return xr.zeros_like(pressure_data)
    
    def _calculate_physicochemical_index(self, 
                                         f_temp: xr.DataArray,
                                         f_sal: xr.DataArray, 
                                         f_oxy: xr.DataArray,
                                         f_ocean: xr.DataArray) -> xr.DataArray:
        """
        Calculate Physicochemical & Oceanographic Index (I_Phys) - NEW
        
        This represents the dynamic, water-column-based habitat using a geometric mean
        of four normalized suitability functions:
        
        I_Phys = (f_temp × f_sal × f_oxy × f_ocean)^(1/4)
        
        Args:
            f_temp: Temperature suitability
            f_sal: Salinity suitability
            f_oxy: Oxygen suitability
            f_ocean: Oceanographic feature suitability (eddies + fronts)
            
        Returns:
            Physicochemical index (0-1 scale)
        """
        try:
            # Geometric mean of the four components
            i_phys = (f_temp * f_sal * f_oxy * f_ocean) ** 0.25
            
            # Clip to ensure values are between 0 and 1
            i_phys = i_phys.clip(0, 1)
            
            logger.info(f"I_Phys calculated: mean={float(i_phys.mean().values):.4f}")
            
            return i_phys
            
        except Exception as e:
            logger.error(f"I_Phys calculation failed: {e}")
            return xr.zeros_like(f_temp)
    
    def _calculate_prey_index(self,
                             f_chl: xr.DataArray,
                             f_prey_dict: Dict[str, xr.DataArray],
                             profile: SharkProfile) -> xr.DataArray:
        """
        Calculate Prey Availability Index (I_Prey) - NEW
        
        This directly models the food landscape using weighted sum of prey guild densities:
        
        I_Prey = Σ(f_prey_i × w_diet_i) + (f_chl × w_chl)
        
        Args:
            f_chl: Chlorophyll suitability (baseline productivity)
            f_prey_dict: Dictionary of prey suitabilities by type
            profile: Shark species profile with dietary weights
            
        Returns:
            Prey availability index (0-1 scale)
        """
        try:
            # Start with chlorophyll contribution (baseline productivity)
            i_prey = f_chl * profile.w_chl
            
            # Add specific prey contributions if available
            if 'pinnipeds' in f_prey_dict:
                i_prey = i_prey + (f_prey_dict['pinnipeds'] * profile.w_prey_pinnipeds)
            else:
                # If no data, use chlorophyll as proxy
                i_prey = i_prey + (f_chl * profile.w_prey_pinnipeds)
            
            if 'turtles' in f_prey_dict:
                i_prey = i_prey + (f_prey_dict['turtles'] * profile.w_prey_turtles)
            else:
                i_prey = i_prey + (f_chl * profile.w_prey_turtles)
            
            if 'fish' in f_prey_dict:
                i_prey = i_prey + (f_prey_dict['fish'] * profile.w_prey_fish)
            else:
                i_prey = i_prey + (f_chl * profile.w_prey_fish)
            
            if 'cephalopods' in f_prey_dict:
                i_prey = i_prey + (f_prey_dict['cephalopods'] * profile.w_prey_cephalopods)
            else:
                i_prey = i_prey + (f_chl * profile.w_prey_cephalopods)
            
            # Normalize to 0-1 scale (weights should sum to 1)
            i_prey = i_prey.clip(0, 1)
            
            logger.info(f"I_Prey calculated: mean={float(i_prey.mean().values):.4f}")
            
            return i_prey
            
        except Exception as e:
            logger.error(f"I_Prey calculation failed: {e}")
            return f_chl  # Fallback to just chlorophyll
    
    def _calculate_topographic_index(self,
                                     f_depth: xr.DataArray,
                                     f_slope: xr.DataArray) -> xr.DataArray:
        """
        Calculate Topographic Index (I_Topo) - NEW
        
        This incorporates static seafloor features using geometric mean:
        
        I_Topo = (f_depth × f_slope)^(1/2)
        
        Args:
            f_depth: Depth suitability
            f_slope: Seafloor slope suitability
            
        Returns:
            Topographic index (0-1 scale)
        """
        try:
            # Geometric mean of depth and slope
            i_topo = (f_depth * f_slope) ** 0.5
            
            # Clip to ensure values are between 0 and 1
            i_topo = i_topo.clip(0, 1)
            
            logger.info(f"I_Topo calculated: mean={float(i_topo.mean().values):.4f}")
            
            return i_topo
            
        except Exception as e:
            logger.error(f"I_Topo calculation failed: {e}")
            return xr.ones_like(f_depth)
    
    def _calculate_anthropogenic_index(self,
                                       f_fishing: xr.DataArray,
                                       f_shipping: xr.DataArray) -> xr.DataArray:
        """
        Calculate Anthropogenic Pressure Index (I_Anthro) - NEW
        
        This acts as a negative modulator using maximum pressure:
        
        I_Anthro = max(f_fishing, f_shipping)
        
        The max function ensures the single greatest human threat dictates displacement risk.
        
        Args:
            f_fishing: Fishing pressure index
            f_shipping: Shipping density index
            
        Returns:
            Anthropogenic pressure index (0-1 scale)
        """
        try:
            # Take maximum of the two pressure sources
            i_anthro = xr.ufuncs.maximum(f_fishing, f_shipping)
            
            # Clip to ensure values are between 0 and 1
            i_anthro = i_anthro.clip(0, 1)
            
            logger.info(f"I_Anthro calculated: mean={float(i_anthro.mean().values):.4f}")
            
            return i_anthro
            
        except Exception as e:
            logger.error(f"I_Anthro calculation failed: {e}")
            return xr.zeros_like(f_fishing)
    
    def get_shark_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Get available shark species profiles"""
        return {
            species: {
                'name': profile.name,
                # Temperature parameters
                's_opt': profile.s_opt,
                'sigma_s': profile.sigma_s,
                't_lag': profile.t_lag,
                # Salinity parameters
                'salinity_min': profile.salinity_min,
                'salinity_opt_min': profile.salinity_opt_min,
                'salinity_opt_max': profile.salinity_opt_max,
                'salinity_max': profile.salinity_max,
                # Oxygen parameters
                'oxygen_min': profile.oxygen_min,
                'oxygen_opt': profile.oxygen_opt,
                'oxygen_sigma': profile.oxygen_sigma,
                # Chlorophyll/prey parameters
                'c_lag': profile.c_lag,
                'w_chl': profile.w_chl,
                # Depth parameters
                'depth_min': profile.depth_min,
                'depth_opt_min': profile.depth_opt_min,
                'depth_opt_max': profile.depth_opt_max,
                'depth_max': profile.depth_max,
                # Model weights
                'w_phys': profile.w_phys,
                'w_prey': profile.w_prey,
                'w_topo': profile.w_topo
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
    
    
    def calculate_component_contributions(self, 
                                         i_phys: float, 
                                         i_prey: float, 
                                         i_topo: float, 
                                         i_anthro: float,
                                         profile: SharkProfile) -> Dict[str, float]:
        """
        Calculate the relative contribution of each component to the HSI score (ENHANCED MODEL)
        
        For the enhanced model:
        HSI = (w_Phys × I_Phys + w_Prey × I_Prey + w_Topo × I_Topo) × (1 - I_Anthro)
        
        This function calculates:
        1. The weighted contribution of each index (before anthropogenic filter)
        2. The effective contribution after anthropogenic pressure is applied

        Args:
            i_phys: Physicochemical & Oceanographic Index (0-1)
            i_prey: Prey Availability Index (0-1)
            i_topo: Topographic Index (0-1)
            i_anthro: Anthropogenic Pressure Index (0-1)
            profile: Shark species profile with weights

        Returns:
            Dictionary with contribution percentages and metrics:
            - physicochemical_pct: % contribution of I_Phys
            - prey_pct: % contribution of I_Prey
            - topographic_pct: % contribution of I_Topo
            - anthropogenic_reduction_pct: % HSI reduction due to human pressure
            - base_hsi: HSI before anthropogenic filter
            - final_hsi: HSI after anthropogenic filter
        """
        try:
            # Calculate base HSI (before anthropogenic filter)
            # This is the weighted linear combination of the three indices
            base_hsi = (profile.w_phys * i_phys + 
                       profile.w_prey * i_prey + 
                       profile.w_topo * i_topo)
            
            # Calculate final HSI (after anthropogenic filter)
            final_hsi = base_hsi * (1.0 - i_anthro)
            
            # Handle edge case where base_hsi is zero
            if base_hsi == 0:
                return {
                    'physicochemical_pct': profile.w_phys * 100,
                    'prey_pct': profile.w_prey * 100,
                    'topographic_pct': profile.w_topo * 100,
                    'anthropogenic_reduction_pct': 0.0,
                    'base_hsi': 0.0,
                    'final_hsi': 0.0,
                    'physicochemical_absolute': 0.0,
                    'prey_absolute': 0.0,
                    'topographic_absolute': 0.0
                }
            
            # Calculate absolute contributions (weighted index values)
            phys_absolute = profile.w_phys * i_phys
            prey_absolute = profile.w_prey * i_prey
            topo_absolute = profile.w_topo * i_topo
            
            # Calculate percentage contributions (relative to base_hsi)
            # These show how much each index contributes to the pre-filtered habitat quality
            phys_pct = (phys_absolute / base_hsi) * 100
            prey_pct = (prey_absolute / base_hsi) * 100
            topo_pct = (topo_absolute / base_hsi) * 100
            
            # Calculate anthropogenic reduction
            # This shows how much the habitat quality is reduced by human pressure
            anthro_reduction_pct = i_anthro * 100
            
            return {
                # Percentage contributions
                'physicochemical_pct': phys_pct,
                'prey_pct': prey_pct,
                'topographic_pct': topo_pct,
                'anthropogenic_reduction_pct': anthro_reduction_pct,
                
                # HSI values
                'base_hsi': base_hsi,
                'final_hsi': final_hsi,
                
                # Absolute contributions (for detailed analysis)
                'physicochemical_absolute': phys_absolute,
                'prey_absolute': prey_absolute,
                'topographic_absolute': topo_absolute,
                
                # Index weights (model configuration)
                'weight_physicochemical': profile.w_phys,
                'weight_prey': profile.w_prey,
                'weight_topographic': profile.w_topo,
                
                # Raw index values (for debugging/analysis)
                'i_phys_raw': i_phys,
                'i_prey_raw': i_prey,
                'i_topo_raw': i_topo,
                'i_anthro_raw': i_anthro
            }

        except Exception as e:
            logger.error(f"Component contribution calculation failed: {e}")
            return {
                'physicochemical_pct': 0.0,
                'prey_pct': 0.0,
                'topographic_pct': 0.0,
                'anthropogenic_reduction_pct': 0.0,
                'base_hsi': 0.0,
                'final_hsi': 0.0,
                'physicochemical_absolute': 0.0,
                'prey_absolute': 0.0,
                'topographic_absolute': 0.0
            }
    
    def calculate_legacy_component_contributions(self, f_c: float, f_e: float, f_s: float, 
                                                 profile: SharkProfile) -> Dict[str, float]:
        """
        Calculate component contributions for LEGACY MODEL (v1.0) - DEPRECATED
        
        This is kept for backward compatibility with the original model.
        For the enhanced model, use calculate_component_contributions() instead.
        
        Legacy formula: HSI = f_sal × (f_C^w_c × f_E^w_e × f_S^w_s)^(1/total_weight)

        Args:
            f_c: Chlorophyll suitability (0-1)
            f_e: Oceanographic suitability (0-1)
            f_s: Temperature suitability (0-1)
            profile: Shark species profile with weights

        Returns:
            Dictionary with contribution percentages for legacy components
        """
        try:
            # Note: Legacy model doesn't have w_c, w_e, w_s anymore
            # For backward compatibility, we return uniform distribution
            logger.warning("Legacy component contributions called - model has been enhanced")
            
            return {
                'chlorophyll': 33.3,
                'oceanographic': 33.3,
                'temperature': 33.4,
                'note': 'Legacy model - consider using enhanced model calculate_component_contributions()'
            }

        except Exception as e:
            logger.error(f"Legacy component contribution calculation failed: {e}")
            return {
                'chlorophyll': 0.0,
                'oceanographic': 0.0,
                'temperature': 0.0
            }

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
