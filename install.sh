#!/bin/bash

# WebCD Installation Script
# This script installs WebCD as a systemd user service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the current user
CURRENT_USER=$(whoami)

echo -e "${GREEN}WebCD Installation Script${NC}"
echo "=========================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}Please do not run this script as root${NC}"
   exit 1
fi

# Check if we're in the right directory
if [ ! -f "app.py" ] || [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: This script must be run from the WebCD directory${NC}"
    echo "Please cd to ~/Code/webcd and run again"
    exit 1
fi

# Check dependencies
echo -e "\n${YELLOW}Checking system dependencies...${NC}"

deps_missing=false

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    deps_missing=true
else
    echo -e "${GREEN}✓ Python 3 found${NC}"
fi

if ! command -v ffmpeg &> /dev/null; then
    echo -e "${RED}✗ FFmpeg is not installed${NC}"
    deps_missing=true
else
    echo -e "${GREEN}✓ FFmpeg found${NC}"
fi

if ! command -v cdparanoia &> /dev/null; then
    echo -e "${YELLOW}⚠ cdparanoia is not installed (optional but recommended)${NC}"
    echo "  Install with: sudo apt install cdparanoia"
fi

if ! command -v cd-discid &> /dev/null; then
    echo -e "${YELLOW}⚠ cd-discid is not installed (optional for CDDB support)${NC}"
    echo "  Install with: sudo apt install cd-discid"
fi

if [ "$deps_missing" = true ]; then
    echo -e "\n${RED}Missing dependencies. Please install them first:${NC}"
    echo "sudo apt update"
    echo "sudo apt install python3 python3-venv ffmpeg cdparanoia"
    exit 1
fi

# Check if user is in cdrom group
if ! groups | grep -q cdrom; then
    echo -e "\n${YELLOW}Warning: You are not in the 'cdrom' group${NC}"
    echo "You may need to run: sudo usermod -a -G cdrom $CURRENT_USER"
    echo "Then log out and back in for the changes to take effect"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "\n${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Install Python dependencies
echo -e "\n${YELLOW}Installing Python dependencies...${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# Create systemd user directory if it doesn't exist
mkdir -p ~/.config/systemd/user/

# Install the service file
echo -e "\n${YELLOW}Installing systemd service...${NC}"
# Use the simpler service file for user services
if [ -f "webcd-simple.service" ]; then
    cp webcd-simple.service ~/.config/systemd/user/webcd.service
else
    cp webcd.service ~/.config/systemd/user/webcd.service
fi

# Reload systemd
systemctl --user daemon-reload

# Create convenience scripts
echo -e "\n${YELLOW}Creating convenience scripts...${NC}"

# Start script
cat > start-webcd.sh << 'EOF'
#!/bin/bash
systemctl --user start webcd
echo "WebCD started. Access it at http://localhost:5000"
echo "Check status with: systemctl --user status webcd"
EOF
chmod +x start-webcd.sh

# Stop script
cat > stop-webcd.sh << 'EOF'
#!/bin/bash
systemctl --user stop webcd
echo "WebCD stopped."
EOF
chmod +x stop-webcd.sh

# Status script
cat > status-webcd.sh << 'EOF'
#!/bin/bash
systemctl --user status webcd
EOF
chmod +x status-webcd.sh

# Enable service to start on boot (optional)
echo -e "\n${YELLOW}Do you want WebCD to start automatically on boot? (y/N)${NC}"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    systemctl --user enable webcd
    echo -e "${GREEN}✓ WebCD will start automatically on boot${NC}"
else
    echo "WebCD will not start automatically (you can enable this later with: systemctl --user enable webcd)"
fi

echo -e "\n${GREEN}Installation complete!${NC}"
echo
echo "Available commands:"
echo "  ./start-webcd.sh   - Start the WebCD service"
echo "  ./stop-webcd.sh    - Stop the WebCD service"
echo "  ./status-webcd.sh  - Check service status"
echo
echo "Or use systemctl directly:"
echo "  systemctl --user start webcd"
echo "  systemctl --user stop webcd"
echo "  systemctl --user status webcd"
echo "  systemctl --user restart webcd"
echo
echo "Logs can be viewed with:"
echo "  journalctl --user -u webcd -f"
echo
echo -e "${YELLOW}Would you like to start WebCD now? (y/N)${NC}"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    systemctl --user start webcd
    sleep 2
    if systemctl --user is-active --quiet webcd; then
        echo -e "\n${GREEN}✓ WebCD is running!${NC}"
        echo "Access it at: http://localhost:5000"
    else
        echo -e "\n${RED}✗ Failed to start WebCD${NC}"
        echo "Check logs with: journalctl --user -u webcd -n 50"
    fi
fi