# WebCD - Web-based CD Player

[![Build Debian Package](https://github.com/GlassOnTin/webcd/actions/workflows/build-deb.yml/badge.svg)](https://github.com/GlassOnTin/webcd/actions/workflows/build-deb.yml)
[![GitHub Release](https://img.shields.io/github/v/release/GlassOnTin/webcd)](https://github.com/GlassOnTin/webcd/releases)

A web interface for playing audio CDs using FFmpeg streaming.

## Features

- Web-based CD player interface
- Track listing and navigation
- Real-time audio streaming using FFmpeg
- Play/Pause/Stop controls
- Previous/Next track navigation
- Automatic track progression
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

Then start the service:
```bash
sudo systemctl start webcd
sudo systemctl enable webcd  # Optional: start on boot
```

### Option 2: Install from Source

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

### With Debian Package

If installed via the Debian package, WebCD runs as a system service:

```bash
# Check service status
sudo systemctl status webcd

# View logs
sudo journalctl -u webcd -f
```

Access the web interface at: http://localhost:5000

### With Source Installation

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

- Default CD device: `/dev/cdrom`
- To use a different device, edit `self.cd_device` in `app.py`
- For `/dev/sr0`, change line 16 to: `self.cd_device = "/dev/sr0"`

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