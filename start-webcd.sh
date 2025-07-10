#!/bin/bash
systemctl --user start webcd
echo "WebCD started. Access it at http://localhost:5000"
echo "Check status with: systemctl --user status webcd"
