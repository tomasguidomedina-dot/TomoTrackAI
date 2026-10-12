#!/bin/bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SOURCE="$HERE/TomoTrack_Native_Check.plugin"
DEST="/Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore/TomoTrack_Native_Check.plugin"
if [ ! -d "$SOURCE" ]; then
  echo "Error: el archivo .plugin no esta junto al instalador."
  read -r -p "Presiona Enter para salir..."
  exit 1
fi
echo "Instalando solo TomoTrack Native Check (no modifica TomoTrackAI anterior)..."
sudo mkdir -p "$(dirname "$DEST")"
sudo rm -rf "$DEST"
sudo ditto "$SOURCE" "$DEST"
sudo xattr -dr com.apple.quarantine "$DEST" 2>/dev/null || true
echo "Instalado. Reinicia After Effects y busca Efecto > Tomo FX > TomoTrack Native Check."
read -r -p "Presiona Enter para cerrar..."
