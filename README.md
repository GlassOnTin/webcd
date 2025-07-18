# WebCD - Web-based CD Player

[![Build Debian Package](https://github.com/GlassOnTin/webcd/actions/workflows/build-deb.yml/badge.svg)](https://github.com/GlassOnTin/webcd/actions/workflows/build-deb.yml)
[![GitHub Release](https://img.shields.io/github/release/GlassOnTin/webcd.svg)](https://github.com/GlassOnTin/webcd/releases)

A web interface for playing audio CDs using FFmpeg streaming.

## Features

- Web-based CD player interface
- Track listing and navigation
- Real-time audio streaming using FFmpeg
- Multiple audio format support:
  - MP3 (32-320 kbps) - compressed, bandwidth-efficient
  - FLAC - lossless compression (~850 kbps)
  - WAV - uncompressed, original CD quality (~1411 kbps)
- Play/Pause/Stop controls
- Previous/Next track navigation
- Eject CD functionality
- Automatic track progression
- Multi-device support (multiple CD/DVD drives)
- Automatic device detection
- Album metadata lookup (GNUDB/MusicBrainz)
- Responsive design

## Requirements

- Python 3.8+
- FFmpeg with libcdio support
- Audio CD in CD-ROM drive

## Installation

### Option 1: Install from Debian Package (Recommended)

Download the latest `.deb` package from the [Releases page](https://github.com/GlassOnTin/webcd/releases) and install:

```bash
sudo dpkg -i webcd_*.deb
sudo apt-get install -f  # Install any missing dependencies
```

The service will start automatically after installation. You can manage it with:
```bash
sudo systemctl status webcd   # Check service status
sudo systemctl restart webcd  # Restart service
sudo systemctl stop webcd     # Stop service
sudo journalctl -u webcd -f   # View logs
```

### Option 2: Install as Systemd Service (From Source)

Clone the repository and use the installation script:

```bash
git clone https://github.com/GlassOnTin/webcd.git
cd webcd
sudo ./install-service.sh
```

The script will:
- Create a system user for WebCD
- Install the application to `/opt/webcd`
- Set up a Python virtual environment
- Install all dependencies
- Configure and start the systemd service

To uninstall:
```bash
sudo ./install-service.sh --uninstall
```

### Option 3: Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/GlassOnTin/webcd.git
cd webcd
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### With Debian Package or Systemd Service

If installed via the Debian package or systemd installation script, WebCD runs as a system service:

```bash
# Check service status
sudo systemctl status webcd

# View logs
sudo journalctl -u webcd -f
```

Access the web interface at: http://localhost:5000

### With Manual Installation

1. Insert an audio CD into your CD-ROM drive

2. Activate the virtual environment:
```bash
source venv/bin/activate
```

3. Run the application:
```bash
python app.py
```

4. Open your browser to: http://localhost:5000

## Configuration

### CD/DVD Device Selection

WebCD automatically detects available CD/DVD devices on your system. You can:

1. **Use the Web Interface**: Click "Select Device" to choose from available devices
2. **Set Environment Variable**: 
   ```bash
   export WEBCD_DEVICE=/dev/sr0
   python app.py
   ```
3. **For systemd service**: Edit `/etc/systemd/system/webcd.service` and add:
   ```
   Environment="WEBCD_DEVICE=/dev/sr0"
   ```
   Then reload and restart:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart webcd
   ```

The application will automatically detect devices at:
- `/dev/cdrom` (default symlink)
- `/dev/dvd` 
- `/dev/sr0`, `/dev/sr1`, `/dev/sr2` (SCSI/SATA devices)

### Stream Quality Settings

Configure streaming quality through the web interface settings panel:

- **Audio Format**: Choose between MP3, FLAC, or WAV
- **Bitrate** (MP3 only): 32-320 kbps
- **Buffer Size**: Adjust for network conditions
- **Read Mode**: Fast/Normal/Paranoid (affects error correction)
- **Preload Time**: Buffer before playback starts

Settings are automatically saved and persist between sessions.

### Systemd Service Customization

For advanced users who want to customize the systemd service:

1. **Change listening port**: Edit the service file and add:
   ```
   Environment="FLASK_RUN_PORT=8080"
   ```

2. **Adjust resource limits**:
   ```
   MemoryLimit=1G
   CPUQuota=80%
   ```

3. **Custom installation path** (for manual installations):
   ```bash
   sudo ./install-service.sh --install-dir /path/to/webcd --user myuser
   ```

After any changes to the service file:
```bash
sudo systemctl daemon-reload
sudo systemctl restart webcd
```

## Troubleshooting

- **No CD detected**: Ensure CD is properly inserted and the device path is correct
- **Permission denied**: Add your user to the `cdrom` group: `sudo usermod -a -G cdrom $USER`
- **FFmpeg not found**: Install FFmpeg with libcdio: `sudo apt install ffmpeg`

## API Endpoints

- `GET /` - Main web interface
- `GET /api/cd-info` - Get CD track information
- `POST /api/play` - Start playback (optional track number in JSON body)
- `POST /api/stop` - Stop playback
- `POST /api/next` - Skip to next track
- `POST /api/previous` - Skip to previous track
- `GET /api/status` - Get player status
- `GET /api/stream/<track>` - Stream audio for specific track

## Development

To run in debug mode with auto-reload:
```bash
FLASK_ENV=development python app.py
```

## License

MIT