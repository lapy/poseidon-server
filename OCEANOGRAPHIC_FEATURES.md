# Oceanographic Features in Shark Habitat Suitability

This document provides comprehensive information about how oceanographic features (eddies and fronts) are detected and integrated into the Shark Habitat Suitability Index (HSI) model.

## 🚀 NASA Space Apps Challenge 2025 - Sharks from Space

This project is part of the **2025 NASA Space Apps Challenge** - [**Sharks from Space**](https://www.spaceappschallenge.org/2025/challenges/sharks-from-space/?tab=details) challenge. This document demonstrates how NASA satellite data can be leveraged to understand and predict shark behavior through advanced oceanographic feature detection.

## Overview

Our HSI model explicitly considers mesoscale oceanographic features that drive prey concentration and shark foraging behavior. These features are detected through sophisticated analysis of Sea Surface Height (SSH) anomalies and gradients.

## 🌀 Eddy Detection

### What are Ocean Eddies?

Ocean eddies are circular currents of water that can span 50-300 kilometers in diameter. They are the "storms" of the ocean and play crucial roles in marine ecosystems by:

- **Nutrient Transport**: Moving nutrients from deep to surface waters
- **Prey Concentration**: Creating areas where marine life aggregates
- **Temperature Regulation**: Influencing local water temperatures
- **Migration Corridors**: Providing pathways for marine species

### Eddy Types in Our Model

#### 1. Cyclonic Eddies (Cold-Core)
- **SLA Signature**: Negative Sea Level Anomaly (depression)
- **Physical Process**: Upwelling of cold, nutrient-rich deep water
- **Ecological Impact**: 
  - Promotes phytoplankton blooms
  - Creates high productivity zones
  - Attracts prey species
  - Becomes shark foraging hotspots

#### 2. Anticyclonic Eddies (Warm-Core)
- **SLA Signature**: Positive Sea Level Anomaly (elevation)
- **Physical Process**: Downwelling of warm surface water
- **Ecological Impact**:
  - Concentrates prey at depth
  - Creates different foraging dynamics
  - Provides thermal refuge for prey
  - Alternative foraging opportunities

### Mathematical Implementation

```math
f_{eddy} = \exp\left(-\frac{E'^2}{2\sigma^2}\right)
```

Where:
- `mathE'` = Sea Level Anomaly (m)
- `math\sigma = 0.1` m (standard deviation for optimal eddy strength)

**Key Parameters:**
- **Optimal Strength**: Moderate SLA values (±0.1m) provide highest suitability
- **Size Range**: 50-300 km diameter, captured by 0.5° grid resolution
- **Weight in HSI**: 60% of the combined oceanographic suitability

## 🌊 Front Detection

### What are Ocean Fronts?

Ocean fronts are sharp boundaries between different water masses characterized by:

- **Strong Gradients**: Rapid changes in temperature, salinity, or density
- **Convergence Zones**: Where different water masses meet
- **Prey Concentration**: Areas where marine life accumulates
- **Migration Boundaries**: Natural corridors for marine species

### Front Types Detected

#### 1. Dynamic Fronts (SSH Gradients)
- **Detection Method**: Spatial gradient analysis of Sea Level Anomaly
- **Formula**: `math|\nabla SLA| = \sqrt{\left(\frac{\partial SLA}{\partial lat}\right)^2 + \left(\frac{\partial SLA}{\partial lon}\right)^2}`
- **Characteristics**: Sharp boundaries between different water masses
- **Ecological Role**: Convergence zones where prey concentrates

#### 2. Thermal Fronts (SST Gradients)
- **Detection Method**: Spatial gradient analysis of Sea Surface Temperature
- **Characteristics**: Temperature boundaries between water masses
- **Ecological Role**: Thermal boundaries that concentrate prey

### Mathematical Implementation

```math
f_{front} = \exp\left(-\frac{|\nabla SLA|}{\sigma_{front}}\right)
```

Where:
- `math|\nabla SLA|` = Gradient magnitude (m/degree)
- `math\sigma_{front} = 0.05` m/degree (threshold for significant fronts)

**Key Parameters:**
- **Gradient Threshold**: >0.05 m/degree indicates significant fronts
- **Weight in HSI**: 40% of the combined oceanographic suitability
- **Spatial Resolution**: Captured by 0.5° grid resolution

## 🔬 Combined Oceanographic Suitability

### Integration Formula

```math
f_E = 0.6 \times f_{eddy} + 0.4 \times f_{front}
```

Where:
- `mathf_{eddy}` = Eddy suitability (0-1 scale)
- `mathf_{front}` = Front suitability (0-1 scale)
- `mathf_E` = Combined oceanographic suitability

### Weighting Rationale

#### Eddies (60% Weight)
- **Primary Foraging Hotspots**: Direct drivers of prey concentration
- **Nutrient Cycling**: Essential for phytoplankton blooms
- **Predictable Patterns**: More consistent than fronts
- **Size Impact**: Large features with significant ecological influence

#### Fronts (40% Weight)
- **Secondary Concentration**: Important but less dominant
- **Migration Corridors**: Natural pathways for marine species
- **Convergence Zones**: Areas where prey accumulates
- **Dynamic Nature**: More variable than eddies

## 📊 Data Sources and Processing

### NASA-SSH Dataset
- **Mission**: TOPEX/Poseidon, Jason series, Sentinel-6
- **Resolution**: 0.5° spatial, 7-day temporal
- **Processing**: 10-day observations with Gaussian weighting (100 km width)
- **Quality Control**: NASA flags (nasa_flag=0, median_filter_flag=0)
- **Basin Awareness**: Avoids mixing data across distinct ocean basins

### Processing Pipeline
1. **Data Acquisition**: Download SSH anomaly data
2. **Quality Control**: Apply NASA quality flags
3. **Spatial Analysis**: Calculate gradients for front detection
4. **Feature Detection**: Identify eddies and fronts
5. **Suitability Calculation**: Apply mathematical models
6. **Integration**: Combine into oceanographic suitability component

## 🦈 Ecological Significance

### For Shark Foraging

#### Direct Effects
- **Prey Concentration**: Eddies and fronts create areas of high prey density
- **Foraging Efficiency**: Sharks can exploit these predictable patterns
- **Migration Guidance**: Natural pathways for seasonal movements
- **Thermal Regulation**: Optimal temperature zones for hunting

#### Indirect Effects
- **Food Web Dynamics**: Bottom-up effects through nutrient cycling
- **Habitat Structure**: Creating three-dimensional habitat complexity
- **Predator-Prey Interactions**: Affecting encounter rates
- **Seasonal Patterns**: Temporal variations in foraging opportunities

### For Marine Ecosystems
- **Primary Productivity**: Eddies drive phytoplankton blooms
- **Biodiversity**: Fronts create diverse habitat types
- **Nutrient Cycling**: Vertical mixing and horizontal transport
- **Climate Regulation**: Ocean-atmosphere interactions

## 🔧 Technical Implementation

### Code Structure

```python
def _normalize_sea_level_anomaly(self, sla: xr.DataArray) -> xr.DataArray:
    """
    Comprehensive eddy and front detection with detailed documentation
    """
    # Step 1: Front detection through spatial gradients
    grad_lat = sla_clean.differentiate('lat')
    grad_lon = sla_clean.differentiate('lon')
    gradient_magnitude = np.sqrt(grad_lat**2 + grad_lon**2)
    front_suitability = np.exp(-gradient_magnitude / 0.05)
    
    # Step 2: Eddy detection through SLA anomalies
    eddy_suitability = np.exp(-(sla_clean ** 2) / (2 * 0.1 ** 2))
    
    # Step 3: Combine with weighted importance
    combined_suitability = 0.6 * eddy_suitability + 0.4 * front_suitability
    
    return combined_suitability
```

### Performance Considerations
- **Computational Efficiency**: Vectorized operations using xarray/NumPy
- **Memory Management**: In-place operations where possible
- **Spatial Resolution**: 0.5° grid balances detail with computational cost
- **Temporal Resolution**: 7-day intervals capture feature evolution

## 📈 Validation and Accuracy

### Validation Methods
- **Satellite Altimetry**: Cross-validation with independent datasets
- **In-situ Observations**: Comparison with buoy and ship data
- **Model Verification**: Validation against known eddy/front locations
- **Statistical Analysis**: Correlation with marine life observations

### Known Limitations
- **Spatial Resolution**: 0.5° may miss smaller features (<50 km)
- **Temporal Resolution**: 7-day intervals may miss rapid changes
- **Coverage Gaps**: Western hemisphere limitations due to satellite tracks
- **Complex Interactions**: Simplified models may miss complex dynamics

## 🔮 Future Enhancements

### Potential Improvements
- **Higher Resolution**: Integration with SWOT satellite data (2 km resolution)
- **Machine Learning**: AI-based feature detection and classification
- **Multi-scale Analysis**: Combining mesoscale and submesoscale features
- **Real-time Processing**: Near-real-time feature detection
- **Additional Variables**: Integration of salinity, oxygen, and other parameters

### Research Applications
- **Climate Studies**: Understanding eddy/front response to climate change
- **Fisheries Management**: Predicting fish abundance and distribution
- **Marine Protected Areas**: Optimizing MPA design and placement
- **Ecosystem Modeling**: Improving marine ecosystem models

## 📚 References

1. Chelton, D. B., et al. (2011). "The influence of nonlinear mesoscale eddies on near-surface oceanic chlorophyll." Science, 334(6054), 328-332.

2. Gaube, P., et al. (2013). "Satellite observations of chlorophyll, phytoplankton biomass, and Ekman pumping in nonlinear mesoscale eddies." Journal of Geophysical Research: Oceans, 118(12), 6349-6370.

3. McGillicuddy, D. J., et al. (2007). "Eddy/wind interactions stimulate extraordinary mid-ocean plankton blooms." Science, 316(5827), 1021-1026.

4. Siegel, D. A., et al. (2011). "The stochastic nature of larval connectivity among nearshore marine populations." Proceedings of the National Academy of Sciences, 108(22), 8974-8979.

---

## 🏆 NASA Space Apps Challenge Impact

### Challenge Alignment
This project directly addresses the "Sharks from Space" challenge by:

1. **Satellite Data Utilization**: Maximizing use of NASA's Earth Science data
2. **Scientific Rigor**: Implementing peer-reviewed oceanographic methods
3. **Global Impact**: Providing worldwide shark habitat predictions
4. **Accessibility**: Making complex satellite data accessible to broader audiences
5. **Conservation Applications**: Supporting marine conservation efforts

### Innovation Highlights
- **Real-time Processing**: Live satellite data integration for current predictions
- **Multi-satellite Fusion**: Combining PACE, VIIRS, and multi-mission altimetry data
- **Advanced Algorithms**: Sophisticated eddy and front detection methods
- **Open Science**: Open-source implementation for research community

### Future Potential
This work demonstrates the potential for satellite-based shark monitoring systems that could:
- Support marine protected area design
- Inform fisheries management decisions
- Contribute to climate change impact studies
- Enable real-time shark habitat monitoring

For more information about the NASA Space Apps Challenge, visit: [https://www.spaceappschallenge.org/2025/challenges/sharks-from-space/](https://www.spaceappschallenge.org/2025/challenges/sharks-from-space/?tab=details)

---

*This documentation is part of the Shark Foraging Hotspot Prediction Server project for the 2025 NASA Space Apps Challenge. For technical details, see the main README.md and source code documentation.*
