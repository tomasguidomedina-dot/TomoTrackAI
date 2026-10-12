#!/bin/bash
set -euo pipefail
PANEL="$HOME/Library/Application Support/Adobe/CEP/extensions/com.tomo.trackai50"
BACKROOT="$HOME/Library/Application Support/TomoTrackAI5/respaldos-ui"
echo "Restaurar interfaz TomoTrackAI anterior (motor PlateTrack intacto)"
echo "Cerrá After Effects antes de continuar."
if [[ ! -f "$PANEL/CSXS/manifest.xml" || ! -d "$BACKROOT" ]];then echo "No hay instalación o respaldo UI.";exit 1;fi
LATEST=""
for p in "$BACKROOT"/panel-previo-*;do
  if [[ -f "$p/index.html" && -f "$p/panel.js" ]];then
     [[ -z "$LATEST" || "$p" -nt "$LATEST" ]] && LATEST="$p"
  fi
done
if [[ -z "$LATEST" ]];then echo "No hay respaldo de interfaz válido.";exit 1;fi
echo "Restaurar desde: $LATEST"
read -r -p "¿Confirmás? [s/N]: " reply
if [[ "$reply" != "s" && "$reply" != "S" ]];then echo "Sin cambios";exit 0;fi
cp "$LATEST/index.html" "$PANEL/index.html"
cp "$LATEST/panel.js" "$PANEL/panel.js"
echo "Interfaz anterior restaurada. Motor intacto."
read -r -p "Enter para cerrar..." _ || true
