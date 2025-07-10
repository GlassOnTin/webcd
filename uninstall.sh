#!/bin/bash

# WebCD Uninstallation Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}WebCD Uninstallation Script${NC}"
echo "============================"

# Stop the service if running
if systemctl --user is-active --quiet webcd; then
    echo -e "\n${YELLOW}Stopping WebCD service...${NC}"
    systemctl --user stop webcd
fi

# Disable the service if enabled
if systemctl --user is-enabled --quiet webcd 2>/dev/null; then
    echo -e "${YELLOW}Disabling WebCD service...${NC}"
    systemctl --user disable webcd
fi

# Remove service files
echo -e "\n${YELLOW}Removing systemd service files...${NC}"
rm -f ~/.config/systemd/user/webcd.service
rm -f ~/.config/systemd/user/webcd@.service

# Reload systemd
systemctl --user daemon-reload

# Remove convenience scripts
echo -e "\n${YELLOW}Removing convenience scripts...${NC}"
rm -f start-webcd.sh
rm -f stop-webcd.sh
rm -f status-webcd.sh

echo -e "\n${GREEN}✓ WebCD service has been uninstalled${NC}"
echo
echo "Note: The application files and virtual environment have been preserved."
echo "To completely remove WebCD, delete the entire directory:"
echo "  rm -rf ~/Code/webcd"
echo
echo "To remove system dependencies (if no longer needed):"
echo "  sudo apt remove ffmpeg cdparanoia"