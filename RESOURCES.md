# Project Resources & Links

Complete list of datasets, libraries, tools, and resources used in the Shark Foraging Hotspot Prediction Server.

## 📊 NASA Datasets

### 1. PACE OCI Chlorophyll-a Data
- **Dataset Page**: https://podaac.jpl.nasa.gov/dataset/PACE_OCI_L3M_CHL
- **Short Name**: `PACE_OCI_L3M_CHL`
- **Mission Page**: https://pace.gsfc.nasa.gov/
- **Data Access**: NASA Earthdata Cloud via earthaccess
- **Documentation**: https://oceancolor.gsfc.nasa.gov/data/pace/
- **Product Guide**: https://oceancolor.gsfc.nasa.gov/atbd/

### 2. NASA-SSH Sea Surface Height
- **Dataset Page**: https://podaac.jpl.nasa.gov/dataset/NASA_SSH_REF_SIMPLE_GRID_V1
- **Short Name**: `NASA_SSH_REF_SIMPLE_GRID_V1`
- **Mission Pages**:
  - TOPEX/Poseidon: https://sealevel.jpl.nasa.gov/missions/topex-poseidon/
  - Jason Series: https://sealevel.jpl.nasa.gov/missions/jason-3/
  - Sentinel-6: https://sealevel.jpl.nasa.gov/missions/sentinel-6-michael-freilich/
- **Reference Surface**: DTU21 Mean Sea Surface (1993-2012)

### 3. VIIRS NPP Sea Surface Temperature
- **Dataset Page**: https://podaac.jpl.nasa.gov/dataset/VIIRSN_L3m_SST3
- **Short Name**: `VIIRSN_L3m_SST3`
- **Mission Page**: https://www.nesdis.noaa.gov/current-satellite-missions/currently-flying/joint-polar-satellite-system/visible-infrared-imaging
- **GHRSST Project**: https://www.ghrsst.org/
- **Product Documentation**: https://podaac.jpl.nasa.gov/GHRSST

### 4. OISSS Sea Surface Salinity
- **Dataset Page**: https://podaac.jpl.nasa.gov/dataset/OISSS_L4_multimission_monthly_v2
- **Short Name**: `OISSS_L4_multimission_monthly_v2`
- **Missions**:
  - SMAP: https://smap.jpl.nasa.gov/
  - SMOS: https://earth.esa.int/eogateway/missions/smos
  - Aquarius: https://aquarius.umaine.edu/
- **Documentation**: https://podaac.jpl.nasa.gov/dataset/OISSS_L4_multimission_monthly_v2

## 🔧 NASA Tools & Services

### Earthdata Cloud
- **NASA Earthdata**: https://www.earthdata.nasa.gov/
- **Earthdata Login**: https://urs.earthdata.nasa.gov/
- **Earthdata Search**: https://search.earthdata.nasa.gov/
- **PO.DAAC**: https://podaac.jpl.nasa.gov/ (Physical Oceanography Distributed Active Archive Center)
- **Earthdata Cloud Cookbook**: https://nasa-openscapes.github.io/earthdata-cloud-cookbook/

### Data Access APIs
- **CMR API**: https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html (Common Metadata Repository)

## 🐍 Python Libraries

### Backend Framework
- **FastAPI**: https://fastapi.tiangolo.com/
  - Version: 0.104.1
  - Modern, fast web framework
- **Uvicorn**: https://www.uvicorn.org/
  - Version: 0.24.0
  - ASGI server

### NASA Data Access
- **earthaccess**: https://github.com/nsidc/earthaccess
  - Version: 0.12.0
  - NASA Earthdata authentication and search
  - Documentation: https://earthaccess.readthedocs.io/

### Scientific Computing
- **NumPy**: https://numpy.org/
  - Version: 1.24.4
  - Numerical computing
  - Documentation: https://numpy.org/doc/
- **SciPy**: https://scipy.org/
  - Version: 1.11.4
  - Scientific computing and optimization
  - Documentation: https://docs.scipy.org/
- **xarray**: https://xarray.dev/
  - Version: 2023.11.0
  - Multi-dimensional array processing
  - Documentation: https://docs.xarray.dev/

### Data Formats
- **netCDF4**: https://unidata.github.io/netcdf4-python/
  - Version: 1.6.5
  - NetCDF file handling
- **h5netcdf**: https://github.com/h5netcdf/h5netcdf
  - Version: 1.3.0
  - HDF5-based NetCDF implementation
- **pandas**: https://pandas.pydata.org/
  - Version: 2.1.3
  - Data manipulation and analysis

### Geospatial Libraries
- **geopandas**: https://geopandas.org/
  - Version: 0.14.1
  - Geospatial data processing
  - Documentation: https://geopandas.org/en/stable/docs.html
- **Shapely**: https://shapely.readthedocs.io/
  - Version: 2.0.2
  - Geometric operations
- **pyproj**: https://pyproj4.github.io/pyproj/
  - Version: 3.6.1
  - Cartographic projections
- **rasterio**: https://rasterio.readthedocs.io/
  - Version: 1.3.9
  - Raster data I/O

### Visualization (Backend)
- **Folium**: https://python-visualization.github.io/folium/
  - Version: 0.15.1
  - Python mapping library

### Utilities
- **python-dotenv**: https://github.com/theskumar/python-dotenv
  - Version: 1.0.0
  - Environment variable management
- **httpx**: https://www.python-httpx.org/
  - Version: 0.25.2
  - Async HTTP client
- **aiofiles**: https://github.com/Tinche/aiofiles
  - Version: 23.2.1
  - Async file operations

## 🌐 Frontend Libraries

### Mapping
- **Leaflet.js**: https://leafletjs.com/
  - Version: 1.9.4
  - Interactive maps
  - Documentation: https://leafletjs.com/reference.html
  - CDN: https://unpkg.com/leaflet@1.9.4/dist/leaflet.js

### Icons
- **Font Awesome**: https://fontawesome.com/
  - Version: 6.4.0
  - Icon library
  - CDN: https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css

### Core Technologies
- **HTML5**: https://developer.mozilla.org/en-US/docs/Web/HTML
- **CSS3**: https://developer.mozilla.org/en-US/docs/Web/CSS
- **JavaScript (ES6+)**: https://developer.mozilla.org/en-US/docs/Web/JavaScript

## 📚 Scientific References & Documentation

### Oceanography
- **DTU Space Mean Sea Surface**: https://www.space.dtu.dk/english/research/scientific_data_and_models/global_mean_sea_surface
- **Ocean Eddies**: https://earth.gsfc.nasa.gov/climate/research/oceanography/ocean-eddies
- **Ocean Fronts**: https://oceanservice.noaa.gov/facts/fronts.html

### Marine Biology
- **IUCN Shark Specialist Group**: https://www.iucnssg.org/
- **NOAA Fisheries Sharks**: https://www.fisheries.noaa.gov/topic/sharks
- **ReefQuest Centre for Shark Research**: http://www.elasmo-research.org/

### Habitat Suitability Modeling
- **Marine SDM**: https://www.sciencedirect.com/topics/earth-and-planetary-sciences/species-distribution-model

## 🏆 Challenge & Project Resources

### NASA Space Apps Challenge
- **Main Challenge Page**: https://www.spaceappschallenge.org/2025/challenges/sharks-from-space/
- **NASA Space Apps**: https://www.spaceappschallenge.org/
- **Challenge Resources**: https://www.spaceappschallenge.org/2025/challenges/sharks-from-space/?tab=resources

### Project Documentation
- **GitHub Repository**: https://github.com/lapy/poseidon-server
- **API Documentation**: Available at `/api/docs` when server is running
- **Technical Docs**: 
  - README.md
  - OCEANOGRAPHIC_FEATURES.md
  - NASA_CHALLENGE_SUBMISSION.md

## 🔬 Research & Papers

### Key Scientific Concepts
- **Mesoscale Eddies**: 
  - https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2011RG000350
  - "The Role of Mesoscale Eddies in Marine Ecosystems"
  
- **Trophic Dynamics**:
  - https://www.nature.com/articles/nature07286
  - Marine food web response times

- **Satellite Oceanography**:
  - https://www.aviso.altimetry.fr/
  - AVISO+ satellite altimetry for oceanography

### Shark Biology & Ecology
- **Shark Habitat Preferences**: https://www.int-res.com/abstracts/meps/
- **Shark Migration Patterns**: https://www.cell.com/current-biology/home
- **Shark Conservation**: https://saveourseas.com/

## 🛠️ Development Tools

### Python Development
- **Python**: https://www.python.org/
  - Version: 3.8+
- **pip**: https://pip.pypa.io/
  - Package installer
- **venv**: https://docs.python.org/3/library/venv.html
  - Virtual environments

### API Development
- **Swagger/OpenAPI**: https://swagger.io/specification/
- **Pydantic**: https://docs.pydantic.dev/

## 🤖 Development Tools & AI Assistance

### AI Development Assistant
- **Claude (Anthropic)**: https://www.anthropic.com/claude
  - Used for: Code development, architecture design, documentation, debugging
  - Role: AI coding partner under human oversight
  - Note: All scientific concepts based on peer-reviewed research and NASA documentation

---

**Last Updated**: October 2025

*This document provides a comprehensive reference for all external resources used in the Shark Foraging Hotspot Prediction Server project.*

**AI Disclosure**: This project was developed with AI assistance (Claude by Anthropic) for code development, optimization, and documentation. All technical decisions and implementations were overseen by human developers, and all scientific methodologies are based on established research.

