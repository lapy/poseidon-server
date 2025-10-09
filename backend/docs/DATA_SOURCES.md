# Data Sources Documentation

## Scientific Data Only

This application uses **REAL SCIENTIFIC DATA ONLY** from authoritative sources. No synthetic or simulated data is used.

---

## Primary Data Sources

### 1. NASA Oceanographic Data

All oceanographic parameters are sourced from NASA satellite missions and validated datasets:

#### Sea Surface Temperature (SST)
- **Source**: VIIRS NPP Level-3 Mapped Sea Surface Temperature
- **Variable**: `sst_triple` (triple sensor blend)
- **Provider**: NASA Ocean Color / OBPG
- **URL**: https://oceancolor.gsfc.nasa.gov/
- **Resolution**: 0.5° latitude/longitude grid
- **Format**: NetCDF (CF-compliant)
- **Update Frequency**: Daily composites

#### Chlorophyll-a Concentration
- **Source**: VIIRS NPP Level-3 Chlorophyll-a
- **Provider**: NASA Ocean Color / OBPG
- **Resolution**: 0.5° grid
- **Format**: NetCDF
- **Scientific Use**: Primary productivity indicator and prey availability proxy

#### Sea Level Anomaly (SLA)
- **Source**: NASA-SSH Multi-Mission Sea Surface Height
- **Mission**: Jason-3, Sentinel-6 Michael Freilich
- **Provider**: NASA Physical Oceanography DAAC
- **Resolution**: 0.5° grid
- **Scientific Use**: Eddy and oceanic front detection
- **Features**:
  - Dual-pass coverage (ascending/descending)
  - 10-day observation window with temporal merging
  - Gaussian weighted spatial averaging

#### Salinity
- **Source**: SMAP L3 Sea Surface Salinity
- **Mission**: Soil Moisture Active Passive (SMAP)
- **Provider**: NASA PO.DAAC
- **Resolution**: 0.5° grid
- **Format**: NetCDF

### 2. Global Fishing Watch (GFW) Anthropogenic Data

Human impact data from the Global Fishing Watch platform:

#### Fishing Pressure
- **Source**: GFW 4Wings API - Public Global Fishing Effort
- **Dataset**: `public-global-fishing-effort:latest`
- **Provider**: Global Fishing Watch
- **Attribution**: "Data provided by Global Fishing Watch (https://globalfishingwatch.org/)"
- **Data Type**: AIS-based apparent fishing activity
- **Coverage**: Global, 2012-present
- **Resolution**: Regridded to 0.5° to match oceanographic grid

#### Vessel Density (Shipping)
- **Source**: GFW 4Wings API - AIS Vessel Presence
- **Provider**: Global Fishing Watch
- **Data Type**: All vessel activity from AIS transponders
- **Coverage**: Global ocean areas
- **Resolution**: Regridded to 0.5°

**Important**: GFW data requires an API key. Set the `GFW_API_KEY` environment variable to enable real anthropogenic data.

---

## Data Handling

### When GFW Data is Unavailable

If the GFW API key is not configured or data cannot be retrieved:
- **Fallback**: Neutral dataset with **zero anthropogenic pressure**
- **Scientific Rationale**: Conservative assumption - assumes no human pressure when data is missing
- **Impact on HSI**: HSI calculations proceed without anthropogenic filter
- **User Notification**: Application logs clearly indicate when neutral (zero) data is used

**This is NOT synthetic data** - it's a scientifically conservative fallback assumption.

### Data Processing Pipeline

1. **Data Retrieval**
   - NASA data: Direct access via OPeNDAP/HTTP
   - GFW data: Via official `gfw-api-python-client`

2. **Caching**
   - All data cached locally in NetCDF format
   - Cache TTL: 30 days (configurable)
   - Location: `data_cache/` directory

3. **Coordinate Alignment**
   - All datasets regridded to common 0.5° grid
   - Method: Linear interpolation via `xarray.interp_like()`
   - CRS: WGS84 (EPSG:4326)
   - Grid extent: -90° to 90° lat, -180° to 180° lon

4. **Quality Control**
   - NaN handling: Masked from calculations
   - Temporal matching: Lag-based selection for biological realism
   - Validation: Min/max range checks

---

## Scientific Citations

When using this application or its outputs, please cite:

### NASA Data
```
NASA Ocean Biology Processing Group (2024). VIIRS Ocean Color Data.
NASA Goddard Space Flight Center, Ocean Ecology Laboratory, Ocean Biology Processing Group.
https://oceancolor.gsfc.nasa.gov/

NASA Physical Oceanography Distributed Active Archive Center (2024).
Multi-Mission Sea Surface Height. JPL PO.DAAC, Pasadena, CA.
https://podaac.jpl.nasa.gov/
```

### Global Fishing Watch
```
Global Fishing Watch (2024). Fishing Activity Data.
Data provided by Global Fishing Watch.
https://globalfishingwatch.org/
```

---

## Data Quality & Limitations

### Spatial Coverage
- **Global**: All ocean areas covered
- **Land Masking**: Automatic via NaN values in NASA datasets
- **Coastal Zones**: May have reduced data density due to satellite coverage gaps

### Temporal Coverage
- **NASA Data**: Near-real-time (3-7 day lag for processing)
- **GFW Data**: 3-day lag from present
- **Historical**: All datasets available from 2012 onwards

### Known Limitations
1. **Cloud Cover**: Optical sensors (VIIRS) affected by clouds; gaps filled via temporal composites
2. **High Latitudes**: Reduced coverage >70° latitude due to orbital geometry
3. **Coastal Interference**: Satellite altimetry less accurate <50km from coast
4. **AIS Limitations**: GFW data only includes vessels with AIS transponders (primarily large commercial vessels)

### Validation
- NASA data: Validated against in-situ measurements (ARGO floats, buoys)
- GFW data: Cross-validated with VMS data where available
- HSI Model: Calibrated against known shark occurrence data

---

## Configuration

### Environment Variables

```bash
# NASA Data (no authentication required for public datasets)
CACHE_DIR=data_cache
NASA_CACHE_TTL_DAYS=30

# Global Fishing Watch (REQUIRED for anthropogenic data)
GFW_API_KEY=your_api_key_here
GFW_CACHE_TTL_DAYS=30
```

### Obtaining a GFW API Key

1. Create account at https://globalfishingwatch.org/
2. Request API access via https://globalfishingwatch.org/our-apis/
3. Set `GFW_API_KEY` environment variable

---

## Data Attribution & Licensing

### NASA Data
- **License**: Open access (no restrictions)
- **Attribution**: Required per NASA policy

### GFW Data
- **License**: Creative Commons (CC BY-SA 4.0)
- **Attribution**: **REQUIRED** - Must display "Data provided by Global Fishing Watch"
- **Terms**: https://globalfishingwatch.org/our-apis/

---

## Updates & Maintenance

- **Data Refresh**: Automatic cache invalidation after TTL
- **Manual Refresh**: Delete files in `data_cache/` directory
- **Version Tracking**: Dataset versions logged in cached NetCDF attributes

For questions about data sources or processing, see:
- [NASA Data Access Guide](./NASA_DATA.md)
- [GFW Integration Documentation](./ANTHROPOGENIC_PRESSURE.md)

