#!/bin/bash
# WebCD systemd service installation script

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Please run: sudo $0"
    exit 1
fi

echo -e "${GREEN}WebCD Systemd Service Installer${NC}"
echo "================================="

# Default installation directory
INSTALL_DIR="/opt/webcd"
SERVICE_USER="webcd"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --user)
            SERVICE_USER="$2"
            shift 2
            ;;
        --uninstall)
            echo -e "${YELLOW}Uninstalling WebCD service...${NC}"
            systemctl stop webcd.service 2>/dev/null || true
            systemctl disable webcd.service 2>/dev/null || true
            rm -f /etc/systemd/system/webcd.service
            systemctl daemon-reload
            echo -e "${GREEN}WebCD service uninstalled successfully${NC}"
            exit 0
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --install-dir DIR    Installation directory (default: /opt/webcd)"
            echo "  --user USER         Service user (default: webcd)"
            echo "  --uninstall         Uninstall the service"
            echo "  -h, --help          Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Check if source files exist
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
if [ ! -f "$SCRIPT_DIR/app.py" ]; then
    echo -e "${RED}Error: app.py not found in $SCRIPT_DIR${NC}"
    echo "Please run this script from the WebCD source directory"
    exit 1
fi

echo "Installation directory: $INSTALL_DIR"
echo "Service user: $SERVICE_USER"
echo

# Create service user if it doesn't exist
if ! id "$SERVICE_USER" &>/dev/null; then
    echo -e "${YELLOW}Creating service user: $SERVICE_USER${NC}"
    useradd --system --home-dir "$INSTALL_DIR" --shell /bin/false "$SERVICE_USER"
    usermod -a -G cdrom,audio "$SERVICE_USER"
else
    echo -e "${GREEN}User $SERVICE_USER already exists${NC}"
    # Ensure user is in required groups
    usermod -a -G cdrom,audio "$SERVICE_USER"
fi

# Create installation directory
echo -e "${YELLOW}Creating installation directory...${NC}"
mkdir -p "$INSTALL_DIR"

# Copy application files
echo -e "${YELLOW}Copying application files...${NC}"
cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/" || true

# Create virtual environment if it doesn't exist
if [ ! -d "$INSTALL_DIR/venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv "$INSTALL_DIR/venv"
fi

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# Set ownership
echo -e "${YELLOW}Setting file ownership...${NC}"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

# Create systemd service file
echo -e "${YELLOW}Creating systemd service file...${NC}"
cat > /etc/systemd/system/webcd.service << EOF
[Unit]
Description=WebCD - Web-based CD Player
Documentation=https://github.com/GlassOnTin/webcd
After=network.target sound.target

[Service]
Type=simple
User=$SERVICE_USER
Group=cdrom
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$INSTALL_DIR"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/app.py
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/tmp
ReadOnlyPaths=$INSTALL_DIR
# Allow access to CD devices
DeviceAllow=/dev/cdrom rw
DeviceAllow=/dev/dvd rw
DeviceAllow=/dev/sr0 rw
DeviceAllow=/dev/sr1 rw
DeviceAllow=/dev/sr2 rw
DeviceAllow=char-* rw
DevicePolicy=closed
SupplementaryGroups=cdrom audio

# Resource limits
MemoryLimit=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
echo -e "${YELLOW}Reloading systemd daemon...${NC}"
systemctl daemon-reload

# Enable and start service
echo -e "${YELLOW}Enabling and starting WebCD service...${NC}"
systemctl enable webcd.service
systemctl start webcd.service

# Check service status
sleep 2
if systemctl is-active --quiet webcd.service; then
    echo -e "${GREEN}✓ WebCD service is running successfully!${NC}"
    echo
    echo "Service status:"
    systemctl status webcd.service --no-pager
    echo
    echo -e "${GREEN}WebCD is now accessible at: http://localhost:5000${NC}"
    echo
    echo "Useful commands:"
    echo "  systemctl status webcd    # Check service status"
    echo "  systemctl stop webcd      # Stop service"
    echo "  systemctl start webcd     # Start service"
    echo "  systemctl restart webcd   # Restart service"
    echo "  journalctl -u webcd -f    # View logs"
else
    echo -e "${RED}✗ Failed to start WebCD service${NC}"
    echo "Check logs with: journalctl -u webcd -n 50"
    exit 1
fi