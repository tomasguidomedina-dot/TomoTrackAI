#!/bin/bash
set -euo pipefail
PANEL="$HOME/Library/Application Support/Adobe/CEP/extensions/com.tomo.trackai60"
ROOT="$HOME/Library/Application Support/TomoTrackAI6/respaldos-ui"
echo "Restaurar panel TomoTrackAI v0.6 anterior al parche"
if pgrep -x "After Effects" >/dev/null 2>&1 || pgrep -x "After Effects 2024" >/dev/null 2>&1;then
 echo "Cerrá completamente After Effects antes de restaurar."
 read -r -p "Enter para salir..." _ || true;exit 1
fi
BACK=""
for item in "$ROOT"/pre-v0.6.1-*;do
 [[ -f "$item/panel.js" ]] || continue
 if [[ -z "$BACK" || "$item" -nt "$BACK" ]];then BACK="$item";fi
done
if [[ -z "$BACK" || ! -d "$PANEL" ]];then echo "No hay respaldo para restaurar.";exit 1;fi
echo "Se restaurará $BACK"
read -r -p "Confirmar [s/N]: " ans
if [[ "$ans" != "s" && "$ans" != "S" ]];then echo "Sin cambios.";exit 0;fi
cp "$BACK/panel.js" "$PANEL/panel.js"
echo "Restauración completa. Motor PlateTrack intacto."
read -r -p "Enter para salir..." _ || true
