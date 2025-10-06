/**
 * Project Poseidon - Frontend Application
 * Predictive Oceanographic Shark Ecology & In-situ Data Observation Network
 * Interactive map interface for visualizing HSI predictions
 */

class SharkHotspotApp {
    constructor() {
        this.map = null;
        this.hsiLayer = null;
        this.heatmapLayer = null;
        this.currentData = null;
        this.isHeatmapMode = false;
        
        // Overlay layers
        this.overlayLayers = {
            chlorophyll: null,
            oceanographic: null,
            salinity: null
        };
        
        // API configuration
        this.apiBaseUrl = window.location.origin + '/api';
        
        // Initialize the application
        this.init();
    }
    
    init() {
        this.initializeMap();
        this.setupEventListeners();
        this.setDefaultDate();
        this.loadSharkSpecies();
        
        // Setup overlay listeners after DOM is ready
        setTimeout(() => {
            this.setupOverlayListeners();
        }, 100);
    }
    
    initializeMap() {
        // Initialize Leaflet map with zoom constraints
        this.map = L.map('map', {
            minZoom: 2,  // Prevent zooming out beyond world view
            maxZoom: 18, // Maximum zoom level
            maxBounds: [
                [-90, -180], // Southwest corner
                [90, 180]    // Northeast corner
            ],
            maxBoundsViscosity: 1.0 // Keep bounds strict
        }).setView([50, 10], 4); // Focus on Europe
        
        // Add base tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 18
        }).addTo(this.map);
        
        // Initialize heatmap layer
        this.heatmapLayer = L.heatLayer([], {
            radius: 25,
            blur: 15,
            maxZoom: 17,
            max: 1.0,
            gradient: {
                0.0: 'blue',
                0.2: 'cyan',
                0.4: 'green',
                0.6: 'yellow',
                0.8: 'orange',
                1.0: 'red'
            }
        });
        
        console.log('Map initialized');
    }
    
    setupEventListeners() {
        // Form controls
        document.getElementById('shark-species').addEventListener('change', () => {
            this.updatePredictButton();
        });
        
        document.getElementById('target-date').addEventListener('change', () => {
            this.updatePredictButton();
        });
        
        document.getElementById('hsi-threshold').addEventListener('input', (e) => {
            document.getElementById('threshold-value').textContent = e.target.value;
            if (this.currentData) {
                this.updateVisualization();
            }
        });
        
        document.getElementById('predict-button').addEventListener('click', () => {
            this.predictHotspots();
        });
        
        // Map controls
        document.getElementById('toggle-heatmap').addEventListener('click', () => {
            this.toggleHeatmap();
        });
        
        document.getElementById('toggle-polygons').addEventListener('click', () => {
            this.togglePolygons();
        });
        
        document.getElementById('reset-map').addEventListener('click', () => {
            this.resetMapView();
        });
        
        // Overlay listeners will be set up after DOM is ready
    }
    
    setDefaultDate() {
        // Set default date to one month ago
        const oneMonthAgo = new Date();
        oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1);
        const dateString = oneMonthAgo.toISOString().split('T')[0];
        document.getElementById('target-date').value = dateString;
        
        // Set max date to 30 days ago to prevent selecting recent dates
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
        document.getElementById('target-date').max = thirtyDaysAgo.toISOString().split('T')[0];
    }
    
    async loadSharkSpecies() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/species`);
            const species = await response.json();
            
            const select = document.getElementById('shark-species');
            select.innerHTML = '';
            
            // Add Tiger Shark first as default
            const tigerOption = document.createElement('option');
            tigerOption.value = 'tiger_shark';
            tigerOption.textContent = 'Tiger Shark';
            tigerOption.selected = true;
            select.appendChild(tigerOption);
            
            // Add other species
            for (const [key, profile] of Object.entries(species)) {
                if (key !== 'tiger_shark') { // Skip tiger shark as it's already added
                    const option = document.createElement('option');
                    option.value = key;
                    option.textContent = profile.name;
                    select.appendChild(option);
                }
            }
        } catch (error) {
            console.error('Failed to load shark species:', error);
            this.showStatus('Error loading shark species', 'error');
        }
    }
    
    updatePredictButton() {
        const species = document.getElementById('shark-species').value;
        const date = document.getElementById('target-date').value;
        const button = document.getElementById('predict-button');
        
        // Button is always enabled since we have defaults for both species and date
        button.disabled = false;
    }
    
    
    async predictHotspots() {
        const species = document.getElementById('shark-species').value;
        const date = document.getElementById('target-date').value;
        
        if (!species || !date) {
            this.showStatus('Please select both species and date', 'error');
            return;
        }
        
        this.showLoading(true);
        this.showStatus('Processing NASA satellite data for entire dataset...', 'loading');

        try {
            const url = `${this.apiBaseUrl}/hotspots?target_date=${date}&shark_species=${species}&format=geojson`;
            
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.currentData = data;
            
            this.updateVisualization();
            this.updateResultsPanel(data.metadata);
            this.updatePerformanceInfo(data.metadata);
            
            this.showStatus('Prediction completed successfully!', 'success');
            
            // Scroll to overlays section after analysis completes
            this.scrollToOverlays();
            
        } catch (error) {
            console.error('Prediction failed:', error);
            this.showStatus(`Prediction failed: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    
    scrollToOverlays() {
        // Find the overlays section and scroll to it
        const overlaysSection = document.querySelector('.overlay-controls-horizontal');
        if (overlaysSection) {
            overlaysSection.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
            console.log('Scrolled to overlays section');
        } else {
            console.warn('Overlays section not found');
        }
    }
    
    toggleOverlay(type, enabled) {
        console.log(`Toggling ${type} overlay: ${enabled}`);
        console.log('Current data available:', !!this.currentData);
        
        // Remove existing layer if it exists
        if (this.overlayLayers[type]) {
            this.map.removeLayer(this.overlayLayers[type]);
            this.overlayLayers[type] = null;
            console.log(`Removed existing ${type} overlay`);
        }
        
        if (enabled && this.currentData) {
            console.log(`Adding ${type} overlay layer`);
            this.addOverlayLayer(type);
        } else if (enabled && !this.currentData) {
            console.log('Cannot add overlay - no data available. Run a prediction first.');
        }
        
        // Update overlay legend visibility
        this.updateOverlayLegend();
    }
    
    setupOverlayListeners() {
        // Add overlay toggle event listeners with error handling
        try {
            const chlorophyllOverlay = document.getElementById('chlorophyll-overlay');
            const oceanographicOverlay = document.getElementById('oceanographic-overlay');
            const salinityOverlay = document.getElementById('salinity-overlay');
            
            if (chlorophyllOverlay) {
                chlorophyllOverlay.addEventListener('change', (e) => {
                    this.toggleOverlay('chlorophyll', e.target.checked);
                });
            } else {
                console.warn('Chlorophyll overlay element not found');
            }
            
            if (oceanographicOverlay) {
                oceanographicOverlay.addEventListener('change', (e) => {
                    this.toggleOverlay('oceanographic', e.target.checked);
                });
            } else {
                console.warn('Oceanographic overlay element not found');
            }
            
            if (salinityOverlay) {
                salinityOverlay.addEventListener('change', (e) => {
                    this.toggleOverlay('salinity', e.target.checked);
                });
            } else {
                console.warn('Salinity overlay element not found');
            }
            
            console.log('Overlay listeners setup complete');
        } catch (error) {
            console.error('Error setting up overlay listeners:', error);
        }
    }
    
    updateOverlayLegend() {
        const overlayLegend = document.getElementById('overlay-legend');
        const hasActiveOverlays = Object.values(this.overlayLayers).some(layer => layer !== null);
        
        if (hasActiveOverlays) {
            overlayLegend.style.display = 'block';
        } else {
            overlayLegend.style.display = 'none';
        }
    }
    
    async addOverlayLayer(type) {
        if (!this.currentData || !this.currentData.metadata) {
            console.warn('No prediction data available for overlay date');
            return;
        }
        
        try {
            console.log(`Fetching ${type} overlay data...`);
            
            // Get the target date from current prediction
            const targetDate = this.currentData.metadata.target_date;
            
            // Build API URL with density reduction and shark species for lag calculation
            const densityFactor = 6; // Higher = less dense overlays
            const sharkSpecies = document.getElementById('shark-species').value || 'tiger_shark';
            const url = `${this.apiBaseUrl}/overlay/${type}?target_date=${targetDate}&shark_species=${sharkSpecies}&density_factor=${densityFactor}`;
            console.log(`Fetching overlay data from: ${url}`);
            
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const overlayData = await response.json();
            console.log(`Received ${type} overlay data with ${overlayData.features.length} features`);
            
            // Create overlay layer
            let layer = null;
            switch (type) {
                case 'chlorophyll':
                    layer = this.createChlorophyllOverlay(overlayData);
                    break;
                case 'oceanographic':
                    layer = this.createOceanographicOverlay(overlayData);
                    break;
                case 'salinity':
                    layer = this.createSalinityOverlay(overlayData);
                    break;
            }
            
            if (layer) {
                this.overlayLayers[type] = layer.addTo(this.map);
                console.log(`Added ${type} overlay layer to map`);
                console.log(`Map layers count:`, Object.keys(this.map._layers).length);
            }
            
        } catch (error) {
            console.error(`Failed to load ${type} overlay:`, error);
            this.showStatus(`Failed to load ${type} overlay data`, 'error');
        }
    }
    
    createChlorophyllOverlay(data) {
        console.log('Creating chlorophyll overlay with raw data');
        
        return L.geoJSON(data, {
            style: (feature) => {
                const value = feature.properties.chlorophyll || 0;
                // Normalize chlorophyll values (typically 0-10 mg/m³)
                const normalized = Math.min(value / 5.0, 1.0); // Scale to 0-1 range
                
                return {
                    fillColor: '#228B22',
                    fillOpacity: Math.max(normalized * 0.8, 0.2),
                    color: '#228B22',
                    weight: 1,
                    opacity: 0.6
                };
            },
            onEachFeature: (feature, layer) => {
                const value = feature.properties.chlorophyll || 0;
                const popup = `
                    <h3>Chlorophyll Concentration</h3>
                    <p><strong>Value:</strong> ${value.toFixed(3)} mg/m³</p>
                    <p><strong>Latitude:</strong> ${feature.properties.lat.toFixed(2)}°</p>
                    <p><strong>Longitude:</strong> ${feature.properties.lon.toFixed(2)}°</p>
                `;
                layer.bindPopup(popup);
            }
        });
    }
    
    createOceanographicOverlay(data) {
        console.log('Creating oceanographic overlay with processed eddy/front data');
        
        return L.geoJSON(data, {
            style: (feature) => {
                const value = feature.properties.oceanographic || 0;
                // Value is already normalized (0-1) from HSI processing
                const normalized = Math.min(Math.max(value, 0), 1);
                
                return {
                    fillColor: '#0064C8',
                    fillOpacity: Math.max(normalized * 0.8, 0.2),
                    color: '#0064C8',
                    weight: 1,
                    opacity: 0.6
                };
            },
            onEachFeature: (feature, layer) => {
                const value = feature.properties.oceanographic || 0;
                const popup = `
                    <h3>Oceanographic Features</h3>
                    <p><strong>Eddy/Front Suitability:</strong> ${(value * 100).toFixed(1)}%</p>
                    <p><strong>Combined Score:</strong> ${value.toFixed(3)} (0-1 scale)</p>
                    <p><strong>Features:</strong> Eddies (60%) + Fronts (40%)</p>
                    <p><strong>Latitude:</strong> ${feature.properties.lat.toFixed(2)}°</p>
                    <p><strong>Longitude:</strong> ${feature.properties.lon.toFixed(2)}°</p>
                `;
                layer.bindPopup(popup);
            }
        });
    }
    
    createSalinityOverlay(data) {
        console.log('Creating salinity overlay with raw data');
        
        return L.geoJSON(data, {
            style: (feature) => {
                const value = feature.properties.salinity || 0; // Sea Surface Salinity
                // Normalize salinity values (typically 30-37 psu)
                const normalized = Math.min((value - 30) / 7.0, 1.0); // Scale to 0-1 range
                
                return {
                    fillColor: '#008080',
                    fillOpacity: Math.max(normalized * 0.8, 0.2),
                    color: '#008080',
                    weight: 1,
                    opacity: 0.6
                };
            },
            onEachFeature: (feature, layer) => {
                const value = feature.properties.salinity || 0;
                const popup = `
                    <h3>Sea Surface Salinity</h3>
                    <p><strong>Value:</strong> ${value.toFixed(2)} psu</p>
                    <p><strong>Latitude:</strong> ${feature.properties.lat.toFixed(2)}°</p>
                    <p><strong>Longitude:</strong> ${feature.properties.lon.toFixed(2)}°</p>
                `;
                layer.bindPopup(popup);
            }
        });
    }
    
    updatePerformanceInfo(metadata) {
        const processingArea = metadata.processing_area || 'Global';
        const laggedDataAvailable = metadata.lagged_data_available;

        let performanceHtml = `
            <div class="performance-stats">
                <div class="stat-item">
                    <span class="stat-label">Processing Area:</span>
                    <span class="stat-value">${processingArea}</span>
                </div>
        `;
        
        if (laggedDataAvailable) {
            performanceHtml += `
                <div class="stat-item">
                    <span class="stat-label">Lagged Data:</span>
                    <span class="stat-value">Chl: ${laggedDataAvailable.chlorophyll ? '✓' : '✗'}, SST: ${laggedDataAvailable.temperature ? '✓' : '✗'}</span>
                </div>
            `;
        }
        
        performanceHtml += '</div>';
        
        // Update or create performance info element
        let performanceElement = document.getElementById('performance-info');
        if (!performanceElement) {
            performanceElement = document.createElement('div');
            performanceElement.id = 'performance-info';
            performanceElement.className = 'performance-info';
            document.querySelector('.results-panel').appendChild(performanceElement);
        }
        
        performanceElement.innerHTML = performanceHtml;
    }
    
    updateVisualization() {
        if (!this.currentData || !this.map) return;
        
        const threshold = parseFloat(document.getElementById('hsi-threshold').value);
        
        // Filter features by threshold
        const filteredFeatures = this.currentData.features.filter(feature => 
            feature.properties.hsi >= threshold
        );
        
        // Clear existing layers
        if (this.hsiLayer) {
            this.map.removeLayer(this.hsiLayer);
        }
        
        if (this.isHeatmapMode) {
            this.updateHeatmap(filteredFeatures);
        } else {
            this.updatePolygons(filteredFeatures);
        }
        
        // Update overlays if they are enabled
        this.updateEnabledOverlays();
    }
    
    updateEnabledOverlays() {
        // Check which overlays are enabled and update them
        const chlorophyllEnabled = document.getElementById('chlorophyll-overlay').checked;
        const oceanographicEnabled = document.getElementById('oceanographic-overlay').checked;
        const salinityEnabled = document.getElementById('salinity-overlay').checked;
        
        // Update each overlay if it's enabled
        if (chlorophyllEnabled && this.overlayLayers.chlorophyll) {
            this.map.removeLayer(this.overlayLayers.chlorophyll);
            this.addOverlayLayer('chlorophyll');
        }
        
        if (oceanographicEnabled && this.overlayLayers.oceanographic) {
            this.map.removeLayer(this.overlayLayers.oceanographic);
            this.addOverlayLayer('oceanographic');
        }
        
        if (salinityEnabled && this.overlayLayers.salinity) {
            this.map.removeLayer(this.overlayLayers.salinity);
            this.addOverlayLayer('salinity');
        }
    }
    
    updatePolygons(features) {
        if (!this.map) return;
        
        // Create polygon layer
        this.hsiLayer = L.geoJSON(features, {
            style: (feature) => ({
                fillColor: this.getHSIColor(feature.properties.hsi),
                fillOpacity: 0.7,
                color: 'white',
                weight: 1,
                opacity: 0.5
            }),
            onEachFeature: (feature, layer) => {
                // Get component contributions if available
                const contributions = feature.properties.component_contributions || {};
                const hasContributions = contributions.chlorophyll !== undefined;

                const popup = `
                    <h3>HSI Prediction</h3>
                    <p><strong>HSI Value:</strong> <span class="hsi-value">${feature.properties.hsi.toFixed(3)}</span></p>
                    <div class="hsi-components">
                        <h4>Suitability Components:</h4>
                        <div class="component-grid">
                            <div class="component-item">
                                <span class="component-label">Temperature:</span>
                                <span class="component-value">${feature.properties.temperature_suitability?.toFixed(3) || 'N/A'}</span>
                                ${hasContributions ? `<span class="component-contrib">(${contributions.temperature?.toFixed(1) || '0.0'}%)</span>` : ''}
                            </div>
                            <div class="component-item">
                                <span class="component-label">Chlorophyll:</span>
                                <span class="component-value">${feature.properties.chlorophyll_suitability?.toFixed(3) || 'N/A'}</span>
                                ${hasContributions ? `<span class="component-contrib">(${contributions.chlorophyll?.toFixed(1) || '0.0'}%)</span>` : ''}
                            </div>
                            <div class="component-item">
                                <span class="component-label">Oceanographic:</span>
                                <span class="component-value">${feature.properties.sea_level_suitability?.toFixed(3) || 'N/A'}</span>
                                ${hasContributions ? `<span class="component-contrib">(${contributions.oceanographic?.toFixed(1) || '0.0'}%)</span>` : ''}
                            </div>
                            <div class="component-item">
                                <span class="component-label">Salinity:</span>
                                <span class="component-value">${feature.properties.salinity_suitability?.toFixed(3) || 'N/A'}</span>
                            </div>
                        </div>
                        ${hasContributions ? `<div class="contribution-note">* Percentages show relative contribution to HSI score</div>` : ''}
                    </div>
                    <p><strong>Latitude:</strong> ${feature.properties.lat.toFixed(2)}°</p>
                    <p><strong>Longitude:</strong> ${feature.properties.lon.toFixed(2)}°</p>
                    <p><strong>Species:</strong> ${this.currentData.metadata.shark_species}</p>
                    <p><strong>Date:</strong> ${this.currentData.metadata.target_date}</p>
                `;
                layer.bindPopup(popup);
            }
        });
        
        this.hsiLayer.addTo(this.map);
        
        // Keep current map view - don't auto-zoom to data bounds
    }
    
    updateHeatmap(features) {
        if (!this.map) return;
        
        // Convert features to heatmap points
        const heatmapPoints = features.map(feature => [
            feature.properties.lat,
            feature.properties.lon,
            feature.properties.hsi
        ]);
        
        // Update heatmap layer
        this.heatmapLayer.setLatLngs(heatmapPoints);
        
        if (!this.map.hasLayer(this.heatmapLayer)) {
            this.heatmapLayer.addTo(this.map);
        }
    }
    
    getHSIColor(hsi) {
        // Color scale based on HSI value
        if (hsi >= 0.8) return 'red';
        if (hsi >= 0.6) return 'orange';
        if (hsi >= 0.4) return 'yellow';
        if (hsi >= 0.2) return 'green';
        if (hsi >= 0.0) return 'cyan';
        return 'blue';
    }
    
    toggleHeatmap() {
        if (!this.map) return;
        
        this.isHeatmapMode = !this.isHeatmapMode;
        
        const button = document.getElementById('toggle-heatmap');
        const polygonButton = document.getElementById('toggle-polygons');
        
        if (this.isHeatmapMode) {
            button.classList.add('active');
            polygonButton.classList.remove('active');
            
            // Remove polygon layer
            if (this.hsiLayer) {
                this.map.removeLayer(this.hsiLayer);
            }
            
            // Add heatmap layer
            if (this.currentData) {
                this.updateVisualization();
            }
        } else {
            button.classList.remove('active');
            polygonButton.classList.add('active');
            
            // Remove heatmap layer
            if (this.map.hasLayer(this.heatmapLayer)) {
                this.map.removeLayer(this.heatmapLayer);
            }
            
            // Add polygon layer
            if (this.currentData) {
                this.updateVisualization();
            }
        }
    }
    
    togglePolygons() {
        if (!this.map) return;
        
        this.isHeatmapMode = false;
        
        const button = document.getElementById('toggle-polygons');
        const heatmapButton = document.getElementById('toggle-heatmap');
        
        button.classList.add('active');
        heatmapButton.classList.remove('active');
        
        // Remove heatmap layer
        if (this.map.hasLayer(this.heatmapLayer)) {
            this.map.removeLayer(this.heatmapLayer);
        }
        
        // Add polygon layer
        if (this.currentData) {
            this.updateVisualization();
        }
    }
    
    resetMapView() {
        if (!this.map) return;
        this.map.setView([50, 10], 4); // Reset to Europe view
    }
    
    updateResultsPanel(metadata) {
        const panel = document.getElementById('results-panel');
        const statsDiv = document.getElementById('result-stats');
        const infoDiv = document.getElementById('result-info');
        
        // Update statistics
        if (metadata.statistics) {
            statsDiv.innerHTML = `
                <h4>HSI Statistics</h4>
                <div class="stat-item">
                    <span class="stat-label">Mean HSI:</span>
                    <span class="stat-value">${metadata.statistics.mean?.toFixed(3) || 'N/A'}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Max HSI:</span>
                    <span class="stat-value">${metadata.statistics.max?.toFixed(3) || 'N/A'}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">90th Percentile:</span>
                    <span class="stat-value">${metadata.statistics.percentile_90?.toFixed(3) || 'N/A'}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">95th Percentile:</span>
                    <span class="stat-value">${metadata.statistics.percentile_95?.toFixed(3) || 'N/A'}</span>
                </div>
            `;
        }
        
        // Update model info
        if (metadata.model_parameters) {
            infoDiv.innerHTML = `
                <h4>Model Parameters</h4>
                <div class="stat-item">
                    <span class="stat-label">Species:</span>
                    <span class="stat-value">${metadata.shark_species}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Date:</span>
                    <span class="stat-value">${metadata.target_date}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Optimal Temp:</span>
                    <span class="stat-value">${metadata.model_parameters.s_opt}°C</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Temp Tolerance:</span>
                    <span class="stat-value">${metadata.model_parameters.sigma_s}°C</span>
                </div>
            `;
        }
        
        panel.style.display = 'block';
    }
    
    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        overlay.style.display = show ? 'flex' : 'none';
    }
    
    showStatus(message, type = 'info') {
        const indicator = document.getElementById('status-indicator');
        const icon = indicator.querySelector('i');
        const text = indicator.querySelector('span');
        
        // Remove existing classes
        indicator.className = 'status-indicator';
        
        // Add new class
        if (type !== 'info') {
            indicator.classList.add(type);
        }
        
        // Update icon and text
        text.textContent = message;
        
        // Update icon based on type
        switch (type) {
            case 'loading':
                icon.className = 'fas fa-spinner fa-spin';
                break;
            case 'success':
                icon.className = 'fas fa-check-circle';
                break;
            case 'error':
                icon.className = 'fas fa-exclamation-circle';
                break;
            default:
                icon.className = 'fas fa-info-circle';
        }
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new SharkHotspotApp();
});
