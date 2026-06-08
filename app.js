// Aura Voyage Core JavaScript

document.addEventListener('DOMContentLoaded', () => {
    // --- Elements ---
    const btnGenerate = document.getElementById('btn-generate');
    const youtubeUrlInput = document.getElementById('youtube-url');
    const tripIntentInput = document.getElementById('trip-intent');
    
    // Settings Modal Elements
    const btnSettings = document.getElementById('btn-settings');
    const modalSettings = document.getElementById('modal-backdrop-settings');
    const btnCloseSettings = document.getElementById('settings-close');
    const btnCancelSettings = document.getElementById('settings-cancel');
    const btnSaveSettings = document.getElementById('settings-save');
    const inputGeminiKey = document.getElementById('gemini-key');
    const inputYoutubeKey = document.getElementById('youtube-key');
    const inputMapsKey = document.getElementById('maps-key');

    // UI Updates
    const consoleLog = document.getElementById('agent-console');
    const pipelineConnector = document.getElementById('pipeline-connector');
    const agentBadge1 = document.getElementById('agent-badge-1');
    const agentBadge2 = document.getElementById('agent-badge-2');
    const summarizerWorkspace = document.getElementById('summarizer-workspace');
    
    // Check local storage for keys
    inputGeminiKey.value = localStorage.getItem('gemini_api_key') || '';
    inputYoutubeKey.value = localStorage.getItem('youtube_api_key') || '';
    inputMapsKey.value = localStorage.getItem('maps_api_key') || '';

    // --- Modal Logic ---
    const openSettings = () => { modalSettings.style.display = 'flex'; };
    const closeSettings = () => { modalSettings.style.display = 'none'; };

    btnSettings.addEventListener('click', openSettings);
    btnCloseSettings.addEventListener('click', closeSettings);
    btnCancelSettings.addEventListener('click', closeSettings);

    btnSaveSettings.addEventListener('click', () => {
        localStorage.setItem('gemini_api_key', inputGeminiKey.value.trim());
        localStorage.setItem('youtube_api_key', inputYoutubeKey.value.trim());
        localStorage.setItem('maps_api_key', inputMapsKey.value.trim());
        closeSettings();
        logToConsole("API Settings updated locally.");
    });

    // --- Helper Functions ---
    function logToConsole(message) {
        if (!consoleLog) return;
        consoleLog.style.display = 'block';
        const p = document.createElement('p');
        p.textContent = `> ${new Date().toLocaleTimeString()} - ${message}`;
        consoleLog.appendChild(p);
        consoleLog.scrollTop = consoleLog.scrollHeight;
    }

    // --- Main Generation Logic ---
    btnGenerate.addEventListener('click', async () => {
        const url = youtubeUrlInput.value.trim();
        const intent = tripIntentInput.value.trim();

        if (!url) {
            alert('Please enter a YouTube URL.');
            return;
        }

        // Reset UI
        consoleLog.innerHTML = '';
        consoleLog.style.display = 'block';
        agentBadge1.classList.add('active');
        pipelineConnector.classList.remove('active');
        agentBadge2.classList.remove('active');
        summarizerWorkspace.style.display = 'none';

        logToConsole(`Initiating planning for: ${url}`);
        
        let pollInterval = setInterval(async () => {
            try {
                let statusRes = await fetch('/api/status');
                if (statusRes.ok) {
                    let statusData = await statusRes.json();
                    if (statusData.logs && statusData.logs.length > 0) {
                        statusData.logs.forEach(msg => logToConsole(msg));
                    }
                }
            } catch(e) {
                // Ignore poll errors
            }
        }, 1500);

        try {
            // Call the local backend server
            const response = await fetch('/api/plan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url: url, intent: intent })
            });

            clearInterval(pollInterval);
            
            // Do one last poll to catch trailing logs
            try {
                let finalStatusRes = await fetch('/api/status');
                if (finalStatusRes.ok) {
                    let finalStatusData = await finalStatusRes.json();
                    if (finalStatusData.logs && finalStatusData.logs.length > 0) {
                        finalStatusData.logs.forEach(msg => logToConsole(msg));
                    }
                }
            } catch(e) {}

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || 'Server error');
            }

            const data = await response.json();
            
            pipelineConnector.classList.add('active');
            agentBadge2.classList.add('active');
            logToConsole("Planning complete!");

            // Show workspace
            summarizerWorkspace.style.display = 'block';
            
            // Render YouTube Details (Stage 1) into Tabs
            const yt = data.youtube_details;
            
            // Places
            const placesContainer = document.getElementById('tab-places');
            placesContainer.innerHTML = '';
            if (yt && yt.places) {
                yt.places.forEach(place => {
                    let sourceLogos = '';
                    if (place.sources && place.sources.length > 0) {
                        if (place.sources.includes('youtube')) sourceLogos += `<i class="fa-brands fa-youtube" title="Recommended by YouTube" style="color: #ff0000; margin-left: 8px; font-size: 0.9rem;"></i>`;
                        if (place.sources.includes('google_maps')) sourceLogos += `<i class="fa-brands fa-google" title="Verified by Google Maps" style="color: #4285F4; margin-left: 6px; font-size: 0.8rem;"></i>`;
                    } else {
                        sourceLogos = `<i class="fa-brands fa-youtube" title="Recommended by YouTube" style="color: #ff0000; margin-left: 8px; font-size: 0.9rem;"></i>`;
                    }

                    const card = document.createElement('div');
                    card.className = 'glass-card';
                    card.style.marginBottom = '10px';
                    card.style.padding = '1rem';
                    card.innerHTML = `
                        <h4 style="margin-bottom: 5px; color: var(--text-primary);">${DOMPurify.sanitize(place.name)}${sourceLogos} <span style="font-size: 0.75rem; padding: 2px 6px; background: rgba(59,130,246,0.2); border-radius: 10px; margin-left: 8px;">${DOMPurify.sanitize(place.category)}</span></h4>
                        <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 5px;">${DOMPurify.sanitize(place.description)}</p>
                        <p style="font-size: 0.8rem; color: var(--accent-color);"><i class="fa-solid fa-masks-theater"></i> Vibe: ${DOMPurify.sanitize(place.vibe)}</p>
                    `;
                    placesContainer.appendChild(card);
                });
            }

            // Hotels
            const hotelsContainer = document.getElementById('tab-hotels');
            hotelsContainer.innerHTML = '';
            const recommendedHotels = data.custom_itinerary?.hotels;
            if (recommendedHotels) {
                recommendedHotels.forEach(hotel => {
                    let sourceLogos = '';
                    if (hotel.sources && hotel.sources.length > 0) {
                        if (hotel.sources.includes('youtube')) sourceLogos += `<i class="fa-brands fa-youtube" title="Recommended by YouTube" style="color: #ff0000; margin-left: 8px; font-size: 0.9rem;"></i>`;
                        if (hotel.sources.includes('google_maps')) sourceLogos += `<i class="fa-brands fa-google" title="Verified by Google Maps" style="color: #4285F4; margin-left: 6px; font-size: 0.8rem;"></i>`;
                    } else {
                        sourceLogos = `<i class="fa-brands fa-google" title="Verified by Google Maps" style="color: #4285F4; margin-left: 6px; font-size: 0.8rem;"></i>`;
                    }

                    const card = document.createElement('div');
                    card.className = 'glass-card';
                    card.style.marginBottom = '10px';
                    card.style.padding = '1rem';
                    
                    let attractionsHTML = '';
                    if (hotel.nearby_attractions && hotel.nearby_attractions.length > 0) {
                        const items = hotel.nearby_attractions.map(a => `<li>${DOMPurify.sanitize(a.name)} (⭐ ${DOMPurify.sanitize(a.rating)})</li>`).join('');
                        attractionsHTML = `
                            <div style="margin-top: 10px; background-color: #8b5cf6; padding: 10px; border-radius: 8px; color: white;">
                                <h5 style="margin: 0 0 5px 0;"><i class="fa-solid fa-map-location-dot"></i> Nearby Attractions</h5>
                                <ul style="margin: 0; padding-left: 20px; font-size: 0.8rem;">
                                    ${items}
                                </ul>
                            </div>
                        `;
                    }

                    card.innerHTML = `
                        <h4 style="margin-bottom: 5px; color: var(--text-primary);">${DOMPurify.sanitize(hotel.name)}${sourceLogos} <span style="font-size: 0.75rem; margin-left: 8px; color: var(--accent-color);">⭐ ${DOMPurify.sanitize(hotel.rating)}</span></h4>
                        <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 8px;"><i class="fa-solid fa-location-dot"></i> ${DOMPurify.sanitize(hotel.address)}</p>
                        <p style="font-size: 0.85rem; color: var(--text-secondary);">${DOMPurify.sanitize(hotel.description)}</p>
                        ${attractionsHTML}
                    `;
                    hotelsContainer.appendChild(card);
                });
            }

            // Tips
            const tipsContainer = document.getElementById('tab-tips');
            tipsContainer.innerHTML = '';
            if (yt && yt.tips) {
                yt.tips.forEach(tip => {
                    const card = document.createElement('div');
                    card.className = 'glass-card';
                    card.style.marginBottom = '10px';
                    card.style.padding = '1rem';
                    card.innerHTML = `
                        <h4 style="margin-bottom: 5px; color: var(--accent-color);"><i class="fa-solid fa-lightbulb"></i> ${DOMPurify.sanitize(tip.topic)}</h4>
                        <p style="font-size: 0.85rem; color: var(--text-secondary);">${DOMPurify.sanitize(tip.content)}</p>
                    `;
                    tipsContainer.appendChild(card);
                });
            }

            // YT Notes (Itinerary Notes)
            const notesContainer = document.getElementById('tab-itinerary');
            if (yt && yt.itinerary_notes) {
                notesContainer.innerHTML = `<div class="glass-card" style="padding: 1rem;"><p style="font-size: 0.85rem; white-space: pre-wrap; color: var(--text-secondary);">${DOMPurify.sanitize(yt.itinerary_notes)}</p></div>`;
            }

            // Render Custom Itinerary (Stage 2) into Middle Section
            const timelineContainer = document.getElementById('itinerary-timeline-container');
            timelineContainer.innerHTML = ''; // Clear 'Ready to Plan'
            
            const itinerary = data.custom_itinerary;
            if (itinerary) {
                // Set Header
                document.getElementById('destination-title').textContent = itinerary.title || "Your Custom Itinerary";
                document.getElementById('destination-subtitle').textContent = itinerary.subtitle || "";

                let mapLocations = [];

                // Render Days
                if (itinerary.days) {
                    itinerary.days.forEach(day => {
                        const dayCard = document.createElement('div');
                        dayCard.className = 'glass-card';
                        
                        let itemsHTML = '';
                        if (day.items) {
                            day.items.forEach(item => {
                                // Add to map locations if it has coordinates (from place lookup) or we can infer it
                                // For now, we will add the titles to the map if they have coordinates. 
                                // Actually, let's extract them from the itinerary places/hotels or infer.
                                // The backend returns places and hotels with lat/lng.
                                
                                let swapsHTML = '';
                                if (item.swaps && item.swaps.length > 0) {
                                    swapsHTML = `<div style="margin-top: 8px; font-size: 0.75rem;"><span style="color: var(--accent-color);">Swaps:</span> ${item.swaps.map(s => `<span class="preset-pill" style="padding: 2px 6px; font-size: 0.7rem; margin-right: 4px; display: inline-block;">${DOMPurify.sanitize(s)}</span>`).join('')}</div>`;
                                }
                                
                                let icon = 'fa-location-dot';
                                if (item.type === 'food') icon = 'fa-utensils';
                                else if (item.type === 'activity') icon = 'fa-person-hiking';
                                else if (item.type === 'hotel') icon = 'fa-bed';
                                
                                // Source attribution logos
                                let sourceLogos = '';
                                if (item.sources && item.sources.length > 0) {
                                    if (item.sources.includes('youtube')) {
                                        sourceLogos += `<i class="fa-brands fa-youtube" title="Recommended by YouTube" style="color: #ff0000; margin-left: 8px; font-size: 0.9rem;"></i>`;
                                    }
                                    if (item.sources.includes('google_maps')) {
                                        sourceLogos += `<i class="fa-brands fa-google" title="Verified by Google Maps" style="color: #4285F4; margin-left: 6px; font-size: 0.8rem;"></i>`;
                                    }
                                } else {
                                    // Fallback to heuristic if sources field is missing
                                    sourceLogos += `<i class="fa-brands fa-youtube" title="Recommended by YouTube" style="color: #ff0000; margin-left: 8px; font-size: 0.9rem;"></i>`;
                                    if (item.refId) {
                                        const matchPlace = itinerary.places?.find(p => p.id === item.refId);
                                        const matchHotel = itinerary.hotels?.find(h => h.id === item.refId);
                                        if (matchPlace || matchHotel) {
                                            sourceLogos += `<i class="fa-brands fa-google" title="Verified by Google Maps" style="color: #4285F4; margin-left: 6px; font-size: 0.8rem;"></i>`;
                                        }
                                    }
                                }

                                itemsHTML += `
                                    <div style="display: flex; gap: 15px; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid var(--border-card);">
                                        <div style="font-weight: bold; color: var(--accent-color); width: 60px; flex-shrink: 0; font-size: 0.85rem;">${DOMPurify.sanitize(item.time)}</div>
                                        <div style="flex: 1;">
                                            <div style="font-weight: 600; color: var(--text-primary); margin-bottom: 4px;"><i class="fa-solid ${icon}" style="margin-right: 6px; font-size: 0.8rem; color: var(--text-muted);"></i>${DOMPurify.sanitize(item.title)}${sourceLogos}</div>
                                            <div style="font-size: 0.8rem; color: var(--text-secondary);">${DOMPurify.sanitize(item.description)}</div>
                                            ${swapsHTML}
                                        </div>
                                    </div>
                                `;
                            });
                        }
                        
                        dayCard.innerHTML = `
                            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px; border-bottom: 2px solid var(--border-card); padding-bottom: 10px;">
                                <h3 style="color: white; margin: 0;">Day ${day.day}</h3>
                                <span style="font-size: 0.85rem; color: var(--text-muted); background: rgba(0,0,0,0.3); padding: 4px 10px; border-radius: 12px;">${DOMPurify.sanitize(day.summary)}</span>
                            </div>
                            <div class="day-items">
                                ${itemsHTML}
                            </div>
                        `;
                        timelineContainer.appendChild(dayCard);
                    });
                }

                // Plot Map
                const mapCanvas = document.getElementById('map-canvas');
                mapCanvas.innerHTML = ''; // Clear fallback background
                mapCanvas.style.background = '#1a1f2b'; // Dark map background
                mapCanvas.style.position = 'relative';
                mapCanvas.style.overflow = 'hidden';

                // Collect all valid places to plot
                const allPlaces = [];
                if (itinerary.hotels) {
                    itinerary.hotels.forEach(h => {
                        if (h.lat && h.lng) allPlaces.push({ name: h.name, lat: h.lat, lng: h.lng, type: 'hotel' });
                    });
                }
                if (itinerary.places) {
                    itinerary.places.forEach(p => {
                        if (p.lat && p.lng) allPlaces.push({ name: p.name, lat: p.lat, lng: p.lng, type: 'place' });
                    });
                }
                
                // We don't have an actual Google Map instance initialized in this UI yet,
                // so we will simulate the map route plot on our canvas with a custom visual map layer.
                if (allPlaces.length > 0) {
                    document.getElementById('hud-route-count').textContent = `${allPlaces.length} locations pinned`;
                    
                    // Simple logic to draw relative points
                    const lats = allPlaces.map(p => p.lat);
                    const lngs = allPlaces.map(p => p.lng);
                    const minLat = Math.min(...lats);
                    const maxLat = Math.max(...lats);
                    const minLng = Math.min(...lngs);
                    const maxLng = Math.max(...lngs);
                    
                    const latRange = (maxLat - minLat) || 0.01;
                    const lngRange = (maxLng - minLng) || 0.01;
                    
                    let routeSVG = `<svg width="100%" height="100%" style="position: absolute; top: 0; left: 0; z-index: 1;">`;
                    let previousPoint = null;

                    allPlaces.forEach((place, index) => {
                        // Calculate percentage position
                        // Invert Lat so higher lat is visually higher (top)
                        const y = 10 + 80 * (1 - ((place.lat - minLat) / latRange));
                        const x = 10 + 80 * ((place.lng - minLng) / lngRange);

                        if (previousPoint) {
                            routeSVG += `<line x1="${previousPoint.x}%" y1="${previousPoint.y}%" x2="${x}%" y2="${y}%" stroke="rgba(59,130,246,0.6)" stroke-width="2" stroke-dasharray="4" />`;
                        }
                        previousPoint = { x, y };

                        const markerColor = place.type === 'hotel' ? '#8b5cf6' : '#3b82f6';
                        const iconHtml = place.type === 'hotel' ? '<i class="fa-solid fa-bed" style="font-size: 10px; color: white;"></i>' : '<i class="fa-solid fa-location-dot" style="font-size: 10px; color: white;"></i>';

                        const marker = document.createElement('div');
                        marker.style.position = 'absolute';
                        marker.style.left = `calc(${x}% - 12px)`;
                        marker.style.top = `calc(${y}% - 12px)`;
                        marker.style.width = '24px';
                        marker.style.height = '24px';
                        marker.style.backgroundColor = markerColor;
                        marker.style.borderRadius = '50%';
                        marker.style.display = 'flex';
                        marker.style.alignItems = 'center';
                        marker.style.justifyContent = 'center';
                        marker.style.boxShadow = '0 0 10px rgba(0,0,0,0.5)';
                        marker.style.cursor = 'pointer';
                        marker.style.zIndex = '2';
                        marker.title = place.name;
                        marker.innerHTML = iconHtml;

                        const label = document.createElement('div');
                        label.style.position = 'absolute';
                        label.style.left = `calc(${x}% + 15px)`;
                        label.style.top = `calc(${y}% - 10px)`;
                        label.style.backgroundColor = 'rgba(0,0,0,0.7)';
                        label.style.color = 'white';
                        label.style.padding = '2px 6px';
                        label.style.borderRadius = '4px';
                        label.style.fontSize = '10px';
                        label.style.whiteSpace = 'nowrap';
                        label.style.zIndex = '3';
                        label.style.pointerEvents = 'none';
                        label.textContent = place.name;

                        mapCanvas.appendChild(marker);
                        mapCanvas.appendChild(label);
                    });
                    
                    routeSVG += `</svg>`;
                    mapCanvas.insertAdjacentHTML('afterbegin', routeSVG);

                } else {
                    document.getElementById('hud-route-count').textContent = `0 locations pinned`;
                    mapCanvas.innerHTML = '<div style="color: #666; text-align: center; margin-top: 50%;">No coordinates available to plot</div>';
                }
            }
            
        } catch (error) {
            logToConsole(`Error: ${error.message}`);
            console.error("Plan Error:", error);
        }
    });

    // --- Tabs Logic ---
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            const targetId = btn.getAttribute('data-tab');
            const targetTab = document.getElementById(targetId);
            if (targetTab) {
                targetTab.classList.add('active');
            }
        });
    });
});
