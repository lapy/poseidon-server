/**
 * Shark Foraging Hotspot Prediction - Frontend Application
 * Interactive map interface for visualizing HSI predictions
 */

class SharkHotspotApp {
    constructor() {
        this.map = null;
        this.hsiLayer = null;
        this.heatmapLayer = null;
        this.currentData = null;
        this.isHeatmapMode = false;
        
        // API configuration
        this.apiBaseUrl = 'http://localhost:8000/api';
        
        // Initialize the application
        this.init();
    }
    
    init() {
        this.initializeMap();
        this.setupEventListeners();
        this.setDefaultDate();
        this.loadSharkSpecies();
    }
    
    initializeMap() {
        // Initialize Leaflet map
        this.map = L.map('map').setView([20, 0], 2);
        
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
    }
    
    setDefaultDate() {
        // Set default date to today
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('target-date').value = today;
    }
    
    async loadSharkSpecies() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/species`);
            const species = await response.json();
            
            const select = document.getElementById('shark-species');
            select.innerHTML = '<option value="">Select a species...</option>';
            
            for (const [key, profile] of Object.entries(species)) {
                const option = document.createElement('option');
                option.value = key;
                option.textContent = profile.name;
                select.appendChild(option);
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
        
        button.disabled = !species || !date;
    }
    
    async predictHotspots() {
        const species = document.getElementById('shark-species').value;
        const date = document.getElementById('target-date').value;
        
        if (!species || !date) {
            this.showStatus('Please select both species and date', 'error');
            return;
        }
        
        this.showLoading(true);
        this.showStatus('Processing NASA satellite data...', 'loading');
        
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
            
            this.showStatus('Prediction completed successfully!', 'success');
            
        } catch (error) {
            console.error('Prediction failed:', error);
            this.showStatus(`Prediction failed: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    updateVisualization() {
        if (!this.currentData) return;
        
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
    }
    
    updatePolygons(features) {
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
                const popup = `
                    <h3>HSI Prediction</h3>
                    <p><strong>HSI Value:</strong> <span class="hsi-value">${feature.properties.hsi.toFixed(3)}</span></p>
                    <p><strong>Latitude:</strong> ${feature.properties.lat.toFixed(2)}°</p>
                    <p><strong>Longitude:</strong> ${feature.properties.lon.toFixed(2)}°</p>
                    <p><strong>Species:</strong> ${this.currentData.metadata.shark_species}</p>
                    <p><strong>Date:</strong> ${this.currentData.metadata.target_date}</p>
                `;
                layer.bindPopup(popup);
            }
        });
        
        this.hsiLayer.addTo(this.map);
        
        // Fit map to data bounds
        if (features.length > 0) {
            const bounds = this.hsiLayer.getBounds();
            this.map.fitBounds(bounds, { padding: [20, 20] });
        }
    }
    
    updateHeatmap(features) {
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
        this.map.setView([20, 0], 2);
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
