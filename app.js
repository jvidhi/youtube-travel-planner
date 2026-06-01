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
        
        try {
            // Call the local backend server
            const response = await fetch('/api/plan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url: url, intent: intent })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || 'Server error');
            }

            const data = await response.json();
            
            pipelineConnector.classList.add('active');
            agentBadge2.classList.add('active');
            logToConsole("Planning complete!");

            // Show workspace
            summarizerWorkspace.style.display = 'flex';
            
            // Render YouTube Details (Stage 1) into Tabs
            const yt = data.youtube_details;
            
            // Places
            const placesContainer = document.getElementById('tab-places');
            placesContainer.innerHTML = '';
            if (yt && yt.places) {
                yt.places.forEach(place => {
                    const card = document.createElement('div');
                    card.className = 'glass-card';
                    card.style.marginBottom = '10px';
                    card.style.padding = '1rem';
                    card.innerHTML = `
                        <h4 style="margin-bottom: 5px; color: var(--text-primary);">${DOMPurify.sanitize(place.name)} <span style="font-size: 0.75rem; padding: 2px 6px; background: rgba(59,130,246,0.2); border-radius: 10px; margin-left: 8px;">${DOMPurify.sanitize(place.category)}</span></h4>
                        <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 5px;">${DOMPurify.sanitize(place.description)}</p>
                        <p style="font-size: 0.8rem; color: var(--accent-color);"><i class="fa-solid fa-masks-theater"></i> Vibe: ${DOMPurify.sanitize(place.vibe)}</p>
                    `;
                    placesContainer.appendChild(card);
                });
            }

            // Hotels
            const hotelsContainer = document.getElementById('tab-hotels');
            hotelsContainer.innerHTML = '';
            if (yt && yt.hotels) {
                yt.hotels.forEach(hotel => {
                    const card = document.createElement('div');
                    card.className = 'glass-card';
                    card.style.marginBottom = '10px';
                    card.style.padding = '1rem';
                    card.innerHTML = `
                        <h4 style="margin-bottom: 5px; color: var(--text-primary);">${DOMPurify.sanitize(hotel.name)} <span style="font-size: 0.75rem; margin-left: 8px;">${DOMPurify.sanitize(hotel.budget_tier)}</span></h4>
                        <p style="font-size: 0.85rem; color: var(--text-secondary);">${DOMPurify.sanitize(hotel.details)}</p>
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

                // Render Days
                if (itinerary.days) {
                    itinerary.days.forEach(day => {
                        const dayCard = document.createElement('div');
                        dayCard.className = 'glass-card';
                        
                        let itemsHTML = '';
                        if (day.items) {
                            day.items.forEach(item => {
                                let swapsHTML = '';
                                if (item.swaps && item.swaps.length > 0) {
                                    swapsHTML = `<div style="margin-top: 8px; font-size: 0.75rem;"><span style="color: var(--accent-color);">Swaps:</span> ${item.swaps.map(s => `<span class="preset-pill" style="padding: 2px 6px; font-size: 0.7rem; margin-right: 4px; display: inline-block;">${DOMPurify.sanitize(s)}</span>`).join('')}</div>`;
                                }
                                
                                let icon = 'fa-location-dot';
                                if (item.type === 'food') icon = 'fa-utensils';
                                else if (item.type === 'activity') icon = 'fa-person-hiking';
                                else if (item.type === 'hotel') icon = 'fa-bed';

                                itemsHTML += `
                                    <div style="display: flex; gap: 15px; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid var(--border-card);">
                                        <div style="font-weight: bold; color: var(--accent-color); width: 60px; flex-shrink: 0; font-size: 0.85rem;">${DOMPurify.sanitize(item.time)}</div>
                                        <div style="flex: 1;">
                                            <div style="font-weight: 600; color: var(--text-primary); margin-bottom: 4px;"><i class="fa-solid ${icon}" style="margin-right: 6px; font-size: 0.8rem; color: var(--text-muted);"></i>${DOMPurify.sanitize(item.title)}</div>
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
