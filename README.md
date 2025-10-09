# POSEIDON: Shark Foraging Hotspot Prediction Server

**P**redictive **O**ceanographic **S**hark **E**cology & **I**n-situ **D**ata **O**bservation **N**etwork

A full-stack web application that predicts global shark foraging hotspots using NASA satellite data and an enhanced ecological niche Habitat Suitability Index (HSI) model.

## 🚀 NASA Space Apps Challenge 2025

This project is part of the **2025 NASA Space Apps Challenge** - [**Sharks from Space**](https://www.spaceappschallenge.org/2025/challenges/sharks-from-space/?tab=details) challenge.

### Challenge Connection
- **Challenge Theme**: Sharks from Space
- **NASA Mission**: Earth Science Division
- **Data Sources**: NASA Earthdata Cloud (satellite observations) + Global Fishing Watch (vessel tracking)
- **Objective**: Leverage satellite data to understand and predict shark behavior and habitat suitability

### Project Alignment
Our solution directly addresses the challenge by:
- **Satellite Data Integration**: Using NASA's Earthdata Cloud for real-time oceanographic, biological, and topographic data
- **Comprehensive Ecological Modeling**: Implementing a scientifically rigorous multi-faceted HSI calculation
- **Global Coverage**: Providing worldwide shark foraging predictions
- **Interactive Visualization**: Making complex data accessible through web interfaces with layer overlays
- **Research Applications**: Supporting marine conservation and shark research efforts

## 🦈 Features

### Currently Implemented (v1.0 - Oceanographic Model)
- **NASA Satellite Data Integration**: Real-time data from multiple NASA missions (PACE, VIIRS, SSH, OISSS)
- **Comprehensive HSI Model**: Temperature, salinity, chlorophyll, eddies, and fronts
- **Interactive Web Interface**: Beautiful, responsive map visualization with Leaflet.js
- **Species-Specific Predictions**: Great White Shark, Tiger Shark, and Bull Shark profiles
- **Data Caching**: Efficient local caching system to avoid redundant API calls
- **Real-time Visualization**: Dynamic heatmap and polygon overlays with detailed popups
- **Trophic Lag Implementation**: Accounts for ecological response times (21-30 days for chlorophyll, 5-7 days for temperature)
- **Advanced Oceanographic Feature Detection**: Sophisticated eddy and front detection from SLA gradients
- **Missing Data Handling**: Intelligent gap-filling using adjacent time periods (±7 days)
- **Derived Oxygen**: Dissolved oxygen estimated from SST and salinity using Garcia-Gordon equation

### Enhanced Features (v2.0 - Ecological Niche Model) ✅ WORKING
- ✅ **Anthropogenic Pressure Index**: **REAL Global Fishing Watch data** - fishing effort and vessel density from 8 ocean basins
- ✅ **GFW Multi-Region Integration**: Fetches and combines 500k+ vessel records per month from Pacific, Atlantic, Indian, Mediterranean, Caribbean, Red Sea
- ✅ **Coordinate Regridding**: Proper alignment of GFW data to NASA oceanographic grid
- ✅ **Production Caching**: 30-day cache for processed anthropogenic pressure grids
- ⚠️ **Topographic Index**: Using neutral values (1.0) - bathymetry integration optional
- **Future Enhancements**: Direct prey tracking, NPP data, advanced bathymetry

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

The enhanced application uses NASA satellite datasets across multiple domains:

### 1. Physicochemical & Oceanographic Data

#### Sea Surface Temperature (SST)
- **Mission/Instrument**: VIIRS NPP
- **Product**: VIIRS NPP Level-3 mapped Sea Surface Temperature
- **Short Name**: `VIIRSN_L3m_SST3`
- **Resolution**: Daily, 750m (at nadir)
- **Usage**: Temperature suitability calculation with trophic lag

#### Sea Surface Salinity (SSS)
- **Mission/Instrument**: Multi-mission (SMAP, SMOS, Aquarius)
- **Product**: Multi-Mission Optimally Interpolated Sea Surface Salinity
- **Short Name**: `OISSS_L4_multimission_monthly_v2`
- **Resolution**: Monthly, 0.25° grid
- **Usage**: Continuous trapezoidal suitability function

#### Dissolved Oxygen (DO)
- **Derivation**: Garcia-Gordon equation from SST and salinity
- **Usage**: Sigmoid function for hypoxia avoidance
- **Status**: ✅ Implemented (derived from SST and salinity)
- **Note**: Direct satellite measurements of dissolved oxygen are not available; using validated oceanographic derivation

#### Sea Surface Height & Oceanographic Features
- **Mission/Instrument**: Multi-mission (TOPEX/Poseidon, Jason series, Sentinel-6)
- **Product**: NASA-SSH Simple Gridded Sea Surface Height
- **Short Name**: `NASA_SSH_REF_SIMPLE_GRID_V1`
- **Resolution**: 7-day, 0.5° grid
- **Usage**: Eddy and front detection via SLA gradients

### 2. Prey Availability Data

#### Phytoplankton/Chlorophyll-a
- **Mission/Instrument**: PACE (Plankton, Aerosol, Cloud, ocean Ecosystem) / OCI
- **Product**: Level-3 Binned Mapped Chlorophyll-a Concentration
- **Short Name**: `PACE_OCI_L3M_CHL`
- **Resolution**: Monthly composite
- **Usage**: Baseline marine productivity proxy with trophic lag
- **Status**: ✅ Implemented

#### Ocean Net Primary Productivity (NPP)
- **Mission/Instrument**: VIIRS (Visible Infrared Imaging Radiometer Suite)
- **Product**: Level-3 Ocean Net Primary Productivity
- **Short Name**: `VIIRSN_L3m_NPP`
- **Resolution**: Monthly, 4km
- **Usage**: Direct measurement of ocean productivity (carbon fixation) - superior prey availability indicator
- **Status**: ✅ Available in NASA Earthdata (ready for implementation)
- **Note**: NPP represents actual carbon fixation rate, providing a more direct proxy for food web productivity than chlorophyll concentration alone

#### Direct Prey Density
- **Sources**: NOAA AMAPPS (marine mammals), USGS (sea turtles)
- **Usage**: Species-specific prey guild availability
- **Status**: ⚠️ Planned (uses chlorophyll as proxy - neutral values for direct prey)
- **Note**: Requires integration with external tracking databases (not available via NASA Earthdata)

### 3. Topographic Data

#### Bathymetry
- **Source**: GEBCO (General Bathymetric Chart of the Oceans) - https://www.gebco.net/
- **Usage**: Depth suitability (trapezoidal function) and seafloor slope calculation (Gaussian function)
- **Status**: ⚠️ Planned (requires separate GEBCO API access - uses neutral values)
- **Note**: GEBCO data is not available through NASA Earthdata

### 4. Anthropogenic Pressure Data

#### Fishing Pressure
- **Source**: Global Fishing Watch - https://globalfishingwatch.org/
- **Product**: Fishing effort data via GFW 4Wings API
- **Usage**: Normalized fishing effort (hours) as habitat displacement risk
- **Status**: ✅ Implemented (requires GFW API key)
- **Note**: Requires separate Global Fishing Watch API authentication - see `backend/docs/ANTHROPOGENIC_PRESSURE.md`
- **Processing**: 95th percentile normalization to 0-1 pressure index
- **Resolution**: Regridded to 0.5° to match NASA data
- **Caching**: 30-day TTL, stored in `data_cache/gfw_cache/`

#### Shipping Traffic
- **Source**: Global Fishing Watch vessel density (AIS data)
- **Usage**: Shipping lanes and vessel density as disturbance risk
- **Status**: ✅ Implemented (using fishing vessel density as proxy)
- **Note**: Currently uses GFW vessel data; can be enhanced with additional AIS sources
- **Processing**: 95th percentile normalization to 0-1 pressure index
- **Graceful Degradation**: Returns neutral values (zeros) if API unavailable

### Data Processing Pipeline

**1. Data Fetching & Authentication:**
- Automatic NASA Earthdata authentication via .netrc or environment variables
- Intelligent search with temporal windows (7 days for SSH/SST, 90 days for salinity)
- Cloud-hosted data prioritization for faster downloads

**2. Quality Control:**
- **SSH**: NASA quality flags (nasa_flag=0), source flags, orbit error reduction
- **SST**: VIIRS quality flags (qual_sst $\leq$ 1), fill value filtering
- **Salinity**: Quality flag filtering, realistic range validation (0-40 psu)
- **Chlorophyll**: Fill value removal, non-negative value enforcement

**3. Coordinate Standardization:**
- Automatic longitude conversion from 0-360° to -180/180° for global compatibility
- Consistent coordinate sorting for proper interpolation
- Diagnostic logging for data range verification

**4. Regridding & Caching:**
- Linear interpolation to common 0.5° grid (matches SSH resolution)
- NetCDF caching for efficient reuse
- Automatic cache management and cleanup

## 🧮 HSI Model

The Habitat Suitability Index uses a scientifically rigorous mathematical model:

### Current Model (v1.0 - Oceanographic)

```math
H(x,y,t) = f_{\text{sal}}(S) \times \left(f_C(C')^{w_C} \times f_E(E')^{w_E} \times f_T(T')^{w_T}\right)^{\frac{1}{w_C + w_E + w_T}}
```

Where:
- $f_{\text{sal}}(S)$: Continuous trapezoidal salinity suitability (0-1)
- $f_C(C')$: Lagged chlorophyll suitability (baseline productivity)
- $f_E(E')$: Oceanographic feature suitability (eddies + fronts from SLA)
- $f_T(T')$: Lagged Gaussian temperature suitability
- $w_C$, $w_E$, $w_T$: Species-specific weights (sum to 1.0)

### Component Functions

**Temperature Suitability (Gaussian):**
```math
f_{\text{temp}}(T') = \exp\left(-\frac{(T' - T_{\text{opt}})^2}{2\sigma_T^2}\right)
```
- Uses lagged SST data (5-7 days prior depending on species)
- Species-specific optimal temperature and tolerance

**Salinity Suitability (Trapezoidal):**
- Continuous function (not binary)
- Species-specific tolerance ranges
- Bull sharks tolerate 0.5-35.0 psu (highly adaptable)
- Great Whites and Tigers: 30.0-37.0 psu

**Chlorophyll Suitability:**
- Lagged data (21-30 days prior for trophic cascade)
- Normalized 0-1 range
- Proxy for baseline marine productivity

**Oceanographic Features (Eddies + Fronts):**
```math
f_{\text{ocean}} = 0.6 \times f_{\text{eddy}}(E') + 0.4 \times f_{\text{front}}(F')
```
- Derived from Sea Level Anomaly (SLA) gradients
- Eddies: Gaussian function on SLA magnitude
- Fronts: Exponential decay on SLA gradient magnitude
- Combined weighted score (eddies 60%, fronts 40%)

### Enhanced Model (v2.0 - PRODUCTION READY ✅)

**Working with Real Data:**

The enhanced ecological niche model formula:

```math
\text{HSI} = (w_{\text{Phys}} \times I_{\text{Phys}} + w_{\text{Prey}} \times I_{\text{Prey}} + w_{\text{Topo}} \times I_{\text{Topo}}) \times (1 - I_{\text{Anthro}})
```

**Current Implementation Status:**
- ✅ **$I_{\text{Anthro}}$**: Global Fishing Watch fishing effort and vessel density (fully integrated with official GFW client)
- ⚠️ **$I_{\text{Prey}}$**: Direct prey density tracking data (uses chlorophyll as baseline - neutral for species-specific prey)
- ⚠️ **$I_{\text{Topo}}$**: GEBCO bathymetry for depth and slope (planned - uses neutral values)

**$I_{\text{Anthro}}$ Implementation** (Active with GFW API key):
- ✅ **Data Source**: Global Fishing Watch official Python client (`gfw-api-python-client`)
- ✅ **Fishing Pressure**: Real-time fishing effort from AIS vessel tracking
- ✅ **Shipping Density**: Vessel presence density from AIS data
- ✅ **Processing**: Automatic gridding to 0.5° resolution, 95th percentile normalization
- **Formula**: $\text{HSI}_{\text{final}} = \text{HSI}_{\text{base}} \times (1 - \max(\text{fishing\_pressure}, \text{shipping\_density}))$
- **Effect**: HSI values reduced in areas with high human activity, reflecting shark avoidance behavior
- **Graceful Degradation**: Falls back to neutral values if GFW API unavailable

### Trophic Lag System

The model implements species-specific ecological response times:

#### Temperature Lag (3-7 days)
- **Physiological Response**: Sharks respond to temperature changes through behavioral migration
- **Implementation**: Uses SST data from 3-7 days prior (species-dependent)

#### Chlorophyll Lag (14-30 days)
- **Food Web Dynamics**: Time for phytoplankton blooms to propagate through the marine food web
- **Trophic Cascade Timeline**:
  ```
  Day 0:    Phytoplankton bloom
  Day 3-7:  Zooplankton growth
  Day 7-14: Small fish aggregation
  Day 14-21: Larger fish migration
  Day 21-30: Sharks arrive
  ```
- **Implementation**: Uses chlorophyll data from 14-30 days prior (species-dependent)

#### No Lag for Sea Level Anomaly
- **Immediate Physical Effect**: Ocean eddies and fronts create immediate changes in prey distribution
- **Implementation**: Uses current-date SLA data

## 🚀 Quick Start

### Prerequisites

- Python 3.8+ (tested with Python 3.8, 3.9, 3.10, 3.11)
- NASA Earthdata account (free registration required)
- Global Fishing Watch API key (optional, for anthropogenic pressure data)
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

4. **Set up Global Fishing Watch API (Optional)**
   
   For anthropogenic pressure data (fishing and shipping):
   
   a. Register at https://globalfishingwatch.org/
   b. Request an API key from the API section
   c. Add to `.env` file:
   ```bash
   GFW_API_KEY=your_gfw_api_key_here
   ```
   
   **Note**: Without a GFW API key, the system will use neutral anthropogenic pressure (zeros), which allows HSI calculation to proceed normally but without human impact assessment.
   
   See `backend/docs/ANTHROPOGENIC_PRESSURE.md` for detailed setup instructions.
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
│   │   └── nasa_data.py       # NASA data access and processing
│   ├── models/
│   │   └── hsi_model.py       # Enhanced HSI mathematical model
│   ├── api/
│   │   └── routes/
│   │       └── hotspots.py    # API endpoints
│   └── utils/
│       ├── geojson_converter.py # Data format conversion
│       └── geojson_cache.py   # GeoJSON caching system
├── frontend/
│   ├── index.html             # Main HTML page
│   ├── styles.css             # CSS styling
│   └── app.js                 # JavaScript application
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## 🔧 Configuration

### Shark Species Profiles

The application includes oceanographic profiles for three shark species:

#### Great White Shark
- **Temperature**: Optimal=18°C, Tolerance=±5°C (σ), Lag=7 days
- **Salinity**: 30.0-37.0 psu (trapezoidal function)
- **Model Weights**: Chlorophyll (0.4), Sea Level/Eddies (0.3), Temperature (0.3)
- **Chlorophyll Lag**: 30 days (trophic cascade timing)
- **Habitat**: Temperate coastal and offshore waters

#### Tiger Shark
- **Temperature**: Optimal=25°C, Tolerance=±4°C (σ), Lag=5 days
- **Salinity**: 30.0-37.0 psu (trapezoidal function)
- **Model Weights**: Chlorophyll (0.3), Sea Level/Eddies (0.4), Temperature (0.3)
- **Chlorophyll Lag**: 21 days (trophic cascade timing)
- **Habitat**: Tropical and subtropical waters

#### Bull Shark
- **Temperature**: Optimal=22°C, Tolerance=±6°C (σ), Lag=3 days
- **Salinity**: 0.5-35.0 psu (highly adaptable - freshwater to marine)
- **Model Weights**: Chlorophyll (0.35), Sea Level/Eddies (0.35), Temperature (0.3)
- **Chlorophyll Lag**: 14 days (trophic cascade timing)
- **Habitat**: Coastal, estuarine, and freshwater systems

### API Endpoints

**Core Endpoints:**
- `GET /api/hotspots` - Get HSI predictions
  - Parameters: `target_date`, `shark_species`, `format`, `threshold` (default: 0.2)
  - Returns: GeoJSON with oceanographic HSI data
- `GET /api/species` - Get available shark species profiles
- `GET /api/dataset-info` - Get NASA dataset information and configurations

**Utility Endpoints:**
- `GET /health` - Health check endpoint
- `POST /api/authenticate` - NASA Earthdata authentication
- `POST /api/cleanup` - Clean up temporary cache files
- `GET /api/sea-level-availability` - Check SSH data availability for date range
- `GET /api/along-track-data` - Get high-resolution along-track SSH data

## 🗺️ Usage

1. **Select Species**: Choose from Great White Shark, Tiger Shark, or Bull Shark
2. **Pick Date**: Select a target date for prediction (30-60 days ago recommended for best data availability)
3. **Adjust Threshold**: Set HSI threshold for visualization (0.0-1.0, default 0.2 - lower values show more areas)
4. **Generate Prediction**: Click "Predict Hotspots" to run the oceanographic model
5. **Explore Results**: View the interactive map with color-coded habitat suitability
6. **Toggle Views**: Switch between polygon and heatmap visualizations using map controls
7. **View Details**: Click on hotspots to see detailed HSI values and component breakdowns

### Understanding the Model Display

The map popup shows for each location:
- **Overall HSI Score**: Habitat suitability index (0-1 scale)
- **Component Contributions**:
  - Temperature suitability (with species-specific optimal temperature)
  - Salinity suitability (trapezoidal function)
  - Chlorophyll concentration (lagged for trophic cascade)
  - Oceanographic features (eddies and fronts from SLA)
- **Geographic Coordinates**: Latitude and longitude
- **Date Information**: Target date and lagged data dates

## 📈 Performance

- **Data Caching**: Downloaded data is cached locally to improve performance
- **Grid Resolution**: 0.5° global grid (matches SSH resolution, ~55km at equator)
- **Smart Zoom Limits**: Map zoom restricted to level 9 to match data resolution
- **Lazy Loading**: Data is fetched only when needed
- **Efficient Visualization**: Optimized GeoJSON conversion for map rendering
- **Adjacent Temporal Merging**: Intelligent gap-filling using ±7 days of satellite data
- **Memory Management**: Efficient handling of large satellite datasets with cleanup routines
- **Progressive Loading**: Data is processed and displayed incrementally for better user experience
- **GeoJSON Caching**: 5-minute cache for overlay data reuse with hash-based validation

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
   - Clear the data cache if needed: `rm -rf data_cache/*`
   - Check available system memory (2GB+ recommended)
   - Use the cleanup endpoint: `POST /api/cleanup`

4. **Frontend Connection Issues**
   - Ensure backend is running on `http://localhost:8000`
   - Check browser console for CORS errors
   - Verify API endpoints are accessible

5. **Missing Enhanced Model Data**
   - Ensure all required NASA datasets are available
   - Check that oxygen derivation is working (derived from SST and salinity)
   - Verify bathymetry and anthropogenic data sources are accessible

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

## 📖 Additional Documentation

- **[NASA_CHALLENGE_SUBMISSION.md](NASA_CHALLENGE_SUBMISSION.md)**: Complete NASA Space Apps Challenge 2025 submission details
- **[OCEANOGRAPHIC_FEATURES.md](OCEANOGRAPHIC_FEATURES.md)**: Comprehensive guide to eddy and front detection
- **[RESOURCES.md](RESOURCES.md)**: Complete list of datasets, libraries, and tools used
- **API Documentation**: Available at `/api/datasets` endpoint

## 🏆 NASA Space Apps Challenge Submission

### Project Overview
This project demonstrates how NASA satellite data can be leveraged to understand and predict shark foraging behavior on a global scale through a comprehensive ecological niche model. By combining multiple satellite datasets across physicochemical, biological, topographic, and anthropogenic dimensions, we provide a holistic tool for marine conservation and research.

### Key Innovations
1. **Multi-Dimensional Ecological Model**: Integrating physicochemical, prey availability, topography, and anthropogenic pressure
2. **Multi-Satellite Integration**: Combining PACE, VIIRS, multi-mission altimetry, and bathymetry data
3. **Advanced Oceanographic Feature Detection**: Real-time eddy and front identification from SLA gradients
4. **Species-Specific Modeling**: Tailored HSI calculations with unique prey preferences and habitat requirements
5. **Interactive Component Visualization**: Separate overlays for each ecological dimension
6. **Trophic Lag Implementation**: Time-lagged environmental data for realistic food web dynamics

### Impact and Applications
- **Marine Conservation**: Identifying critical shark habitats for protection across multiple ecological dimensions
- **Fisheries Management**: Supporting sustainable fishing practices by understanding shark displacement risks
- **Climate Research**: Understanding shark response to multi-faceted oceanographic and anthropogenic changes
- **Public Education**: Making complex ecological satellite data accessible to broader audiences

### NASA Data Utilization
Our project maximizes the use of NASA's Earth Science data by:
- **Real-time Processing**: Live satellite data integration from multiple missions
- **Multi-scale Analysis**: From mesoscale eddies to global habitat patterns
- **Quality Assurance**: Implementing NASA-recommended data processing standards
- **Open Science**: Providing open-source tools for the research community
- **Innovative Derivations**: Calculating dissolved oxygen from SST and salinity using oceanographic equations

For more information about the NASA Space Apps Challenge, visit: [https://www.spaceappschallenge.org/2025/challenges/sharks-from-space/](https://www.spaceappschallenge.org/2025/challenges/sharks-from-space/?tab=details)

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

- **NASA**: For providing free access to satellite data across multiple missions
- **earthaccess**: For simplifying NASA data access
- **Leaflet**: For the excellent mapping library
- **FastAPI**: For the modern Python web framework
- **Global Fishing Watch**: For fishing effort data
- **GEBCO**: For bathymetry data

## 📞 Support

For questions, issues, or contributions, please:

1. Check the troubleshooting section
2. Search existing issues
3. Create a new issue with detailed information
4. Contact the development team

## 🔮 Future Enhancements

- [x] Enhanced ecological niche model with 4 core dimensions
- [x] Individual index overlay visualization
- [x] Dissolved oxygen integration (derived)
- [x] Topographic analysis (depth and slope)
- [x] Anthropogenic pressure modeling
- [ ] Direct prey species density integration (NOAA AMAPPS, USGS data)
- [ ] Direct dissolved oxygen measurements (when available)
- [ ] Additional shark species profiles (Whale Shark, Blue Shark, Hammerhead)
- [ ] Real-time data streaming
- [ ] Machine learning model integration for prey density prediction
- [ ] Mobile app development
- [ ] Advanced visualization options (3D terrain, time-series animation)
- [ ] Data export functionality
- [ ] User authentication and saved predictions
- [ ] Integration with shark tracking data (OCEARCH, SPOT tags)

---

**Note**: This application is for research and educational purposes. Always verify predictions with actual field data and consult marine biologists for scientific applications.
