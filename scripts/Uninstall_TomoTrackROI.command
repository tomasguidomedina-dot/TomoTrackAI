#!/bin/bash
set -euo pipefail
DEST="/Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore/TomoTrack_ROI_Select.plugin"
echo "Desinstalando solamente TomoTrack ROI Select..."
if [[ -d "$DEST" ]]; then sudo rm -rf "$DEST"; fi
echo "Listo. Native Check v0.0.3 y demas plugins quedan intactos."
read -r -p "Enter para terminar..."
