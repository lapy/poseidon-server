/**
 * Shark Foraging Hotspot Prediction - Frontend Application
 * Interactive map interface for visualizing HSI predictions
 */

class WaterRippleAnimation {
    constructor() {
        this.canvas = document.getElementById('ripple');
        this.ctx = this.canvas.getContext('2d');
        this.bubbles = [];
        this.time = 0;
        this.gradientOffset = 0;
        
        // Create initial bubbles
        for (let i = 0; i < 30; i++) {
            this.createNewBubble();
        }
        
        this.resize();
        this.animate();
        window.addEventListener('resize', () => this.resize());
        this.canvas.addEventListener('click', (e) => this.addBubbleBurst(e.clientX, e.clientY));
    }
    
    createNewBubble() {
        this.bubbles.push({
            x: Math.random() * this.canvas.width,
            y: this.canvas.height + 50, // Start below screen
            radius: 3 + Math.random() * 8, // Random size bubbles
            speed: 0.5 + Math.random() * 1.5, // Random rise speed
            wobble: Math.random() * Math.PI * 2, // For horizontal movement
            wobbleSpeed: 0.02 + Math.random() * 0.03,
            wobbleAmount: 10 + Math.random() * 30,
            opacity: 0.3 + Math.random() * 0.5
        });
    }
    
    addBubbleBurst(x, y) {
        // Create a burst of bubbles on click
        for (let i = 0; i < 5; i++) {
            this.bubbles.push({
                x: x + (Math.random() - 0.5) * 50,
                y: y,
                radius: 3 + Math.random() * 6,
                speed: 1 + Math.random() * 2,
                wobble: Math.random() * Math.PI * 2,
                wobbleSpeed: 0.03 + Math.random() * 0.05,
                wobbleAmount: 15 + Math.random() * 25,
                opacity: 0.5 + Math.random() * 0.3
            });
        }
    }
    
    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }
    
    animate() {
        this.time += 0.01;
        this.gradientOffset += 0.2;
        
        // Draw animated gradient background
        this.drawAnimatedBackground();
        
        // Update and draw bubbles
        for (let i = this.bubbles.length - 1; i >= 0; i--) {
            const bubble = this.bubbles[i];
            
            // Move bubble up
            bubble.y -= bubble.speed;
            
            // Add wobble effect (side-to-side movement)
            bubble.wobble += bubble.wobbleSpeed;
            bubble.x += Math.sin(bubble.wobble) * 0.5;
            
            // Remove bubble if it goes off screen
            if (bubble.y < -50) {
                this.bubbles.splice(i, 1);
                this.createNewBubble(); // Create a new one at the bottom
                continue;
            }
            
            // Draw the bubble
            this.drawBubble(bubble);
        }
        
        requestAnimationFrame(() => this.animate());
    }
    
    drawAnimatedBackground() {
        const gradient = this.ctx.createLinearGradient(
            0, 0,
            this.canvas.width, this.canvas.height
        );
        
        // Create moving gradient effect by shifting color stops
        const offset = (Math.sin(this.time * 0.5) + 1) * 0.1;
        
        gradient.addColorStop(0 + offset, 'rgba(12, 74, 110, 0.3)');
        gradient.addColorStop(0.25 + offset, 'rgba(7, 89, 133, 0.3)');
        gradient.addColorStop(0.5 + offset, 'rgba(3, 105, 161, 0.3)');
        gradient.addColorStop(0.75 + offset, 'rgba(2, 132, 199, 0.3)');
        gradient.addColorStop(1, 'rgba(14, 165, 233, 0.3)');
        
        this.ctx.fillStyle = gradient;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }
    
    drawBubble(bubble) {
        // Draw bubble with highlight for 3D effect
        const gradient = this.ctx.createRadialGradient(
            bubble.x - bubble.radius * 0.3,
            bubble.y - bubble.radius * 0.3,
            bubble.radius * 0.1,
            bubble.x,
            bubble.y,
            bubble.radius
        );
        
        gradient.addColorStop(0, `rgba(255, 255, 255, ${bubble.opacity * 0.8})`);
        gradient.addColorStop(0.3, `rgba(173, 216, 230, ${bubble.opacity * 0.6})`);
        gradient.addColorStop(0.7, `rgba(96, 165, 250, ${bubble.opacity * 0.4})`);
        gradient.addColorStop(1, `rgba(96, 165, 250, ${bubble.opacity * 0.1})`);
        
        // Draw main bubble
        this.ctx.fillStyle = gradient;
        this.ctx.beginPath();
        this.ctx.arc(bubble.x, bubble.y, bubble.radius, 0, Math.PI * 2);
        this.ctx.fill();
        
        // Draw bubble outline
        this.ctx.strokeStyle = `rgba(255, 255, 255, ${bubble.opacity * 0.5})`;
        this.ctx.lineWidth = 1;
        this.ctx.beginPath();
        this.ctx.arc(bubble.x, bubble.y, bubble.radius, 0, Math.PI * 2);
        this.ctx.stroke();
        
        // Draw highlight spot (makes it look more realistic)
        this.ctx.fillStyle = `rgba(255, 255, 255, ${bubble.opacity * 0.9})`;
        this.ctx.beginPath();
        this.ctx.arc(
            bubble.x - bubble.radius * 0.35,
            bubble.y - bubble.radius * 0.35,
            bubble.radius * 0.25,
            0,
            Math.PI * 2
        );
        this.ctx.fill();
    }
}
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
    // Start water ripple animation
    new WaterRippleAnimation();
    
    // Start main application
    new SharkHotspotApp();
});
