# Shark Foraging Hotspot Prediction Server

A full-stack web application that predicts global shark foraging hotspots using NASA satellite data and a Habitat Suitability Index (HSI) model.

## 🦈 Features

- **NASA Satellite Data Integration**: Fetches and processes real-time data from NASA's Earthdata Cloud
- **HSI Mathematical Model**: Implements habitat suitability calculations for different shark species
- **Interactive Web Interface**: Beautiful, responsive map visualization with Leaflet.js
- **Species-Specific Predictions**: Supports Great White Shark and Tiger Shark profiles
- **Data Caching**: Efficient local caching system to avoid redundant API calls
- **Real-time Visualization**: Dynamic heatmap and polygon overlays

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

The application uses three NASA satellite datasets with enhanced processing:

### 1. Phytoplankton/Chlorophyll-a
- **Mission/Instrument**: PACE (Plankton, Aerosol, Cloud, ocean Ecosystem) / OCI (Ocean Color Instrument)
- **Product**: Level-3 Binned Mapped Chlorophyll-a Concentration
- **Short Name**: `PACE_OCI_L3M_CHL`
- **Details**: Monthly composite data that provides stable "pasture" maps for trophic lag calculations. Serves as the foundational layer of the marine food web.

### 2. Sea Surface Height, Eddies, and Fronts
- **Mission/Instrument**: Multi-mission (TOPEX/Poseidon, Jason series, Sentinel-6)
- **Product**: NASA-SSH Simple Gridded Sea Surface Height from Standardized Reference Missions Only Version 1
- **Short Name**: `NASA-SSH_SIMPLE_GRIDDED_SSH_V1`
- **Details**: Provides Sea Surface Height Anomaly (SSHA) in meters on a 0.5° grid with 7-day temporal resolution. Large positive values represent warm-core anticyclonic eddies, negative values represent cold-core cyclonic eddies. Steep gradients indicate ocean fronts where prey concentrates. Uses 10 days of observations per grid with Gaussian weighted spatial averaging (100 km width). Data spans from Oct 1992 to present with basin-aware processing. Quality controlled using NASA flags (nasa_flag=0, median_filter_flag=0).

### 3. Sea Surface Temperature (SST)
- **Mission/Instrument**: Multi-mission blended product (VIIRS, MODIS)
- **Product**: MUR (Multi-scale Ultra-high Resolution) Level-4 Global Foundation Sea Surface Temperature Analysis
- **Short Name**: `MUR-JPL-L4-GLOB-v4.1`
- **Details**: Gap-filled, cloud-free global SST data at ~1km resolution. Critical habitability filter for the model.

## 🧮 HSI Model

The Habitat Suitability Index is calculated using the formula:

```
H(x,y,t) = (f_C(C')^w_C × f_E(E')^w_E × f_S(S)^w_S)^(1/(w_C + w_E + w_S))
```

Where:
- `f_C`: Normalized chlorophyll concentration (food web foundation)
- `f_E`: Combined eddy and front suitability from sea level anomaly
- `f_S`: Gaussian temperature suitability (habitability filter)
- `w_C`, `w_E`, `w_S`: Species-specific weights

### Enhanced Processing Features:
- **Eddy Detection**: Identifies warm-core (positive SLA) and cold-core (negative SLA) eddies
- **Front Detection**: Calculates spatial gradients to identify ocean fronts
- **Trophic Lag Implementation**: Uses lagged environmental data to account for ecological response times
- **Data Quality Control**: Handles fill values, outliers, and unit conversions
- **Spatial Regridding**: Aligns all datasets to a common 0.25° global grid

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js (for development)
- NASA Earthdata account (free registration required)

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

The application includes predefined profiles for two shark species:

#### Great White Shark
- Optimal Temperature: 18°C
- Temperature Tolerance: 5°C
- Temperature Lag: 7 days
- Chlorophyll Lag: 30 days
- Weights: Chlorophyll (0.4), Sea Level (0.3), Temperature (0.3)

#### Tiger Shark
- Optimal Temperature: 25°C
- Temperature Tolerance: 4°C
- Temperature Lag: 5 days
- Chlorophyll Lag: 21 days
- Weights: Chlorophyll (0.3), Sea Level (0.4), Temperature (0.3)

### Data Sources
- **Chlorophyll**: PACE OCI Level-3 Monthly Composite
- **Sea Level**: NASA-SSH Simple Gridded Sea Surface Height L4 (7-day resolution, 0.5° grid, SSHA variable)
- **Temperature**: MUR Level-4 Global Foundation Sea Surface Temperature

### API Endpoints

- `GET /api/hotspots` - Get HSI predictions
- `GET /api/species` - Get available shark species profiles
- `GET /api/datasets` - Get NASA dataset information
- `GET /health` - Health check
- `POST /api/authenticate` - NASA Earthdata authentication

## 🗺️ Usage

1. **Select Species**: Choose from Great White Shark or Tiger Shark
2. **Pick Date**: Select a target date for prediction
3. **Adjust Threshold**: Set HSI threshold for visualization
4. **Generate Prediction**: Click "Predict Hotspots" to run the model
5. **Explore Results**: View the interactive map with hotspots
6. **Toggle Views**: Switch between polygon and heatmap visualizations

## 🔬 Model Parameters

The HSI model uses species-specific parameters that can be adjusted:

- **S_opt**: Optimal temperature for the species
- **σ_S**: Temperature tolerance (standard deviation)
- **T_lag**: Temperature lag in days
- **C_lag**: Chlorophyll lag in days
- **Weights**: Relative importance of each environmental factor

### Trophic Lag Implementation

The model implements trophic lag to account for ecological response times:

- **Temperature Lag**: Sharks respond to temperature changes with a delay (5-7 days)
- **Chlorophyll Lag**: Food web effects propagate from phytoplankton to sharks (21-30 days)
- **Sea Level Anomaly**: Current data used (immediate oceanographic response)
- **Fallback**: If lagged data is unavailable, current data is used with warnings

## 📈 Performance

- **Data Caching**: Downloaded data is cached locally to improve performance
- **Grid Resolution**: 0.25° global grid for optimal balance of detail and performance
- **Lazy Loading**: Data is fetched only when needed
- **Efficient Visualization**: Optimized GeoJSON conversion for map rendering

## 🛡️ Security

- **NASA Authentication**: Secure authentication with NASA Earthdata
- **Input Validation**: Comprehensive input validation and error handling
- **CORS Configuration**: Configurable Cross-Origin Resource Sharing

## 🔍 Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Ensure you have a valid NASA Earthdata account
   - Run `earthaccess.login()` to authenticate
   - Check your internet connection

2. **Data Not Found**
   - Some dates may not have available satellite data
   - Try dates within the last 2-3 years
   - Check NASA data availability

3. **Performance Issues**
   - Clear the data cache if needed
   - Reduce grid resolution for faster processing
   - Check available system memory

### Debug Mode

Enable debug logging by setting the log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

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
