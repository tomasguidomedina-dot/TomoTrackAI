#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="$ROOT/TomoTrack_ROI_Select.plugin"
DEST="/Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore/TomoTrack_ROI_Select.plugin"
if [[ ! -d "$SRC" ]]; then
  echo "Falta TomoTrack_ROI_Select.plugin junto al instalador."
  read -r -p "Enter para salir..."
  exit 1
fi
echo "Instalando TomoTrack ROI Select. No modifica Native Check v0.0.3 ni plugins antiguos."
sudo mkdir -p "$(dirname "$DEST")"
if [[ -d "$DEST" ]]; then sudo rm -rf "$DEST"; fi
sudo ditto "$SRC" "$DEST"
sudo xattr -dr com.apple.quarantine "$DEST" 2>/dev/null || true
echo "Instalado. Reinicia AE y busca Efectos > Tomo FX > TomoTrack ROI Select."
read -r -p "Enter para terminar..."
