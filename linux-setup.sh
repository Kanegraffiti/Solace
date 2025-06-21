#!/bin/bash
# Install system packages for Solace on Debian/Ubuntu

sudo apt-get update
sudo apt-get install -y python3 python3-pip espeak portaudio19-dev ffmpeg

echo "System packages installed. Continue with bash install-safe.sh"

