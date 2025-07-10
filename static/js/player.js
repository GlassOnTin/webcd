class WebCDPlayer {
    constructor() {
        this.tracks = [];
        this.currentTrack = 1;
        this.isPlaying = false;
        this.audioPlayer = document.getElementById('audio-player');
        this.streamSettings = {};
        
        this.initializeEventListeners();
        this.loadSettings();
        this.refreshCDInfo();
    }
    
    initializeEventListeners() {
        document.getElementById('refresh-cd').addEventListener('click', () => this.refreshCDInfo());
        document.getElementById('play-btn').addEventListener('click', () => this.togglePlay());
        document.getElementById('stop-btn').addEventListener('click', () => this.stop());
        document.getElementById('next-btn').addEventListener('click', () => this.nextTrack());
        document.getElementById('prev-btn').addEventListener('click', () => this.previousTrack());
        
        // Audio player events
        this.audioPlayer.addEventListener('ended', () => this.nextTrack());
        this.audioPlayer.addEventListener('error', (e) => this.handleAudioError(e));
        
        // Settings panel events
        document.getElementById('toggle-settings').addEventListener('click', () => this.toggleSettings());
        document.getElementById('apply-settings').addEventListener('click', () => this.applySettings());
        document.getElementById('preload-seconds').addEventListener('input', (e) => {
            document.getElementById('preload-value').textContent = e.target.value + 's';
        });
        
        // Album search events
        document.getElementById('search-album').addEventListener('click', () => this.openAlbumSearch());
        document.querySelector('.close').addEventListener('click', () => this.closeAlbumSearch());
        document.getElementById('search-button').addEventListener('click', () => this.searchAlbums());
        document.getElementById('album-search-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.searchAlbums();
        });
    }
    
    async refreshCDInfo() {
        this.updateStatus('Checking CD...');
        
        try {
            const response = await fetch('/api/cd-info');
            const data = await response.json();
            
            if (data.success) {
                this.tracks = data.tracks;
                this.displayTracks();
                this.updateStatus(`Found ${this.tracks.length} tracks`);
                
                // Update album info if available
                if (data.album) {
                    this.displayAlbumInfo(data.album);
                } else {
                    document.getElementById('cd-info').innerHTML = `<p>CD detected: ${this.tracks.length} tracks</p>`;
                    document.getElementById('album-info').style.display = 'none';
                }
                
                // Show search button when CD is detected
                document.getElementById('search-album').style.display = 'inline-block';
            } else {
                this.updateStatus('Error: ' + data.error);
                document.getElementById('cd-info').innerHTML = '<p>No CD detected or error reading CD</p>';
                document.getElementById('album-info').style.display = 'none';
                this.tracks = [];
                this.displayTracks();
            }
        } catch (error) {
            this.updateStatus('Error connecting to server');
            console.error('Error:', error);
        }
    }
    
    displayAlbumInfo(album) {
        document.getElementById('cd-info').style.display = 'none';
        document.getElementById('album-info').style.display = 'block';
        document.getElementById('album-title').textContent = album.album || 'Unknown Album';
        document.getElementById('album-artist').textContent = album.artist || 'Unknown Artist';
        
        let yearText = album.year || '';
        if (album.source) {
            yearText += (yearText ? ' • ' : '') + `Source: ${album.source}`;
        }
        document.getElementById('album-year').textContent = yearText;
    }
    
    displayTracks() {
        const trackList = document.getElementById('track-list');
        
        if (this.tracks.length === 0) {
            trackList.innerHTML = '<p style="text-align: center; padding: 20px;">No tracks available</p>';
            return;
        }
        
        trackList.innerHTML = this.tracks.map(track => `
            <div class="track-item" data-track="${track.number}">
                <span>
                    <span class="track-number">${track.number}.</span>
                    ${track.title}
                </span>
                <span>${track.duration}</span>
            </div>
        `).join('');
        
        // Add click listeners to tracks
        trackList.querySelectorAll('.track-item').forEach(item => {
            item.addEventListener('click', () => {
                const trackNum = parseInt(item.dataset.track);
                this.playTrack(trackNum);
            });
        });
    }
    
    async playTrack(trackNumber) {
        this.currentTrack = trackNumber;
        
        // Update UI
        this.highlightActiveTrack();
        this.updateNowPlaying();
        
        // Set audio source and play
        // Add timestamp to prevent caching issues
        this.audioPlayer.src = `/api/stream/${trackNumber}?t=${Date.now()}`;
        
        // Set preload for mobile
        this.audioPlayer.preload = 'none';
        
        try {
            // Add small delay for mobile browsers
            if (/Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {
                this.updateStatus(`Buffering track ${trackNumber}...`);
                await new Promise(resolve => setTimeout(resolve, 500));
            }
            
            await this.audioPlayer.play();
            this.isPlaying = true;
            this.updatePlayButton();
            this.updateStatus(`Playing track ${trackNumber}`);
        } catch (error) {
            this.handleAudioError(error);
        }
    }
    
    async togglePlay() {
        if (this.isPlaying) {
            this.pause();
        } else {
            if (this.audioPlayer.src) {
                try {
                    await this.audioPlayer.play();
                    this.isPlaying = true;
                    this.updatePlayButton();
                    this.updateStatus(`Resumed track ${this.currentTrack}`);
                } catch (error) {
                    this.handleAudioError(error);
                }
            } else if (this.tracks.length > 0) {
                this.playTrack(this.currentTrack);
            }
        }
    }
    
    pause() {
        this.audioPlayer.pause();
        this.isPlaying = false;
        this.updatePlayButton();
        this.updateStatus('Paused');
    }
    
    stop() {
        this.audioPlayer.pause();
        this.audioPlayer.currentTime = 0;
        this.isPlaying = false;
        this.updatePlayButton();
        this.updateStatus('Stopped');
    }
    
    async nextTrack() {
        if (this.currentTrack < this.tracks.length) {
            await this.playTrack(this.currentTrack + 1);
        } else {
            this.updateStatus('Reached end of CD');
            this.stop();
        }
    }
    
    async previousTrack() {
        if (this.currentTrack > 1) {
            await this.playTrack(this.currentTrack - 1);
        } else {
            this.updateStatus('Already at first track');
        }
    }
    
    highlightActiveTrack() {
        document.querySelectorAll('.track-item').forEach(item => {
            if (parseInt(item.dataset.track) === this.currentTrack) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }
    
    updateNowPlaying() {
        const track = this.tracks.find(t => t.number === this.currentTrack);
        if (track) {
            document.getElementById('current-track').textContent = `Track ${track.number}: ${track.title}`;
        }
    }
    
    updatePlayButton() {
        const playBtn = document.getElementById('play-btn');
        if (this.isPlaying) {
            playBtn.textContent = '⏸ Pause';
        } else {
            playBtn.textContent = '▶ Play';
        }
    }
    
    updateStatus(message) {
        document.getElementById('status-text').textContent = message;
    }
    
    handleAudioError(error) {
        console.error('Audio error:', error);
        this.isPlaying = false;
        this.updatePlayButton();
        this.updateStatus('Error playing audio. Check if CD is inserted.');
    }
    
    toggleSettings() {
        const settingsContent = document.getElementById('settings-content');
        if (settingsContent.style.display === 'none') {
            settingsContent.style.display = 'block';
        } else {
            settingsContent.style.display = 'none';
        }
    }
    
    async loadSettings() {
        try {
            const response = await fetch('/api/settings');
            if (response.ok) {
                this.streamSettings = await response.json();
                this.updateSettingsUI();
            }
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }
    
    updateSettingsUI() {
        if (this.streamSettings.bitrate) {
            document.getElementById('bitrate').value = this.streamSettings.bitrate;
        }
        if (this.streamSettings.buffer_size) {
            document.getElementById('buffer-size').value = this.streamSettings.buffer_size;
        }
        if (this.streamSettings.paranoia_mode) {
            document.getElementById('paranoia-mode').value = this.streamSettings.paranoia_mode;
        }
        if (this.streamSettings.preload_seconds !== undefined) {
            document.getElementById('preload-seconds').value = this.streamSettings.preload_seconds;
            document.getElementById('preload-value').textContent = this.streamSettings.preload_seconds + 's';
        }
    }
    
    async applySettings() {
        const settings = {
            bitrate: document.getElementById('bitrate').value,
            buffer_size: document.getElementById('buffer-size').value,
            paranoia_mode: document.getElementById('paranoia-mode').value,
            preload_seconds: parseInt(document.getElementById('preload-seconds').value)
        };
        
        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings)
            });
            
            if (response.ok) {
                this.streamSettings = await response.json();
                this.updateStatus('Settings applied successfully');
                
                // Save to localStorage for persistence
                localStorage.setItem('webcd-settings', JSON.stringify(this.streamSettings));
                
                // If currently playing, stop and restart with new settings
                if (this.isPlaying) {
                    const track = this.currentTrack;
                    this.stop();
                    setTimeout(() => this.playTrack(track), 500);
                }
            }
        } catch (error) {
            console.error('Error applying settings:', error);
            this.updateStatus('Error applying settings');
        }
    }
    
    openAlbumSearch() {
        document.getElementById('album-search-modal').style.display = 'flex';
        document.getElementById('album-search-input').focus();
    }
    
    closeAlbumSearch() {
        document.getElementById('album-search-modal').style.display = 'none';
        document.getElementById('search-results').innerHTML = '';
        document.getElementById('album-search-input').value = '';
    }
    
    async searchAlbums() {
        const query = document.getElementById('album-search-input').value.trim();
        if (!query) return;
        
        const resultsDiv = document.getElementById('search-results');
        resultsDiv.innerHTML = '<p>Searching...</p>';
        
        try {
            const response = await fetch('/api/search-album', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            
            const data = await response.json();
            
            if (data.success && data.albums.length > 0) {
                resultsDiv.innerHTML = data.albums.map(album => `
                    <div class="album-result" data-id="${album.id}">
                        <h3>${album.album}</h3>
                        <p>${album.artist}${album.year ? ' • ' + album.year : ''}</p>
                        <p style="font-size: 0.8em; color: #aaa;">${album.track_count} tracks</p>
                    </div>
                `).join('');
                
                // Add click handlers
                resultsDiv.querySelectorAll('.album-result').forEach(div => {
                    div.addEventListener('click', () => this.selectAlbum(div.dataset.id));
                });
            } else {
                resultsDiv.innerHTML = '<p>No albums found. Try a different search.</p>';
            }
        } catch (error) {
            resultsDiv.innerHTML = '<p>Error searching albums.</p>';
            console.error('Search error:', error);
        }
    }
    
    async selectAlbum(releaseId) {
        this.updateStatus('Setting album information...');
        
        try {
            const response = await fetch('/api/set-album', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ release_id: releaseId })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Update album info
                if (data.album) {
                    this.displayAlbumInfo(data.album);
                }
                
                // Update tracks
                if (data.tracks) {
                    this.tracks = data.tracks;
                    this.displayTracks();
                }
                
                this.updateStatus('Album information updated');
                this.closeAlbumSearch();
            } else {
                this.updateStatus('Error setting album');
            }
        } catch (error) {
            console.error('Error setting album:', error);
            this.updateStatus('Error setting album');
        }
    }
}

// Initialize player when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.cdPlayer = new WebCDPlayer();
});