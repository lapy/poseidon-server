# POSEIDON: Shark Foraging Hotspot Prediction Server

**P**redictive **O**ceanographic **S**hark **E**cology & **I**n-situ **D**ata **O**bservation **N**etwork

A full-stack web application that predicts global shark foraging hotspots using NASA satellite data and a Habitat Suitability Index (HSI) model.

## 🚀 NASA Space Apps Challenge 2025

This project is part of the **2025 NASA Space Apps Challenge** - [**Sharks from Space**](https://www.spaceappschallenge.org/2025/challenges/sharks-from-space/?tab=details) challenge.

### Challenge Connection
- **Challenge Theme**: Sharks from Space
- **NASA Mission**: Earth Science Division
- **Data Sources**: NASA Earthdata Cloud (satellite observations)
- **Objective**: Leverage satellite data to understand and predict shark behavior and habitat suitability

### Project Alignment
Our solution directly addresses the challenge by:
- **Satellite Data Integration**: Using NASA's Earthdata Cloud for real-time oceanographic data
- **Shark Habitat Modeling**: Implementing scientifically rigorous HSI calculations
- **Global Coverage**: Providing worldwide shark foraging predictions
- **Interactive Visualization**: Making complex data accessible through web interfaces
- **Research Applications**: Supporting marine conservation and shark research efforts

## 🦈 Features

- **NASA Satellite Data Integration**: Fetches and processes real-time data from NASA's Earthdata Cloud
- **HSI Mathematical Model**: Implements habitat suitability calculations for different shark species
- **Interactive Web Interface**: Beautiful, responsive map visualization with Leaflet.js
- **Species-Specific Predictions**: Supports Great White Shark and Tiger Shark profiles
- **Data Caching**: Efficient local caching system to avoid redundant API calls
- **Real-time Visualization**: Dynamic heatmap and polygon overlays
- **Viewport Filtering**: Optional geographic filtering for faster processing of specific regions
- **Trophic Lag Implementation**: Accounts for ecological response times in predictions
- **Advanced Oceanographic Feature Detection**: Sophisticated eddy and front detection algorithms
- **Missing Data Handling**: Intelligent gap-filling using adjacent time periods
- **Interactive Map Controls**: Toggle between heatmap and polygon views, reset map view

## 🛠️ Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **earthaccess**: NASA Earthdata access library
- **xarray**: Multi-dimensional array processing
- **NumPy**: Numerical computing
- **SciPy**: Scientific computing

### Frontend
- **Leaflet.js**: Interactive map library
- **Vanilla JavaScript**: Modern ES6+ JavaScript
- **CSS3**: Responsive design with modern styling
- **HTML5**: Semantic markup

## 📊 Data Sources

The application uses four NASA satellite datasets with enhanced processing:

### 1. Phytoplankton/Chlorophyll-a
- **Mission/Instrument**: PACE (Plankton, Aerosol, Cloud, ocean Ecosystem) / OCI (Ocean Color Instrument)
- **Product**: Level-3 Binned Mapped Chlorophyll-a Concentration
- **Short Name**: `PACE_OCI_L3M_CHL`
- **Details**: Monthly composite data that provides stable "pasture" maps for trophic lag calculations. Serves as the foundational layer of the marine food web.

### 2. Sea Surface Height, Eddies, and Fronts
- **Mission/Instrument**: Multi-mission (TOPEX/Poseidon, Jason series, Sentinel-6)
- **Product**: NASA-SSH Simple Gridded Sea Surface Height from Standardized Reference Missions Only Version 1
- **Short Name**: `NASA_SSH_REF_SIMPLE_GRID_V1`
- **Details**: Provides Sea Surface Height Anomaly (SSHA) in meters on a 0.5° grid with 7-day temporal resolution. This dataset is the primary source for detecting mesoscale oceanographic features:

#### Eddy Detection:
- **Cyclonic Eddies** (negative SLA): Cold-core eddies that create upwelling, bringing nutrient-rich deep water to the surface, promoting phytoplankton blooms and prey aggregation
- **Anticyclonic Eddies** (positive SLA): Warm-core eddies that create downwelling, concentrating prey at depth and creating different foraging opportunities
- **Eddy Size**: Typically 50-300 km in diameter, captured by the 0.5° grid resolution
- **Optimal Strength**: Moderate SLA values (±0.1m) provide highest shark foraging suitability

#### Front Detection:
- **Ocean Fronts**: Sharp boundaries between different water masses identified by steep spatial gradients in SLA
- **Gradient Calculation**: Computed as `math\sqrt{\left(\frac{\partial SLA}{\partial lat}\right)^2 + \left(\frac{\partial SLA}{\partial lon}\right)^2}` to identify convergence zones
- **Front Suitability**: High gradients (>0.05 m/degree) indicate areas where prey concentrates
- **Thermal Fronts**: Additional fronts detected through SST gradients

#### Data Processing:
- **Temporal Resolution**: 7-day intervals with 10-day observation windows for temporal overlap
- **Spatial Averaging**: Gaussian weighted spatial averaging with 100 km width
- **Coordinate Conversion**: Automatic conversion from 0-360° to -180/180° longitude for global coverage
- **Quality Control**: NASA flags (nasa_flag=0) and source flags ensure data reliability
- **Orbit Error Reduction**: Applied OER correction reduces RMS variability by ~2.3 cm
- **Coverage**: Full global coverage across all hemispheres

### 3. Sea Surface Temperature (SST)
- **Mission/Instrument**: VIIRS NPP
- **Product**: VIIRS NPP Level-3 mapped Sea Surface Temperature (SST)
- **Short Name**: `VIIRSN_L3m_SST3`
- **Details**: Daily SST measurements using thermal infrared data at 750m resolution (at nadir). Provides high-resolution global coverage with quality-controlled temperature data for habitat suitability analysis.

### 4. Sea Surface Salinity (SSS)
- **Mission/Instrument**: Multi-mission (SMAP, SMOS, Aquarius)
- **Product**: Multi-Mission Optimally Interpolated Sea Surface Salinity Global Monthly Dataset V2
- **Short Name**: `OISSS_L4_multimission_monthly_v2`
- **Details**: Monthly composite salinity data at 0.25° resolution providing global coverage for habitat filtering. This dataset is critical for excluding areas where sharks cannot survive based on salinity tolerance levels.

#### Data Processing Pipeline:
All NASA satellite data goes through a streamlined processing pipeline:

**1. Data Fetching & Authentication:**
- Automatic NASA Earthdata authentication via .netrc or environment variables
- Intelligent search with temporal windows (7 days for SSH/SST, 90 days for salinity)
- Cloud-hosted data prioritization for faster downloads

**2. Quality Control:**
- **SSH**: NASA quality flags (nasa_flag=0), source flags, orbit error reduction
- **SST**: VIIRS quality flags (qual_sst ≤ 1), fill value filtering
- **Salinity**: Quality flag filtering, realistic range validation (0-40 psu)
- **Chlorophyll**: Fill value removal, non-negative value enforcement

**3. Coordinate Standardization:**
- Automatic longitude conversion from 0-360° to -180/180° for global compatibility
- Consistent coordinate sorting for proper interpolation
- Diagnostic logging for data range verification

**4. Regridding & Caching:**
- Linear interpolation to common 0.25° grid
- NetCDF caching for efficient reuse
- Automatic cache management and cleanup

## 🧮 HSI Model

The Habitat Suitability Index is calculated using the formula:

```math
H(x,y,t) = f_{sal}(S) \times (f_C(C')^{w_C} \times f_E(E')^{w_E} \times f_S(S)^{w_S})^{\frac{1}{w_C + w_E + w_S}}
```

Where:
- `mathf_{sal}(S)`: Binary salinity filter (1 for suitable salinity, 0 for unsuitable)
- `mathf_C`: Normalized chlorophyll concentration (food web foundation)
- `mathf_E`: Combined eddy and front suitability from sea level anomaly
- `mathf_S`: Gaussian temperature suitability (habitability filter)
- `mathw_C, w_E, w_S`: Species-specific weights

### Enhanced Processing Features:

#### Oceanographic Feature Detection:
- **Eddy Detection**: 
  - Gaussian normalization: `mathf_{eddy} = \exp\left(-\frac{E'^2}{2\sigma^2}\right)` where `math\sigma = 0.1m`
  - Captures both cyclonic (upwelling) and anticyclonic (downwelling) eddies
  - Optimal eddy strength provides highest shark foraging suitability
- **Front Detection**: 
  - Spatial gradient calculation: `math|\nabla SLA| = \sqrt{\left(\frac{\partial SLA}{\partial lat}\right)^2 + \left(\frac{\partial SLA}{\partial lon}\right)^2}`
  - Exponential front suitability: `mathf_{front} = \exp\left(-\frac{|\nabla SLA|}{\sigma_{front}}\right)` where `math\sigma_{front} = 0.05 \text{ m/degree}`
  - Identifies convergence zones where prey accumulates
- **Combined Oceanographic Suitability**: 
  - Weighted combination: `mathf_E = 0.6 \times f_{eddy} + 0.4 \times f_{front}`
  - Eddies (60%) and fronts (40%) both contribute to prey concentration

#### Advanced Data Processing:
- **Trophic Lag Implementation**: Uses lagged environmental data to account for ecological response times
- **Adjacent Temporal Merging**: Fetches data from ±7 days to maximize coverage and fill gaps
- **Data Quality Control**: Handles fill values, outliers, and unit conversions
- **Missing Data Handling**: Uses neutral sea level suitability (0.5) where data unavailable
- **Spatial Regridding**: Aligns all datasets to a common 0.25° global grid
- **Geographic Filtering**: Supports viewport-based processing for performance optimization
- **Salinity Habitat Filtering**: Binary filtering excludes areas where sharks cannot survive based on species-specific salinity tolerance ranges
- **Time-Insensitive Salinity**: Uses December 2022 salinity data (latest reliable OISSS L4 availability) since ocean salinity patterns are relatively stable
- **Preemptive Data Validation**: Ultra-fast failure by checking data availability before downloads, avoiding unnecessary processing

## 🚀 Quick Start

### Prerequisites

- Python 3.8+ (tested with Python 3.8, 3.9, 3.10, 3.11)
- NASA Earthdata account (free registration required)
- Internet connection for satellite data access
- 2GB+ available disk space for data caching

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd poseidon-server
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up NASA Earthdata authentication**
   ```bash
   python -c "import earthaccess; earthaccess.login()"
   ```
   Follow the prompts to authenticate with your NASA Earthdata credentials.
   
   **Alternative authentication methods:**
   
   **Option A: Using .netrc file (recommended for production)**
   ```bash
   echo "machine urs.earthdata.nasa.gov login <username> password <password>" >> ~/.netrc
   chmod 600 ~/.netrc
   ```
   
   **Option B: Using environment variables**
   ```bash
   export EARTHDATA_USERNAME="<username>"
   export EARTHDATA_PASSWORD="<password>"
   ```

4. **Start the backend server**
   ```bash
   cd backend
   python main.py
   ```

5. **Access the application**
   Open your browser and navigate to `http://localhost:8000`

## 📁 Project Structure

```
poseidon-server/
├── backend/
│   ├── main.py                 # FastAPI application entry point
│   ├── data/
│   │   └── nasa_data.py       # NASA data access and caching
│   ├── models/
│   │   └── hsi_model.py       # HSI mathematical model
│   ├── api/
│   │   └── routes/
│   │       └── hotspots.py    # API endpoints
│   └── utils/
│       └── geojson_converter.py # Data format conversion
├── frontend/
│   ├── index.html             # Main HTML page
│   ├── styles.css             # CSS styling
│   └── app.js                 # JavaScript application
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## 🔧 Configuration

### Shark Species Profiles

The application includes predefined profiles for three shark species:

#### Great White Shark
- Optimal Temperature: 18°C
- Temperature Tolerance: 5°C
- Temperature Lag: 7 days
- Chlorophyll Lag: 30 days
- Weights: Chlorophyll (0.4), Sea Level (0.3), Temperature (0.3)
- Salinity Range: 30.0-37.0 psu

#### Tiger Shark
- Optimal Temperature: 25°C
- Temperature Tolerance: 4°C
- Temperature Lag: 5 days
- Chlorophyll Lag: 21 days
- Weights: Chlorophyll (0.3), Sea Level (0.4), Temperature (0.3)
- Salinity Range: 30.0-37.0 psu

#### Bull Shark
- Optimal Temperature: 22°C
- Temperature Tolerance: 6°C
- Temperature Lag: 3 days
- Chlorophyll Lag: 14 days
- Weights: Chlorophyll (0.35), Sea Level (0.35), Temperature (0.3)
- Salinity Range: 0.5-35.0 psu (highly adaptable)

### Data Sources
All data sources provide global coverage:
- **Chlorophyll**: PACE OCI Level-3 Monthly Composite (PACE_OCI_L3M_CHL)
- **Sea Level**: NASA-SSH Simple Gridded L4 (NASA_SSH_REF_SIMPLE_GRID_V1, 7-day, 0.5° grid)
- **Temperature**: VIIRS NPP Level-3 SST (VIIRSN_L3m_SST3, daily, 750m resolution)
- **Salinity**: OISSS L4 Multi-Mission (OISSS_L4_multimission_monthly_v2, monthly, 0.25° grid)

### API Endpoints

**Core Endpoints:**
- `GET /api/hotspots` - Get HSI predictions with optional geographic filtering
  - Parameters: `target_date`, `shark_species`, `format`, `north`, `south`, `east`, `west`
  - Returns: GeoJSON or raw HSI data
- `GET /api/species` - Get available shark species profiles
- `GET /api/dataset-info` - Get NASA dataset information and configurations

**Data Overlay Endpoints:**
- `GET /api/chlorophyll-overlay` - Get chlorophyll concentration overlay
- `GET /api/oceanographic-overlay` - Get sea level anomaly/eddy overlay
- `GET /api/salinity-overlay` - Get sea surface salinity overlay

**Utility Endpoints:**
- `GET /health` - Health check endpoint
- `POST /api/authenticate` - NASA Earthdata authentication
- `POST /api/cleanup` - Clean up temporary cache files
- `GET /api/sea-level-availability` - Check SSH data availability for date range
- `GET /api/along-track-data` - Get high-resolution along-track SSH data

## 🗺️ Usage

1. **Select Species**: Choose from Great White Shark, Tiger Shark, or Bull Shark
2. **Pick Date**: Select a target date for prediction
3. **Adjust Threshold**: Set HSI threshold for visualization (0.0-1.0)
4. **Optional - Viewport Filtering**: Enable "Limit to Map View" to process only the visible map area for faster performance
5. **Generate Prediction**: Click "Predict Hotspots" to run the model
6. **Explore Results**: View the interactive map with hotspots
7. **Toggle Views**: Switch between polygon and heatmap visualizations using map controls
8. **View Details**: Click on hotspots to see detailed HSI values and coordinates

## 🧹 Code Quality & Performance

### Recent Improvements (2025)
**Data Processing Enhancements:**
- ✅ Fixed SSH longitude coverage issue (0-360° to -180/180° conversion)
- ✅ Removed 400+ lines of unused/redundant code (29% reduction in nasa_data.py)
- ✅ Simplified API - removed wrapper functions and unused parameters
- ✅ Improved diagnostic logging for data coverage verification
- ✅ Streamlined data fetching pipeline

**Code Cleanup:**
- Removed unused basin connection logic (266 lines of data)
- Removed redundant `download_combined_pass_data()` wrapper
- Removed unused helper functions (`_merge_datasets`, `_check_data_availability`, etc.)
- Cleaned up imports and eliminated unused dependencies
- Zero linter errors across all modules

**Performance:**
- Efficient NetCDF caching reduces redundant API calls
- 5-minute cache for overlay data reuse
- Automatic temporary file cleanup
- Optimized data fetching with intelligent search windows

### Code Statistics
| Module | Lines | Functions | Purpose |
|--------|-------|-----------|---------|
| `nasa_data.py` | 979 | 24 | NASA data access & processing |
| `hotspots.py` | 709 | 15 | API route handlers |
| `hsi_model.py` | 525 | 12 | HSI calculations |
| `geojson_converter.py` | 310 | 5 | Data format conversion |

## 🔬 Model Parameters

The HSI model uses species-specific parameters that can be adjusted:

- **`mathS_{opt}`**: Optimal temperature for the species
- **`math\sigma_S`**: Temperature tolerance (standard deviation)
- **`mathT_{lag}`**: Temperature lag in days
- **`mathC_{lag}`**: Chlorophyll lag in days
- **Weights**: Relative importance of each environmental factor

### Trophic Lag Implementation

The model implements trophic lag to account for ecological response times in marine ecosystems. This is crucial for accurate habitat suitability predictions because:

#### **Temperature Lag (5-7 days)**
- **Physiological Response**: Sharks are ectothermic (cold-blooded) and respond to temperature changes through behavioral adaptations rather than immediate physiological changes
- **Behavioral Migration**: Temperature changes trigger migration patterns as sharks seek optimal thermal habitats
- **Metabolic Adjustment**: Changes in prey metabolism and distribution lag behind temperature changes
- **Implementation**: Uses SST data from 5-7 days prior to the prediction date for Great White Sharks (7 days) and Tiger Sharks (5 days)

#### **Chlorophyll Lag (21-30 days)**
- **Food Web Dynamics**: Represents the time for bottom-up effects to propagate through the marine food web

**Trophic Cascade Timeline:**
```
Day 0:    Phytoplankton bloom (chlorophyll increase)
Day 3-7:  Zooplankton population growth
Day 7-14: Small fish aggregation and feeding
Day 14-21: Larger fish (shark prey) migration to area
Day 21-30: Sharks arrive to exploit prey concentrations
```

- **Implementation**: Uses chlorophyll data from 21-30 days prior (Tiger Sharks: 21 days, Great White Sharks: 30 days)

#### **Why Sea Level Anomaly Has No Lag**
- **Immediate Physical Effect**: Ocean eddies and fronts create immediate changes in prey distribution
- **Direct Impact**: Mesoscale features affect prey aggregation and shark foraging behavior within hours to days
- **Current Data**: Sea level anomaly data is used from the prediction date itself

#### **Mathematical Implementation**
The lag system works by:

```python
# Calculate lagged dates for each species
chlorophyll_lag_date = target_date - timedelta(days=profile.c_lag)
temperature_lag_date = target_date - timedelta(days=profile.t_lag)

# Fetch data from lagged dates with adjacent time periods
lagged_chlorophyll_data = get_data_for_date_with_adjacent(chlorophyll_lag_date)
lagged_sst_data = get_data_for_date_with_adjacent(temperature_lag_date)

# Use lagged data in HSI calculation if available
if lagged_chlorophyll_data is not None:
    f_c = normalize_chlorophyll(lagged_chlorophyll_data['chlorophyll'])
else:
    f_c = normalize_chlorophyll(current_chlorophyll_data['chlorophyll'])
```

#### **Fallback Strategy**
When lagged data is unavailable:
- **Graceful Degradation**: Falls back to current date data
- **Adjacent Time Merging**: Uses ±7 days of data around the lagged date to maximize coverage
- **Quality Assurance**: Logs which data sources are being used for transparency
- **Performance Optimization**: Caches both current and lagged data for efficient retrieval

#### **Scientific Basis**
This lag implementation is based on:
- **Marine Ecology Research**: Studies on food web dynamics and predator-prey relationships
- **Satellite Data Analysis**: Empirical observations of temporal correlations between environmental variables and marine life distribution
- **Species-Specific Behavior**: Different shark species have varying response times based on their ecology and physiology
- **Ecological Modeling**: Incorporates trophic cascade effects and bottom-up control mechanisms

#### **NASA Challenge Significance**
The trophic lag implementation demonstrates sophisticated use of satellite data for ecological modeling:
- **Multi-temporal Analysis**: Leverages historical satellite data to predict future conditions
- **Biological Realism**: Incorporates real ecological processes rather than simple correlation
- **Species-Specific Adaptation**: Different lag times for different shark species reflect their unique ecology
- **Predictive Power**: Enables forecasting of shark habitat suitability based on past environmental conditions

## 📖 Additional Documentation

- **[NASA_CHALLENGE_SUBMISSION.md](NASA_CHALLENGE_SUBMISSION.md)**: Complete NASA Space Apps Challenge 2025 submission details
- **[OCEANOGRAPHIC_FEATURES.md](OCEANOGRAPHIC_FEATURES.md)**: Comprehensive guide to eddy and front detection
- **API Documentation**: Available at `/api/datasets` endpoint
- **Model Parameters**: Detailed in shark species profiles section above

## 🏆 NASA Space Apps Challenge Submission

### Project Overview
This project demonstrates how NASA satellite data can be leveraged to understand and predict shark foraging behavior on a global scale. By combining multiple satellite datasets and implementing sophisticated oceanographic feature detection, we provide a comprehensive tool for marine conservation and research.

### Key Innovations
1. **Multi-Satellite Integration**: Combining PACE, VIIRS, and multi-mission altimetry data
2. **Advanced Oceanographic Feature Detection**: Real-time eddy and front identification
3. **Species-Specific Modeling**: Tailored HSI calculations for different shark species
4. **Global Accessibility**: Web-based interface for researchers and conservationists worldwide

### Impact and Applications
- **Marine Conservation**: Identifying critical shark habitats for protection
- **Fisheries Management**: Supporting sustainable fishing practices
- **Climate Research**: Understanding shark response to oceanographic changes
- **Public Education**: Making satellite data accessible to broader audiences

### NASA Data Utilization
Our project maximizes the use of NASA's Earth Science data by:
- **Real-time Processing**: Live satellite data integration
- **Multi-scale Analysis**: From mesoscale eddies to global patterns
- **Quality Assurance**: Implementing NASA-recommended data processing standards
- **Open Science**: Providing open-source tools for the research community

For more information about the NASA Space Apps Challenge, visit: [https://www.spaceappschallenge.org/2025/challenges/sharks-from-space/](https://www.spaceappschallenge.org/2025/challenges/sharks-from-space/?tab=details)

## 📈 Performance

- **Data Caching**: Downloaded data is cached locally to improve performance
- **Grid Resolution**: 0.25° global grid for optimal balance of detail and performance
- **Lazy Loading**: Data is fetched only when needed
- **Efficient Visualization**: Optimized GeoJSON conversion for map rendering
- **Viewport Filtering**: Optional geographic filtering to process only visible map areas
- **Adjacent Temporal Merging**: Intelligent gap-filling using ±7 days of satellite data
- **Memory Management**: Efficient handling of large satellite datasets with cleanup routines
- **Progressive Loading**: Data is processed and displayed incrementally for better user experience

## 🛡️ Security

- **NASA Authentication**: Secure authentication with NASA Earthdata
- **Input Validation**: Comprehensive input validation and error handling
- **CORS Configuration**: Configurable Cross-Origin Resource Sharing

## 🔍 Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Ensure you have a valid NASA Earthdata account
   - Run `python -c "import earthaccess; earthaccess.login()"` to authenticate
   - Check your internet connection
   - Verify credentials in `.netrc` file or environment variables

2. **Data Not Found**
   - Some dates may not have available satellite data
   - Try dates within the last 2-3 years
   - Check NASA data availability using `/api/sea-level-availability` endpoint
   - Use adjacent time periods (±7 days) for better coverage

3. **Performance Issues**
   - Enable viewport filtering to process only visible map area
   - Clear the data cache if needed: `rm -rf data_cache/*`
   - Check available system memory (2GB+ recommended)
   - Use the cleanup endpoint: `POST /api/cleanup`

4. **Frontend Connection Issues**
   - Ensure backend is running on `http://localhost:8000`
   - Check browser console for CORS errors
   - Verify API endpoints are accessible

5. **Missing Sea Level Data**
   - NASA-SSH has limited coverage in western hemisphere
   - The system automatically uses adjacent time periods (±7 days) to fill gaps
   - Neutral suitability (0.5) is used where data is unavailable

### Debug Mode

Enable debug logging by setting the log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Data Cache Management

- Cache directory: `data_cache/` (configurable via `CACHE_DIR` environment variable)
- Cache files are automatically created and reused
- Temporary files are cleaned up after processing
- Use `POST /api/cleanup` to manually clean temporary files

## 📚 Resources

For a complete list of datasets, libraries, and tools used in this project, see [RESOURCES.md](RESOURCES.md).

**Quick Links:**
- [NASA Earthdata](https://www.earthdata.nasa.gov/)
- [PO.DAAC Data Portal](https://podaac.jpl.nasa.gov/)
- [earthaccess Library](https://earthaccess.readthedocs.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Leaflet.js](https://leafletjs.com/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 🤖 AI Assistance Disclosure

This project was developed with assistance from AI tools (Claude by Anthropic) for:
- Code development and optimization
- Documentation writing
- Architecture design and refactoring
- Debugging and problem-solving

All scientific concepts, methodologies, and NASA data integration were implemented based on established research and official documentation. The AI served as a development assistant while the project architect maintained oversight of all technical decisions and implementations.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **NASA**: For providing free access to satellite data
- **earthaccess**: For simplifying NASA data access
- **Leaflet**: For the excellent mapping library
- **FastAPI**: For the modern Python web framework

## 📞 Support

For questions, issues, or contributions, please:

1. Check the troubleshooting section
2. Search existing issues
3. Create a new issue with detailed information
4. Contact the development team

## 🔮 Future Enhancements

- [x] Salinity-based habitat filtering
- [x] Bull shark species profile
- [ ] Additional shark species profiles
- [ ] Real-time data streaming
- [ ] Machine learning model integration
- [ ] Mobile app development
- [ ] Advanced visualization options
- [ ] Data export functionality
- [ ] User authentication and saved predictions
- [ ] Integration with shark tracking data (OCEARCH)

---

**Note**: This application is for research and educational purposes. Always verify predictions with actual field data and consult marine biologists for scientific applications.
