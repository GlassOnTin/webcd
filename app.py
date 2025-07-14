import os
import subprocess
import json
import threading
import time
import re
import hashlib
import musicbrainzngs
import requests
import socket
from flask import Flask, render_template, jsonify, Response, request, make_response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Configure MusicBrainz
musicbrainzngs.set_useragent("WebCD", "1.0", "https://github.com/webcd")

class CDPlayer:
    def __init__(self):
        self.current_process = None
        self.is_playing = False
        self.current_track = 1
        self.track_info = []
        self.available_devices = []
        self.cd_device = None
        # Default streaming settings
        self.stream_settings = {
            'bitrate': '192k',
            'buffer_size': '256k',
            'paranoia_mode': 'fast',  # 'fast', 'normal', 'paranoid'
            'preload_seconds': 1
        }
        self.album_info = None
        # Detect CD devices on initialization
        self.detect_cd_devices()
        
        # Check for environment variable override
        env_device = os.environ.get('WEBCD_DEVICE')
        if env_device and os.path.exists(env_device):
            self.cd_device = env_device
        elif self.available_devices and not self.cd_device:
            # Use first available device if no environment override
            self.cd_device = self.available_devices[0]['device']
    
    def detect_cd_devices(self):
        """Detect available CD/DVD devices on the system"""
        self.available_devices = []
        
        # Method 1: Check common device paths
        common_devices = ['/dev/cdrom', '/dev/dvd', '/dev/sr0', '/dev/sr1', '/dev/sr2']
        for device in common_devices:
            if os.path.exists(device):
                # Try to get device info
                device_info = self.get_device_info(device)
                if device_info:
                    self.available_devices.append(device_info)
        
        # Method 2: Check /sys/block for sr* devices
        try:
            for device in os.listdir('/sys/block'):
                if device.startswith('sr'):
                    device_path = f'/dev/{device}'
                    if os.path.exists(device_path):
                        device_info = self.get_device_info(device_path)
                        if device_info and not any(d['device'] == device_path for d in self.available_devices):
                            self.available_devices.append(device_info)
        except:
            pass
        
        # Remove duplicates based on real path
        unique_devices = {}
        for dev in self.available_devices:
            real_path = dev['real_path']
            if real_path not in unique_devices:
                unique_devices[real_path] = dev
        self.available_devices = list(unique_devices.values())
        
        return self.available_devices
    
    def get_device_info(self, device_path):
        """Get information about a CD/DVD device"""
        try:
            # Get the real device path (resolve symlinks)
            real_path = os.path.realpath(device_path)
            
            # Try to get device model info
            model = "Unknown CD/DVD Drive"
            try:
                # Extract device name from path (e.g., sr0 from /dev/sr0)
                device_name = os.path.basename(real_path)
                model_file = f'/sys/block/{device_name}/device/model'
                if os.path.exists(model_file):
                    with open(model_file, 'r') as f:
                        model = f.read().strip()
            except:
                pass
            
            # Check if media is present
            has_media = self.check_media_present(device_path)
            
            return {
                'device': device_path,
                'real_path': real_path,
                'model': model,
                'has_media': has_media
            }
        except:
            return None
    
    def check_media_present(self, device_path):
        """Check if a CD is present in the device"""
        try:
            # Try using cdparanoia -Q to check for media
            result = subprocess.run(['cdparanoia', '-Q', '-d', device_path], 
                                  capture_output=True, timeout=2)
            # If cdparanoia can read TOC, media is present
            return 'Unable to open disc' not in result.stderr.decode()
        except:
            try:
                # Fallback: try using blockdev
                result = subprocess.run(['blockdev', '--getsize64', device_path], 
                                      capture_output=True, timeout=1)
                return result.returncode == 0 and int(result.stdout.strip()) > 0
            except:
                return False
    
    def set_cd_device(self, device_path):
        """Set the active CD device"""
        # Verify the device exists
        if not os.path.exists(device_path):
            return {'success': False, 'error': 'Device not found'}
        
        # Stop playback if currently playing
        if self.is_playing:
            self.stop()
        
        self.cd_device = device_path
        # Clear current track info when switching devices
        self.track_info = []
        self.album_info = None
        
        return {'success': True, 'device': device_path}
        
    def get_cd_info(self):
        """Get CD track information using cdparanoia or ffmpeg"""
        tracks = []
        # Reset album info for new scan
        self.album_info = None
        
        # Check if we have a CD device selected
        if not self.cd_device:
            return {'success': False, 'error': 'No CD device selected', 'tracks': []}
        
        # First try cdparanoia which is more reliable for CD info
        try:
            cmd = ['cdparanoia', '-Q', '-d', self.cd_device]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            # Parse cdparanoia output (it outputs to stderr)
            lines = result.stderr.split('\n')
            for line in lines:
                # Look for track listings like: "  1.    33027 [07:20.27]        0 [00:00.00]    0"
                match = re.match(r'\s+(\d+)\.\s+\d+\s+\[(\d+):(\d+)\.(\d+)\]', line)
                if match:
                    track_num = int(match.group(1))
                    minutes = int(match.group(2))
                    seconds = int(match.group(3))
                    duration = f"{minutes:02d}:{seconds:02d}"
                    
                    tracks.append({
                        'number': track_num,
                        'title': f'Track {track_num}',
                        'duration': duration
                    })
            
            if tracks:
                self.track_info = tracks
                # Try to get album info from MusicBrainz
                self.get_album_info()
                return {'success': True, 'tracks': self.track_info, 'album': self.album_info}
                
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            # cdparanoia failed, try ffmpeg
            pass
        
        # Fallback to ffmpeg
        try:
            cmd = [
                'ffmpeg', '-f', 'libcdio', '-i', self.cd_device,
                '-t', '0.1', '-f', 'null', '-'
            ]
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            try:
                stdout, stderr = process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
            
            # Look for track count in ffmpeg output
            for line in stderr.split('\n'):
                # Look for lines like "libcdio ... 12 tracks"
                match = re.search(r'(\d+)\s+tracks?', line, re.IGNORECASE)
                if match:
                    track_count = int(match.group(1))
                    tracks = [{'number': i+1, 'title': f'Track {i+1}', 'duration': '00:00'} 
                            for i in range(track_count)]
                    break
            
            # If we found tracks or if there's CD input detected
            if tracks or 'Input #0' in stderr:
                if not tracks:
                    # Default to single track if CD detected but no track info
                    tracks = [{'number': 1, 'title': 'Track 1', 'duration': '00:00'}]
                
                self.track_info = tracks
                # Try to get album info from MusicBrainz
                self.get_album_info()
                return {'success': True, 'tracks': self.track_info, 'album': self.album_info}
            else:
                return {'success': False, 'error': 'No CD detected'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def calculate_disc_id(self):
        """Calculate disc ID using cd-discid or manual calculation"""
        try:
            # First try cd-discid if available
            result = subprocess.run(
                ['cd-discid', self.cd_device], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse cd-discid output
                parts = result.stdout.strip().split()
                if len(parts) >= 3:
                    return parts[0]  # Return the disc ID
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Fallback: calculate from track info
        # This is a simplified version - real CDDB calculation is more complex
        if self.track_info:
            track_count = len(self.track_info)
            # Create a simple hash based on track count and durations
            hash_input = f"{track_count}"
            for track in self.track_info:
                hash_input += track['duration']
            return hashlib.md5(hash_input.encode()).hexdigest()[:8]
        
        return None
    
    def query_gnudb(self, disc_id_output):
        """Query GNUDB/FreeDB for album information"""
        try:
            # Parse cd-discid output: "a10b1d0c 12 150 22776 36491..."
            parts = disc_id_output.strip().split()
            if len(parts) < 4:
                return None
                
            disc_id = parts[0]
            track_count = int(parts[1])
            offsets = [int(x) for x in parts[2:]]
            
            # cd-discid output format: discid num_tracks offset1 offset2 ... offsetN total_seconds
            # The last value is already the total disc length in seconds
            disc_length_seconds = offsets[-1]
            track_offsets = offsets[:-1]  # All but the last value
            
            # GNUDB query format
            query = f"cddb query {disc_id} {track_count} {' '.join(map(str, track_offsets))} {disc_length_seconds}"
            
            print(f"GNUDB Query: {query}")
            
            # Debug: write to file
            with open('/tmp/webcd_debug.log', 'a') as f:
                f.write(f"\n--- GNUDB Query at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                f.write(f"CD-DISCID output: {disc_id_output}\n")
                f.write(f"Query: {query}\n")
            
            # Connect to GNUDB
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            
            try:
                sock.connect(('gnudb.gnudb.org', 8880))
                
                # Read welcome message first
                welcome = sock.recv(1024).decode()
                print(f"GNUDB Welcome: {welcome.strip()}")
                
                # Send hello
                hello = f"cddb hello webcd localhost WebCD 1.0\r\n"
                sock.send(hello.encode())
                hello_response = sock.recv(1024).decode()
                print(f"GNUDB Hello Response: {hello_response.strip()}")
                
                # Send query
                sock.send((query + '\r\n').encode())
                response = sock.recv(4096).decode()
                
                print(f"GNUDB Query Response: {response.strip()}")
                
                # Debug: write response to file
                with open('/tmp/webcd_debug.log', 'a') as f:
                    f.write(f"Response: {response.strip()}\n")
                
                # Parse response
                if response.startswith('200'):  # Exact match
                    # Response format: "200 genre discid Artist / Album"
                    parts = response.split(' ', 3)
                    if len(parts) >= 4:
                        genre = parts[1]
                        disc_id = parts[2]
                        artist_album = parts[3].strip()
                        
                        # Get full disc info
                        read_cmd = f"cddb read {genre} {disc_id}\n"
                        sock.send(read_cmd.encode())
                        
                        # Read full response
                        full_data = b""
                        while True:
                            chunk = sock.recv(4096)
                            if not chunk:
                                break
                            full_data += chunk
                            if b'\r\n.\r\n' in full_data or b'\n.\n' in full_data:
                                break
                        
                        disc_data = full_data.decode('utf-8', errors='ignore')
                        
                        # Parse disc data
                        album_info = self.parse_gnudb_data(disc_data)
                        if album_info:
                            return album_info
                            
                elif response.startswith('211') or response.startswith('210'):  # Multiple or exact matches
                    # For 210 (exact match) or 211 (multiple matches), take the first match
                    lines = response.split('\n')
                    for line in lines[1:]:
                        line = line.strip()
                        if line and not line.startswith('.'):
                            parts = line.split(' ', 2)
                            if len(parts) >= 3:
                                genre = parts[0]
                                disc_id = parts[1]
                                
                                # Get full disc info
                                read_cmd = f"cddb read {genre} {disc_id}\n"
                                sock.send(read_cmd.encode())
                                
                                # Read full response
                                full_data = b""
                                while True:
                                    chunk = sock.recv(4096)
                                    if not chunk:
                                        break
                                    full_data += chunk
                                    if b'\r\n.\r\n' in full_data or b'\n.\n' in full_data:
                                        break
                                
                                disc_data = full_data.decode('utf-8', errors='ignore')
                                album_info = self.parse_gnudb_data(disc_data)
                                if album_info:
                                    return album_info
                                break  # Only process first match
                
                sock.close()
                
            except socket.error as e:
                print(f"GNUDB connection error: {e}")
                if sock:
                    sock.close()
                    
        except Exception as e:
            print(f"GNUDB query error: {e}")
            
        return None
    
    def parse_gnudb_data(self, data):
        """Parse GNUDB disc data"""
        try:
            lines = data.split('\n')
            album_info = {}
            tracks = []
            
            for line in lines:
                if line.startswith('DTITLE='):
                    # Format: "Artist / Album"
                    title = line[7:].strip()
                    if ' / ' in title:
                        artist, album = title.split(' / ', 1)
                        album_info['artist'] = artist.strip()
                        album_info['album'] = album.strip()
                    else:
                        album_info['album'] = title
                        album_info['artist'] = 'Unknown Artist'
                        
                elif line.startswith('DYEAR='):
                    album_info['year'] = line[6:].strip()
                    
                elif line.startswith('TTITLE'):
                    # Track title format: "TTITLE0=Track Name"
                    match = re.match(r'TTITLE(\d+)=(.*)', line)
                    if match:
                        track_num = int(match.group(1)) + 1
                        track_title = match.group(2).strip()
                        tracks.append((track_num, track_title))
            
            # Update track info
            if tracks and album_info:
                for track_num, title in sorted(tracks):
                    if track_num <= len(self.track_info):
                        self.track_info[track_num - 1]['title'] = title
                        
                album_info['source'] = 'GNUDB'
                return album_info
                
        except Exception as e:
            print(f"Error parsing GNUDB data: {e}")
            
        return None
    
    def get_album_info(self):
        """Look up album information from GNUDB first, then MusicBrainz"""
        try:
            # First try to get full cd-discid output for GNUDB
            try:
                result = subprocess.run(
                    ['cd-discid', self.cd_device], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    # Try GNUDB first
                    cd_discid_output = result.stdout.strip()
                    print(f"CD-DISCID output: {cd_discid_output}")
                    print(f"Trying GNUDB lookup...")
                    gnudb_info = self.query_gnudb(cd_discid_output)
                    if gnudb_info:
                        self.album_info = gnudb_info
                        print(f"Found album in GNUDB: {gnudb_info}")
                        return
                    else:
                        print("GNUDB lookup returned nothing")
                        
            except Exception as e:
                print(f"GNUDB lookup failed: {e}")
            
            # Fall back to MusicBrainz
            disc_id = self.calculate_disc_id()
            if not disc_id:
                return
            
            print(f"Trying MusicBrainz with disc ID: {disc_id}")
            
            # Try to look up by disc ID
            try:
                result = musicbrainzngs.get_releases_by_discid(
                    disc_id, 
                    includes=["artists", "recordings", "release-groups"]
                )
                
                if 'disc' in result and result['disc'].get('release-list'):
                    releases = result['disc']['release-list']
                    
                    # Prefer releases in English or with high data quality
                    best_release = None
                    for release in releases:
                        if best_release is None:
                            best_release = release
                        # Prefer releases with more complete data
                        if 'date' in release and 'date' not in best_release:
                            best_release = release
                        # Prefer releases with language info
                        if release.get('text-representation', {}).get('language') == 'eng':
                            best_release = release
                            break
                    
                    if best_release:
                        self.album_info = {
                            'artist': best_release['artist-credit'][0]['artist']['name'],
                            'album': best_release['title'],
                            'year': best_release.get('date', '').split('-')[0],
                            'disc_id': disc_id
                        }
                        
                        # Update track titles
                        if 'medium-list' in best_release:
                            for medium in best_release['medium-list']:
                                if 'disc-list' in medium:
                                    for disc in medium['disc-list']:
                                        if disc['id'] == disc_id:
                                            # Found the right disc
                                            if 'track-list' in medium:
                                                for i, track in enumerate(medium['track-list']):
                                                    if i < len(self.track_info):
                                                        self.track_info[i]['title'] = track['recording']['title']
                                            return
                        return
            except Exception as e:
                print(f"MusicBrainz lookup error: {e}")
            
            # If disc ID lookup fails, try searching by track count and first track duration
            if self.track_info:
                track_count = len(self.track_info)
                # Search for releases with similar track count
                search_results = musicbrainzngs.search_releases(
                    tracks=str(track_count),
                    limit=5
                )
                
                if search_results and 'release-list' in search_results:
                    # For now, just use the first result as a guess
                    release = search_results['release-list'][0]
                    self.album_info = {
                        'artist': release.get('artist-credit', [{}])[0].get('artist', {}).get('name', 'Unknown Artist'),
                        'album': release.get('title', 'Unknown Album'),
                        'year': release.get('date', '').split('-')[0] if 'date' in release else ''
                    }
                    
        except Exception as e:
            print(f"Error getting album info: {e}")
            self.album_info = None
    
    def play_track(self, track_number=None):
        """Play a specific track or resume playback"""
        if track_number:
            self.current_track = track_number
            
        self.stop()  # Stop any current playback
        
        try:
            # Start ffmpeg process for audio streaming
            self.current_process = subprocess.Popen([
                'ffmpeg',
                '-f', 'libcdio',
                '-i', self.cd_device,
                '-track', str(self.current_track),
                '-acodec', 'mp3',
                '-ab', '192k',
                '-f', 'mp3',
                '-'
            ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            
            self.is_playing = True
            return {'success': True, 'track': self.current_track}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def stop(self):
        """Stop playback"""
        if self.current_process:
            self.current_process.terminate()
            self.current_process = None
        self.is_playing = False
        return {'success': True}
    
    def next_track(self):
        """Skip to next track"""
        if self.current_track < len(self.track_info):
            return self.play_track(self.current_track + 1)
        return {'success': False, 'error': 'Last track'}
    
    def previous_track(self):
        """Skip to previous track"""
        if self.current_track > 1:
            return self.play_track(self.current_track - 1)
        return {'success': False, 'error': 'First track'}
    
    def get_status(self):
        """Get current player status"""
        return {
            'is_playing': self.is_playing,
            'current_track': self.current_track,
            'track_count': len(self.track_info)
        }
    
    def eject_cd(self):
        """Eject the CD tray"""
        if not self.cd_device:
            return {'success': False, 'error': 'No CD device selected'}
            
        try:
            # Stop playback first if playing
            if self.is_playing:
                self.stop()
            
            # Use eject command to open the CD tray
            cmd = ['eject', self.cd_device]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                # Clear track info since CD is ejected
                self.track_info = []
                self.album_info = None
                # Refresh device info to update media status
                self.detect_cd_devices()
                return {'success': True, 'message': 'CD ejected successfully'}
            else:
                return {'success': False, 'error': f'Failed to eject CD: {result.stderr}'}
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Eject command timed out'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Create player instance
player = CDPlayer()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/cd-info')
def get_cd_info():
    # Force fresh CD read every time
    result = player.get_cd_info()
    print(f"API returning album info: {player.album_info}")
    return jsonify(result)

@app.route('/api/play', methods=['POST'])
def play():
    track = request.json.get('track') if request.json else None
    return jsonify(player.play_track(track))

@app.route('/api/stop', methods=['POST'])
def stop():
    return jsonify(player.stop())

@app.route('/api/next', methods=['POST'])
def next_track():
    return jsonify(player.next_track())

@app.route('/api/previous', methods=['POST'])
def previous_track():
    return jsonify(player.previous_track())

@app.route('/api/status')
def status():
    return jsonify(player.get_status())

@app.route('/api/eject', methods=['POST'])
def eject():
    return jsonify(player.eject_cd())

@app.route('/api/devices')
def get_devices():
    """Get list of available CD/DVD devices"""
    player.detect_cd_devices()  # Refresh device list
    return jsonify({
        'success': True,
        'devices': player.available_devices,
        'current_device': player.cd_device
    })

@app.route('/api/set-device', methods=['POST'])
def set_device():
    """Set the active CD device"""
    data = request.json
    if not data or not data.get('device'):
        return jsonify({'success': False, 'error': 'No device specified'})
    
    result = player.set_cd_device(data['device'])
    return jsonify(result)

@app.route('/api/search-album', methods=['POST'])
def search_album():
    """Manual album search"""
    data = request.json
    if not data or not data.get('query'):
        return jsonify({'success': False, 'error': 'No search query provided'})
    
    try:
        # Search MusicBrainz for albums
        results = musicbrainzngs.search_releases(
            release=data['query'],
            limit=10
        )
        
        albums = []
        if results and 'release-list' in results:
            for release in results['release-list']:
                album = {
                    'id': release.get('id'),
                    'album': release.get('title', 'Unknown Album'),
                    'artist': release.get('artist-credit', [{}])[0].get('artist', {}).get('name', 'Unknown Artist'),
                    'year': release.get('date', '').split('-')[0] if 'date' in release else '',
                    'track_count': release.get('medium-track-count', 0)
                }
                albums.append(album)
        
        return jsonify({'success': True, 'albums': albums})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/set-album', methods=['POST'])
def set_album():
    """Manually set album information"""
    data = request.json
    if not data or not data.get('release_id'):
        return jsonify({'success': False, 'error': 'No release ID provided'})
    
    try:
        # Get detailed release info
        result = musicbrainzngs.get_release_by_id(
            data['release_id'],
            includes=["artists", "recordings", "media"]
        )
        
        if result and 'release' in result:
            release = result['release']
            player.album_info = {
                'artist': release['artist-credit'][0]['artist']['name'],
                'album': release['title'],
                'year': release.get('date', '').split('-')[0],
                'manually_set': True
            }
            
            # Update track titles if available
            if 'medium-list' in release and len(release['medium-list']) > 0:
                tracks = release['medium-list'][0].get('track-list', [])
                for i, track in enumerate(tracks):
                    if i < len(player.track_info):
                        player.track_info[i]['title'] = track['recording']['title']
            
            return jsonify({
                'success': True, 
                'album': player.album_info,
                'tracks': player.track_info
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/settings', methods=['GET', 'POST'])
def stream_settings():
    """Get or update stream quality settings"""
    if request.method == 'POST':
        data = request.json
        if data:
            # Update settings with validation
            if 'bitrate' in data:
                # Validate bitrate (32k-320k)
                bitrate = data['bitrate']
                if bitrate in ['32k', '64k', '96k', '128k', '192k', '256k', '320k']:
                    player.stream_settings['bitrate'] = bitrate
            
            if 'buffer_size' in data:
                # Validate buffer size
                buffer_size = data['buffer_size']
                if buffer_size in ['64k', '128k', '256k', '512k', '1024k']:
                    player.stream_settings['buffer_size'] = buffer_size
            
            if 'paranoia_mode' in data:
                # Validate paranoia mode
                mode = data['paranoia_mode']
                if mode in ['fast', 'normal', 'paranoid']:
                    player.stream_settings['paranoia_mode'] = mode
            
            if 'preload_seconds' in data:
                # Validate preload time (0-10 seconds)
                preload = int(data['preload_seconds'])
                if 0 <= preload <= 10:
                    player.stream_settings['preload_seconds'] = preload
    
    return jsonify(player.stream_settings)

@app.route('/api/debug-cd')
def debug_cd():
    """Debug endpoint to see raw CD tool outputs"""
    debug_info = {}
    
    # Try cd-discid
    try:
        cmd = ['cd-discid', player.cd_device]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        debug_info['cd-discid'] = {
            'output': result.stdout.strip(),
            'stderr': result.stderr,
            'returncode': result.returncode
        }
        
        # Parse the output
        if result.stdout:
            parts = result.stdout.strip().split()
            if len(parts) >= 4:
                debug_info['parsed'] = {
                    'disc_id': parts[0],
                    'track_count': parts[1],
                    'offsets': parts[2:-1],
                    'disc_length_frames': parts[-1],
                    'disc_length_seconds': int(parts[-1]) // 75
                }
    except Exception as e:
        debug_info['cd-discid'] = {'error': str(e)}
    
    # Try cdparanoia
    try:
        cmd = ['cdparanoia', '-Q', '-d', player.cd_device]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        debug_info['cdparanoia'] = {
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except Exception as e:
        debug_info['cdparanoia'] = {'error': str(e)}
        
    return jsonify(debug_info)

@app.route('/api/stream/<int:track>')
def stream_track(track):
    """Stream audio data for a specific track"""
    
    # Add cache headers for better mobile performance
    def generate():
        # For CD audio, we need to specify the track differently
        # Track selection in ffmpeg for CD audio uses -ss (seek start)
        # We'll use cdparanoia for more reliable track extraction
        
        # First try cdparanoia which handles CD tracks better
        try:
            # Build cdparanoia command based on settings
            cmd = ['cdparanoia', '-d', player.cd_device, '-r']
            
            # Apply paranoia mode settings
            if player.stream_settings['paranoia_mode'] == 'fast':
                cmd.extend(['-Z', '-Y', '--never-skip=10'])
            elif player.stream_settings['paranoia_mode'] == 'normal':
                cmd.extend(['-Y', '--never-skip=20'])
            # 'paranoid' mode uses default settings (no flags)
            
            cmd.extend([str(track), '-'])  # track number and output to stdout
            
            # Pipe cdparanoia output to ffmpeg for MP3 encoding
            cdp_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', 's16le',  # raw PCM input
                '-ar', '44100',  # sample rate
                '-ac', '2',  # stereo
                '-i', '-',  # input from stdin
                '-acodec', 'mp3',
                '-ab', player.stream_settings['bitrate'],
                '-bufsize', player.stream_settings['buffer_size'],
                '-maxrate', player.stream_settings['bitrate'],
                '-f', 'mp3',
                '-'  # output to stdout
            ]
            
            ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd, 
                stdin=cdp_process.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )
            
            cdp_process.stdout.close()  # Allow cdparanoia to receive SIGPIPE
            
            try:
                while True:
                    data = ffmpeg_process.stdout.read(4096)
                    if not data:
                        break
                    yield data
            finally:
                cdp_process.terminate()
                ffmpeg_process.terminate()
                
        except Exception as e:
            # Fallback to direct ffmpeg if cdparanoia fails
            print(f"cdparanoia failed: {e}, falling back to ffmpeg")
            
            cmd = [
                'ffmpeg',
                '-f', 'libcdio',
                '-i', player.cd_device,
                '-map', f'0:a:{track-1}',  # Map audio track (0-indexed)
                '-acodec', 'mp3',
                '-ab', '192k',
                '-f', 'mp3',
                '-'
            ]
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            try:
                while True:
                    data = process.stdout.read(4096)
                    if not data:
                        break
                    yield data
            finally:
                process.terminate()
    
    response = Response(generate(), mimetype='audio/mpeg')
    # Add headers for better mobile streaming
    response.headers['Accept-Ranges'] = 'none'  # We don't support range requests yet
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

if __name__ == '__main__':
    # Check if running in production (systemd) or development
    import os
    if os.environ.get('FLASK_ENV') == 'development':
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        # Production mode - no debug, no auto-reload
        app.run(host='0.0.0.0', port=5000)