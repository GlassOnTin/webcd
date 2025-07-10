# WebCD - Web-based CD Player

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

1. Clone the repository:
```bash
cd ~/Code/webcd
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