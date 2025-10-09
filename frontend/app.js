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
        this.allFeatures = null; // Store all unfiltered features for client-side filtering
        this.isHeatmapMode = false;
        
        // Overlay layers (Enhanced Model Indices v2.0)
        this.overlayLayers = {
            i_phys: null,
            i_prey: null,
            i_topo: null,
            i_anthro: null
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
            maxZoom: 9,  // Maximum zoom level (prevents over-zooming beyond 0.5° data resolution ~55km)
            maxBounds: [
                [-90, -180], // Southwest corner
                [90, 180]    // Northeast corner
            ],
            maxBoundsViscosity: 1.0 // Keep bounds strict
        }).setView([50, 10], 4); // Focus on Europe
        
        // Add base tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 18  // Tile layer supports higher zoom, but map restricts to zoom 9
        }).addTo(this.map);
        
        // Initialize heatmap layer (default for performance)
        this.heatmapLayer = L.heatLayer([], {
            radius: 20,
            blur: 12,
            maxZoom: 17,
            max: 1.0,
            gradient: {
                0.0: 'rgba(139, 0, 0, 0.3)',      // Dark red - unsuitable
                0.2: 'rgba(255, 69, 0, 0.5)',     // Orange-red
                0.4: 'rgba(255, 165, 0, 0.6)',    // Orange
                0.6: 'rgba(255, 255, 0, 0.7)',    // Yellow
                0.8: 'rgba(144, 238, 144, 0.8)',  // Light green
                1.0: 'rgba(0, 100, 0, 1.0)'       // Dark green - most suitable
            }
        }).addTo(this.map); // Add heatmap by default for better performance
        
        // Set initial visualization mode to heatmap
        this.visualizationMode = 'heatmap';
        
        console.log('Map initialized with heatmap as default visualization');
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
        
        // Status notification close button
        document.getElementById('status-close').addEventListener('click', () => {
            this.hideStatus();
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
        // Set default date to 60 days ago (NASA data has ~30 day processing delay)
        const defaultDate = new Date();
        defaultDate.setDate(defaultDate.getDate() - 60);
        const dateString = defaultDate.toISOString().split('T')[0];
        document.getElementById('target-date').value = dateString;
        
        // Set max date to 30 days ago to prevent selecting recent dates
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
        document.getElementById('target-date').max = thirtyDaysAgo.toISOString().split('T')[0];
        
        // Set min date to 2 years ago (reasonable data availability window)
        const twoYearsAgo = new Date();
        twoYearsAgo.setFullYear(twoYearsAgo.getFullYear() - 2);
        document.getElementById('target-date').min = twoYearsAgo.toISOString().split('T')[0];
        
        console.log(`Date range: ${twoYearsAgo.toISOString().split('T')[0]} to ${thirtyDaysAgo.toISOString().split('T')[0]}`);
        console.log(`Default date: ${dateString}`);
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
        
        // Hide overlay controls and clear any existing overlays
        this.hideOverlayControls();
        this.clearAllOverlays();

        try {
            // Always fetch with threshold=0.0 to get all grid points
            // Frontend will filter based on user's threshold slider
            const url = `${this.apiBaseUrl}/hotspots?target_date=${date}&shark_species=${species}&format=geojson&threshold=0.0`;
            
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Store the complete unfiltered data
            this.currentData = data;
            this.allFeatures = data.features; // Store all features for filtering
            
            // Check if we have any features
            if (!data.features || data.features.length === 0) {
                this.showStatus(`No habitat data available. Try using a different date (30-60 days ago recommended).`, 'warning');
                this.showLoading(false);
                return;
            }
            
            // Apply client-side threshold filtering
            this.updateVisualization();
            this.updateResultsPanel(data.metadata);
            
            // Show overlay controls after successful HSI calculation
            this.showOverlayControls();
            
            const threshold = parseFloat(document.getElementById('hsi-threshold').value);
            const filteredCount = this.currentData.features.filter(f => f.properties.hsi >= threshold).length;
            this.showStatus(`Prediction completed! ${filteredCount} suitable habitat areas above threshold ${threshold.toFixed(2)}.`, 'success');
            
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
    
    showOverlayControls() {
        // Show the overlay controls section
        const overlayControls = document.getElementById('overlay-controls');
        if (overlayControls) {
            overlayControls.style.display = 'block';
            console.log('Overlay controls shown');
        }
    }
    
    hideOverlayControls() {
        // Hide the overlay controls section
        const overlayControls = document.getElementById('overlay-controls');
        if (overlayControls) {
            overlayControls.style.display = 'none';
            console.log('Overlay controls hidden');
        }
        
        // Reset all overlay checkboxes
        const overlayIds = ['i_phys', 'i_prey', 'i_topo', 'i_anthro'];
        overlayIds.forEach(overlayId => {
            const checkbox = document.getElementById(`${overlayId}-overlay`);
            if (checkbox) {
                checkbox.checked = false;
            }
        });
    }
    
    clearAllOverlays() {
        // Remove all overlay layers from the map
        const overlayIds = ['i_phys', 'i_prey', 'i_topo', 'i_anthro'];
        overlayIds.forEach(overlayType => {
            if (this.overlayLayers[overlayType]) {
                this.map.removeLayer(this.overlayLayers[overlayType]);
                this.overlayLayers[overlayType] = null;
            }
        });
        
        // Update overlay legend visibility
        this.updateOverlayLegend();
        
        console.log('All overlays cleared');
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
        // Add overlay toggle event listeners for enhanced model indices
        try {
            const overlayIds = ['i_phys', 'i_prey', 'i_topo', 'i_anthro'];
            
            overlayIds.forEach(overlayId => {
                const element = document.getElementById(`${overlayId}-overlay`);
                if (element) {
                    element.addEventListener('change', (e) => {
                        this.toggleOverlay(overlayId, e.target.checked);
                });
            } else {
                    console.warn(`${overlayId} overlay element not found`);
                }
            });
            
            console.log('Enhanced model overlay listeners setup complete');
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
    
    addOverlayLayer(type) {
        if (!this.allFeatures || this.allFeatures.length === 0) {
            console.warn('No prediction data available for overlay');
            return;
        }
        
        console.log(`Creating ${type} overlay from full HSI dataset...`);
        
        // Use ALL features (not filtered by threshold) so indices can be viewed everywhere
        // Extract features that have the requested index type
        const overlayFeatures = this.allFeatures.filter(feature => 
            feature.properties && feature.properties[type] !== undefined
        );
        
        if (overlayFeatures.length === 0) {
            console.warn(`No ${type} data found in HSI response`);
            this.showStatus(`${type} data not available in current prediction`, 'warning');
            return;
        }
        
        console.log(`Found ${overlayFeatures.length} features with ${type} data`);
        
        // Create overlay data structure
        const overlayData = {
            type: "FeatureCollection",
            features: overlayFeatures
        };
        
        // Create overlay layer
        const layer = this.createIndexOverlay(type, overlayData);
        
        if (layer) {
            this.overlayLayers[type] = layer.addTo(this.map);
            console.log(`Added ${type} overlay layer to map`);
        }
    }
    
    createIndexOverlay(indexType, data) {
        console.log(`Creating ${indexType} overlay`);
        
        // Define colors for each index type
        const indexColors = {
            'i_phys': '#667eea',      // Purple-blue for physicochemical
            'i_prey': '#f093fb',      // Pink for prey availability
            'i_topo': '#4facfe',      // Light blue for topography
            'i_anthro': '#e74c3c'     // Red for anthropogenic pressure
        };
        
        const indexNames = {
            'i_phys': '🌊 Water Conditions',
            'i_prey': '🐟 Food Availability (Productivity-based)',
            'i_topo': '🗺️ Seafloor Quality',
            'i_anthro': '🚢 Human Impact'
        };
        
        return L.geoJSON(data, {
            renderer: L.canvas({ padding: 0.5 }), // Use Canvas for overlay layers too
            style: (feature) => {
                const value = feature.properties[indexType] || 0;
                // Value is already normalized (0-1) from HSI calculation
                const normalized = Math.min(Math.max(value, 0), 1);
                
                // Configure visibility thresholds and opacity
                // Anthropogenic data uses high threshold because many coastal areas
                // reach max values due to 95th-percentile normalization
                let threshold, maxOpacity;
                
                if (indexType === 'i_anthro') {
                    // Anthropogenic: Mediterranean is extremely heavily fished
                    // At 0.5° resolution, coastal grid cells include both sea and land
                    // Solution: Ultra-high threshold + minimal opacity for barely-visible indication
                    threshold = 0.97;   // Only show extreme outliers (top 3%)
                    maxOpacity = 0.15;  // Barely visible - just the faintest red hint
                } else {
                    // Other indices: moderate threshold
                    threshold = 0.05;
                    maxOpacity = 0.7;
                }
                
                // Calculate opacity with smooth scaling above threshold
                const fillOpacity = normalized > threshold ? (normalized - threshold) / (1 - threshold) * maxOpacity : 0;
                const strokeOpacity = normalized > threshold ? 0.4 : 0;
                
                return {
                    fillColor: indexColors[indexType],
                    fillOpacity: fillOpacity,
                    color: indexColors[indexType],
                    weight: 1,
                    opacity: strokeOpacity
                };
            },
            onEachFeature: (feature, layer) => {
                const value = feature.properties[indexType] || 0;
                const popup = `
                    <h3>${indexNames[indexType]}</h3>
                    <p><strong>Index Value:</strong> <span style="color: ${indexColors[indexType]}; font-weight: bold;">${value.toFixed(3)}</span></p>
                    <p><strong>Latitude:</strong> ${feature.properties.lat.toFixed(2)}°</p>
                    <p><strong>Longitude:</strong> ${feature.properties.lon.toFixed(2)}°</p>
                    <p class="index-description">${this.getIndexDescription(indexType)}</p>
                `;
                layer.bindPopup(popup);
            }
        });
    }
    
    getIndexDescription(indexType) {
        const descriptions = {
            'i_phys': '<small>Water conditions including temperature, salinity, oxygen levels, and ocean features like eddies and fronts</small>',
            'i_prey': '<small>Food availability based on ocean productivity (chlorophyll as baseline). <strong>Note:</strong> Direct prey tracking data not yet available - using productivity as proxy.</small>',
            'i_topo': '<small>Seafloor characteristics including water depth and seafloor slope that sharks prefer</small>',
            'i_anthro': '<small><strong>Anthropogenic Pressure Index:</strong> Human impact from fishing activity (Global Fishing Watch) and vessel traffic density. Shown with minimal transparency - only the most extreme fishing zones (top 3%) are visible. Note: At 0.5° resolution (~55km), coastal cells naturally include both water and land. Data from GFW API.</small>'
        };
        return descriptions[indexType] || '';
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
        
        // Filter features by threshold (client-side filtering)
        // Use allFeatures if available (full dataset), otherwise use current features
        const sourceFeatures = this.allFeatures || this.currentData.features;
        const filteredFeatures = sourceFeatures.filter(feature => 
            feature.properties.hsi >= threshold
        );
        
        // Update the current data features with filtered results for rendering
        this.currentData.features = filteredFeatures;
        
        // Clear existing layers
        if (this.hsiLayer) {
            this.map.removeLayer(this.hsiLayer);
        }
        
        if (this.isHeatmapMode) {
            this.updateHeatmap(filteredFeatures);
        } else {
            this.updatePolygons(filteredFeatures);
        }
        
        // Update overlays if they are enabled (overlays use full dataset for all indices)
        this.updateEnabledOverlays();
    }
    
    updateEnabledOverlays() {
        // Update all enabled enhanced model index overlays
        const overlayIds = ['i_phys', 'i_prey', 'i_topo', 'i_anthro'];
        
        overlayIds.forEach(overlayType => {
            const checkbox = document.getElementById(`${overlayType}-overlay`);
            if (checkbox && checkbox.checked && this.overlayLayers[overlayType]) {
                // Recreate the overlay with current data
                this.map.removeLayer(this.overlayLayers[overlayType]);
                this.overlayLayers[overlayType] = null;
                this.addOverlayLayer(overlayType);
            }
        });
    }
    
    updatePolygons(features) {
        if (!this.map) return;
        
        // Optimize: For large datasets, reduce polygon complexity
        let optimizedFeatures = features;
        if (features.length > 100000) {
            // Simplify polygons to points at high zoom levels for performance
            console.log(`Large dataset (${features.length} features) - optimizing for performance`);
            // Keep all features but simplify rendering
        }
        
        // Create polygon layer with Canvas renderer for much better performance
        this.hsiLayer = L.geoJSON(optimizedFeatures, {
            renderer: L.canvas({ padding: 0.5 }), // Canvas is 10-100x faster than SVG for many polygons
            style: (feature) => ({
                fillColor: this.getHSIColor(feature.properties.hsi),
                fillOpacity: 0.7,
                color: 'white',
                weight: 1,
                opacity: 0.5
            }),
            onEachFeature: (feature, layer) => {
                // Performance: For large datasets (>100k features), only show popup on click
                const useClickOnly = features.length > 100000;
                
                // Get component contributions if available
                const contributions = feature.properties.component_contributions || {};
                const hasEnhancedModel = contributions.physicochemical_pct !== undefined;
                const hasLegacyContributions = contributions.chlorophyll !== undefined;
                
                // Determine if this is enhanced model (v2.0) or legacy (v1.0)
                const isEnhancedModel = feature.properties.i_phys !== undefined;

                let popup = `
                    <h3>🦈 HSI Prediction</h3>
                    <p><strong>HSI Value:</strong> <span class="hsi-value hsi-high">${feature.properties.hsi.toFixed(3)}</span></p>
                `;

                // Enhanced Model Display (v2.0)
                if (isEnhancedModel) {
                    popup += `
                        <div class="model-badge">Enhanced Model v2.0</div>
                        
                        <div class="hsi-indices">
                            <h4>🔬 Habitat Quality Factors:</h4>
                            <div class="index-grid">
                                <div class="index-item">
                                    <span class="index-label" title="Water conditions: temperature, salinity, oxygen, and oceanographic features (eddies & fronts)">
                                        🌊 Water Conditions:
                                    </span>
                                    <span class="index-value">${feature.properties.i_phys?.toFixed(3) || 'N/A'}</span>
                                    ${hasEnhancedModel ? `<span class="index-contrib">(${contributions.physicochemical_pct?.toFixed(1) || '0'}%)</span>` : ''}
                                </div>
                                <div class="index-item">
                                    <span class="index-label" title="Food availability based on ocean productivity. Uses chlorophyll as baseline proxy for marine food web productivity.">
                                        🐟 Food Availability:
                                    </span>
                                    <span class="index-value">${feature.properties.i_prey?.toFixed(3) || 'N/A'}</span>
                                    ${hasEnhancedModel ? `<span class="index-contrib">(${contributions.prey_pct?.toFixed(1) || '0'}%)</span>` : ''}
                                </div>
                                <div class="index-item">
                                    <span class="index-label" title="Seafloor characteristics: depth and slope preferences">
                                        🗺️ Seafloor Quality:
                                    </span>
                                    <span class="index-value">${feature.properties.i_topo?.toFixed(3) || 'N/A'}</span>
                                    ${hasEnhancedModel ? `<span class="index-contrib">(${contributions.topographic_pct?.toFixed(1) || '0'}%)</span>` : ''}
                                </div>
                                <div class="index-item anthropogenic">
                                    <span class="index-label" title="Human activity impact from fishing and shipping (Global Fishing Watch). Shows displacement risk - higher values mean sharks avoid these areas.">
                                        🚢 Human Impact:
                                    </span>
                                    <span class="index-value">${feature.properties.i_anthro?.toFixed(3) || 'N/A'}</span>
                                    ${hasEnhancedModel ? `<span class="index-contrib warning">(${contributions.anthropogenic_reduction_pct?.toFixed(1) || '0'}%)</span>` : ''}
                                </div>
                            </div>
                            ${hasEnhancedModel ? `
                                <div class="hsi-breakdown">
                                    <div class="breakdown-item">
                                        <span>📈 Natural Habitat Score:</span>
                                        <span class="value">${contributions.base_hsi?.toFixed(3) || 'N/A'}</span>
                                    </div>
                                    <div class="breakdown-item">
                                        <span>🎯 Final Habitat Score:</span>
                                        <span class="value">${contributions.final_hsi?.toFixed(3) || 'N/A'}</span>
                                    </div>
                                </div>
                            ` : ''}
                        </div>

                        <div class="hsi-components">
                            <h4>📊 Individual Environmental Factors:</h4>
                            <div class="component-grid">
                                <div class="component-item">
                                    <span class="component-label">🌡️ Water Temperature:</span>
                                    <span class="component-value">${feature.properties.temperature_suitability?.toFixed(3) || 'N/A'}</span>
                                </div>
                                <div class="component-item">
                                    <span class="component-label">🧂 Salt Content:</span>
                                    <span class="component-value">${feature.properties.salinity_suitability?.toFixed(3) || 'N/A'}</span>
                                </div>
                                <div class="component-item">
                                    <span class="component-label">💨 Oxygen Levels:</span>
                                    <span class="component-value">${feature.properties.oxygen_suitability?.toFixed(3) || 'N/A'}</span>
                                </div>
                                <div class="component-item">
                                    <span class="component-label">🌿 Productivity (Chlorophyll):</span>
                                    <span class="component-value">${feature.properties.chlorophyll_suitability?.toFixed(3) || 'N/A'}</span>
                                </div>
                                <div class="component-item">
                                    <span class="component-label">🌀 Ocean Features (Eddies/Fronts):</span>
                                    <span class="component-value">${feature.properties.oceanographic_suitability?.toFixed(3) || 'N/A'}</span>
                                </div>
                            </div>
                        </div>
                        
                        ${hasEnhancedModel ? `
                            <div class="contribution-note">
                                <strong>How it works:</strong> This score combines water conditions, food availability (based on ocean productivity), and seafloor quality. Human impact from fishing and shipping reduces the score in areas with high activity.<br>
                                <em>💡 Percentages show how much each factor contributes to the habitat quality</em><br>
                                <em>ℹ️ Note: Direct prey tracking data not yet available - using chlorophyll as productivity proxy</em>
                            </div>
                        ` : ''}
                    `;
                } else {
                    // Legacy Model Display (v1.0)
                    popup += `
                        <div class="model-badge legacy">Legacy Model v1.0</div>
                        
                    <div class="hsi-components">
                        <h4>Suitability Components:</h4>
                        <div class="component-grid">
                            <div class="component-item">
                                <span class="component-label">Temperature:</span>
                                <span class="component-value">${feature.properties.temperature_suitability?.toFixed(3) || 'N/A'}</span>
                                    ${hasLegacyContributions ? `<span class="component-contrib">(${contributions.temperature?.toFixed(1) || '0.0'}%)</span>` : ''}
                            </div>
                            <div class="component-item">
                                <span class="component-label">Chlorophyll:</span>
                                <span class="component-value">${feature.properties.chlorophyll_suitability?.toFixed(3) || 'N/A'}</span>
                                    ${hasLegacyContributions ? `<span class="component-contrib">(${contributions.chlorophyll?.toFixed(1) || '0.0'}%)</span>` : ''}
                            </div>
                            <div class="component-item">
                                <span class="component-label">Oceanographic:</span>
                                <span class="component-value">${feature.properties.oceanographic_suitability?.toFixed(3) || 'N/A'}</span>
                                    ${hasLegacyContributions ? `<span class="component-contrib">(${contributions.oceanographic?.toFixed(1) || '0.0'}%)</span>` : ''}
                            </div>
                            <div class="component-item">
                                <span class="component-label">Salinity:</span>
                                <span class="component-value">${feature.properties.salinity_suitability?.toFixed(3) || 'N/A'}</span>
                            </div>
                        </div>
                            ${hasLegacyContributions ? `<div class="contribution-note">* Percentages show relative contribution to HSI score</div>` : ''}
                        </div>
                    `;
                }

                popup += `
                    <div class="location-info">
                        <p><strong>📍 Location:</strong> ${feature.properties.lat.toFixed(2)}°, ${feature.properties.lon.toFixed(2)}°</p>
                        <p><strong>🦈 Species:</strong> ${this.currentData.metadata.shark_species}</p>
                        <p><strong>📅 Date:</strong> ${this.currentData.metadata.target_date}</p>
                    </div>
                `;
                
                // Performance: For large datasets, disable popups (use heatmap instead)
                if (!useClickOnly) {
                    layer.bindPopup(popup, {
                        maxWidth: 450,
                        maxHeight: 500,
                        autoPan: true,
                        autoPanPadding: [50, 50],
                        className: 'enhanced-popup'
                    });
                }
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
        // Higher HSI = more suitable habitat = greener color
        if (hsi >= 0.8) return '#006400';      // Dark green - most suitable
        if (hsi >= 0.6) return '#90EE90';      // Light green
        if (hsi >= 0.4) return '#FFFF00';      // Yellow
        if (hsi >= 0.2) return '#FFA500';      // Orange
        if (hsi >= 0.0) return '#FF4500';      // Orange-red - unsuitable
        return '#8B0000';                       // Dark red - very unsuitable
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
        const overviewDiv = document.getElementById('result-overview');
        const statsDiv = document.getElementById('result-stats');
        const modelDiv = document.getElementById('result-model');
        const dataDiv = document.getElementById('result-data');
        
        // Overview Section
        const featureCount = this.currentData.features.length;
        const totalFeatures = this.allFeatures ? this.allFeatures.length : featureCount;
        const threshold = parseFloat(document.getElementById('hsi-threshold').value);
        const modelVersion = metadata.model_version || 'Enhanced Model v2.0';
        
        overviewDiv.innerHTML = `
            <h4><i class="fas fa-info-circle"></i> Overview</h4>
            <div class="result-highlight">
                <div class="stat-item" style="margin-bottom: 0;">
                    <span class="stat-label">Suitable Habitat Areas:</span>
                    <span class="stat-value">${featureCount.toLocaleString()}</span>
                </div>
            </div>
            <div class="stat-item">
                <span class="stat-label">Total Grid Cells:</span>
                <span class="stat-value">${totalFeatures.toLocaleString()}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Species:</span>
                <span class="stat-value">${metadata.shark_species || 'N/A'}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Target Date:</span>
                <span class="stat-value">${metadata.target_date || 'N/A'}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">HSI Threshold:</span>
                <span class="stat-value">${threshold.toFixed(2)}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Model Version:</span>
                <span class="stat-value">${modelVersion}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Processing Area:</span>
                <span class="stat-value">${metadata.processing_area || 'Global'}</span>
            </div>
        `;
        
        // Statistics Section
        if (metadata.statistics) {
            const stats = metadata.statistics;
            statsDiv.innerHTML = `
                <h4><i class="fas fa-chart-bar"></i> HSI Statistics</h4>
                <div class="stat-item">
                    <span class="stat-label">Mean HSI:</span>
                    <span class="stat-value">${stats.mean?.toFixed(3) || 'N/A'}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Std Deviation:</span>
                    <span class="stat-value">${stats.std?.toFixed(3) || 'N/A'}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Min HSI:</span>
                    <span class="stat-value">${stats.min?.toFixed(3) || 'N/A'}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Max HSI:</span>
                    <span class="stat-value">${stats.max?.toFixed(3) || 'N/A'}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">90th Percentile:</span>
                    <span class="stat-value">${stats.percentile_90?.toFixed(3) || 'N/A'}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">95th Percentile:</span>
                    <span class="stat-value">${stats.percentile_95?.toFixed(3) || 'N/A'}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">99th Percentile:</span>
                    <span class="stat-value">${stats.percentile_99?.toFixed(3) || 'N/A'}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Valid Data Points:</span>
                    <span class="stat-value">${stats.valid_points?.toLocaleString() || 'N/A'}</span>
                </div>
            `;
        }
        
        // Model Parameters Section
        if (metadata.model_parameters) {
            const params = metadata.model_parameters;
            const speciesName = params.name || metadata.shark_species || 'Shark';
            let paramsHtml = `
                <h4><i class="fas fa-fish"></i> ${speciesName} Ecological Profile</h4>
                <p style="color: var(--text-light); font-size: 0.85rem; margin-bottom: 0.5rem; font-style: italic;">
                    Species-specific habitat preferences and behavioral parameters
                </p>
                <div class="ecological-params">
            `;
            
            // Column 1: Water Chemistry & Physical Conditions
            paramsHtml += '<div class="param-group">';
            
            // Temperature Parameters
            paramsHtml += '<div style="margin-bottom: 0.75rem;"><strong style="color: var(--primary-color); font-size: 0.9rem;">🌡️ Temperature</strong></div>';
            paramsHtml += `
                <div class="stat-item">
                    <span class="stat-label">Optimal:</span>
                    <span class="stat-value">${params.s_opt?.toFixed(1)}°C</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Tolerance:</span>
                    <span class="stat-value">±${params.sigma_s?.toFixed(1)}°C</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Lag:</span>
                    <span class="stat-value">${params.t_lag} days</span>
                </div>
            `;
            
            // Salinity Parameters
            paramsHtml += '<div style="margin: 1rem 0 0.75rem;"><strong style="color: var(--primary-color); font-size: 0.9rem;">🧂 Salinity</strong></div>';
            paramsHtml += `
                <div class="stat-item">
                    <span class="stat-label">Range:</span>
                    <span class="stat-value">${params.salinity_min?.toFixed(1)}-${params.salinity_max?.toFixed(1)} PSU</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Optimal:</span>
                    <span class="stat-value">${params.salinity_opt_min?.toFixed(1)}-${params.salinity_opt_max?.toFixed(1)} PSU</span>
                </div>
            `;
            
            // Oxygen Parameters
            paramsHtml += '<div style="margin: 1rem 0 0.75rem;"><strong style="color: var(--primary-color); font-size: 0.9rem;">💨 Oxygen</strong></div>';
            paramsHtml += `
                <div class="stat-item">
                    <span class="stat-label">Minimum:</span>
                    <span class="stat-value">${params.oxygen_min?.toFixed(1)} mg/L</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Optimal:</span>
                    <span class="stat-value">${params.oxygen_opt?.toFixed(1)} mg/L</span>
                </div>
            `;
            
            paramsHtml += '</div>'; // Close param-group 1
            
            // Column 2: Habitat & Topology
            paramsHtml += '<div class="param-group">';
            
            // Depth Parameters
            paramsHtml += '<div style="margin-bottom: 0.75rem;"><strong style="color: var(--primary-color); font-size: 0.9rem;">🌊 Depth</strong></div>';
            paramsHtml += `
                <div class="stat-item">
                    <span class="stat-label">Range:</span>
                    <span class="stat-value">${params.depth_min?.toLocaleString()}-${params.depth_max?.toLocaleString()}m</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Optimal:</span>
                    <span class="stat-value">${params.depth_opt_min?.toLocaleString()}-${params.depth_opt_max?.toLocaleString()}m</span>
                </div>
            `;
            
            // Seafloor Slope
            paramsHtml += '<div style="margin: 1rem 0 0.75rem;"><strong style="color: var(--primary-color); font-size: 0.9rem;">🗻 Seafloor</strong></div>';
            paramsHtml += `
                <div class="stat-item">
                    <span class="stat-label">Optimal Slope:</span>
                    <span class="stat-value">${params.slope_opt?.toFixed(1)}°</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Tolerance:</span>
                    <span class="stat-value">±${params.slope_sigma?.toFixed(1)}°</span>
                </div>
            `;
            
            // Oceanographic Features
            if (params.w_eddy !== undefined || params.w_front !== undefined) {
                paramsHtml += '<div style="margin: 1rem 0 0.75rem;"><strong style="color: var(--primary-color); font-size: 0.9rem;">🌀 Oceanographic</strong></div>';
                paramsHtml += `
                    <div class="stat-item">
                        <span class="stat-label">Eddy Weight:</span>
                        <span class="stat-value">${(params.w_eddy * 100)?.toFixed(0)}%</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Front Weight:</span>
                        <span class="stat-value">${(params.w_front * 100)?.toFixed(0)}%</span>
                    </div>
                `;
            }
            
            paramsHtml += '</div>'; // Close param-group 2
            
            // Column 3: Diet & Productivity
            paramsHtml += '<div class="param-group">';
            
            // Chlorophyll/Productivity
            paramsHtml += '<div style="margin-bottom: 0.75rem;"><strong style="color: var(--primary-color); font-size: 0.9rem;">🌿 Productivity</strong></div>';
            paramsHtml += `
                <div class="stat-item">
                    <span class="stat-label">Chlorophyll:</span>
                    <span class="stat-value">${(params.w_chl * 100)?.toFixed(0)}%</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Lag:</span>
                    <span class="stat-value">${params.c_lag} days</span>
                </div>
            `;
            
            // Prey Weights
            paramsHtml += '<div style="margin: 1rem 0 0.75rem;"><strong style="color: var(--primary-color); font-size: 0.9rem;">🐟 Diet</strong></div>';
            paramsHtml += `
                <div class="stat-item">
                    <span class="stat-label">Pinnipeds:</span>
                    <span class="stat-value">${(params.w_prey_pinnipeds * 100)?.toFixed(0)}%</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Sea Turtles:</span>
                    <span class="stat-value">${(params.w_prey_turtles * 100)?.toFixed(0)}%</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Fish:</span>
                    <span class="stat-value">${(params.w_prey_fish * 100)?.toFixed(0)}%</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Cephalopods:</span>
                    <span class="stat-value">${(params.w_prey_cephalopods * 100)?.toFixed(0)}%</span>
                </div>
            `;
            
            paramsHtml += '</div>'; // Close param-group 3
            
            // Column 4: Behavioral Priorities
            paramsHtml += '<div class="param-group">';
            
            // Model Weights
            paramsHtml += '<div style="margin-bottom: 0.75rem;"><strong style="color: var(--primary-color); font-size: 0.9rem;">⚖️ Priorities</strong></div>';
            paramsHtml += `
                <div class="stat-item">
                    <span class="stat-label">Water:</span>
                    <span class="stat-value">${(params.w_phys * 100)?.toFixed(0)}%</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Food:</span>
                    <span class="stat-value">${(params.w_prey * 100)?.toFixed(0)}%</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Seafloor:</span>
                    <span class="stat-value">${(params.w_topo * 100)?.toFixed(0)}%</span>
                </div>
            `;
            
            paramsHtml += '</div>'; // Close param-group 4
            paramsHtml += '</div>'; // Close ecological-params grid
            
            modelDiv.innerHTML = paramsHtml;
        }
        
        // Data Sources Section
        const laggedData = metadata.lagged_data_available || {};
        const gfwData = metadata.anthropogenic_data_available || {};
        
        let dataBadges = '';
        
        // Environmental data
        if (laggedData.temperature !== false) {
            dataBadges += `<span class="data-badge success"><i class="fas fa-check"></i> Temperature</span>`;
        }
        if (laggedData.chlorophyll !== false) {
            dataBadges += `<span class="data-badge success"><i class="fas fa-check"></i> Chlorophyll</span>`;
        }
        if (laggedData.salinity !== false) {
            dataBadges += `<span class="data-badge success"><i class="fas fa-check"></i> Salinity</span>`;
        }
        if (laggedData.oxygen !== false) {
            dataBadges += `<span class="data-badge success"><i class="fas fa-check"></i> Oxygen</span>`;
        }
        if (laggedData.sea_level !== false) {
            dataBadges += `<span class="data-badge success"><i class="fas fa-check"></i> Sea Level</span>`;
        }
        
        // GFW data
        if (gfwData.fishing) {
            dataBadges += `<span class="data-badge success"><i class="fas fa-ship"></i> Fishing Activity</span>`;
        } else {
            dataBadges += `<span class="data-badge warning"><i class="fas fa-times"></i> Fishing Activity</span>`;
        }
        
        if (gfwData.shipping) {
            dataBadges += `<span class="data-badge success"><i class="fas fa-ship"></i> Vessel Traffic</span>`;
        } else {
            dataBadges += `<span class="data-badge warning"><i class="fas fa-times"></i> Vessel Traffic</span>`;
        }
        
        dataDiv.innerHTML = `
            <h4><i class="fas fa-database"></i> Data Sources</h4>
            <div style="margin-bottom: 1rem;">
                ${dataBadges}
            </div>
            ${metadata.data_sources ? `
                <div class="stat-item">
                    <span class="stat-label">Temperature Source:</span>
                    <span class="stat-value">${metadata.data_sources.temperature || 'CMEMS'}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Chlorophyll Source:</span>
                    <span class="stat-value">${metadata.data_sources.chlorophyll || 'NASA'}</span>
                </div>
            ` : ''}
            <div class="stat-item">
                <span class="stat-label">Anthropogenic Data:</span>
                <span class="stat-value">
                    ${gfwData.fishing ? '✓' : '✗'} Fishing, 
                    ${gfwData.shipping ? '✓' : '✗'} Shipping
                </span>
            </div>
            ${metadata.anthropogenic_data_source ? `
                <div class="stat-item">
                    <span class="stat-label">GFW Attribution:</span>
                    <span class="stat-value" style="font-size: 0.8rem;">${metadata.anthropogenic_data_source}</span>
                </div>
            ` : ''}
            ${metadata.cache_performance ? `
                <div class="stat-item">
                    <span class="stat-label">Cache Hits:</span>
                    <span class="stat-value">${metadata.cache_performance.hits || 0}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Processing Time:</span>
                    <span class="stat-value">${metadata.cache_performance.processing_time?.toFixed(2) || 'N/A'}s</span>
                </div>
            ` : ''}
        `;
        
        panel.style.display = 'block';
    }
    
    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        overlay.style.display = show ? 'flex' : 'none';
    }
    
    showStatus(message, type = 'info', autoDismiss = true) {
        const indicator = document.getElementById('status-indicator');
        const icon = indicator.querySelector('i');
        const text = indicator.querySelector('span');
        const closeBtn = document.getElementById('status-close');
        
        // Clear any existing timeout
        if (this.statusTimeout) {
            clearTimeout(this.statusTimeout);
            this.statusTimeout = null;
        }
        
        // Remove existing classes
        indicator.className = 'status-indicator show';
        
        // Add type class
        if (type !== 'info') {
            indicator.classList.add(type);
        }
        
        // Update icon and text
        text.textContent = message;
        
        // Update icon based on type
        switch (type) {
            case 'loading':
                icon.className = 'fas fa-spinner fa-spin';
                autoDismiss = false; // Don't auto-dismiss loading states
                closeBtn.style.display = 'none'; // Hide close button for loading
                break;
            case 'success':
                icon.className = 'fas fa-check-circle';
                closeBtn.style.display = 'flex'; // Show close button
                break;
            case 'error':
                icon.className = 'fas fa-exclamation-circle';
                closeBtn.style.display = 'flex'; // Show close button
                break;
            case 'warning':
                icon.className = 'fas fa-exclamation-triangle';
                closeBtn.style.display = 'flex'; // Show close button
                break;
            default:
                icon.className = 'fas fa-info-circle';
                closeBtn.style.display = 'flex'; // Show close button
        }
        
        // Auto-dismiss after 5 seconds (except loading states)
        if (autoDismiss && type !== 'loading') {
            this.statusTimeout = setTimeout(() => {
                this.hideStatus();
            }, 5000);
        }
    }
    
    hideStatus() {
        const indicator = document.getElementById('status-indicator');
        
        // Add hiding animation
        indicator.classList.add('hiding');
        
        // Remove after animation completes
        setTimeout(() => {
            indicator.classList.remove('show', 'hiding');
        }, 400); // Match the animation duration
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new SharkHotspotApp();
});
