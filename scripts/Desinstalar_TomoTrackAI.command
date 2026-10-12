#!/bin/bash
set -euo pipefail
APP="$HOME/Library/Application Support/TomoTrackAI5"
PANEL="$HOME/Library/Application Support/Adobe/CEP/extensions/com.tomo.trackai50"
echo "Desinstalar únicamente TomoTrackAI PlateTrack v0.5"
echo "No se modificarán TomoTrackAI3, NanoTrack, sus modelos ni otros plugins."
read -r -p "¿Retirar motor/panel PlateTrack v0.5? [s/N]: " answer || answer=N
if [[ "$answer" =~ ^[sS]$ ]];then
   [[ ! -d "$PANEL" ]] || rm -rf "$PANEL"
   [[ ! -d "$APP/engine/TomoPlateTrack" ]] || rm -rf "$APP/engine/TomoPlateTrack"
   echo "v0.5 retirada. Los respaldos permanecen en Application Support/TomoTrackAI5."
else echo "Sin cambios.";fi
read -r -p "Enter para cerrar..." _ || true
