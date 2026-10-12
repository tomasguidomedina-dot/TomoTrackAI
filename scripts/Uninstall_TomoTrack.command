#!/bin/bash
set -euo pipefail
TARGET="/Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore/TomoTrack_Native_Check.plugin"
echo "Quitando solamente TomoTrack Native Check..."
if [ -d "$TARGET" ]; then
  sudo rm -rf "$TARGET"
  echo "Completado."
else
  echo "No se encontro instalado."
fi
read -r -p "Presiona Enter para cerrar..."
