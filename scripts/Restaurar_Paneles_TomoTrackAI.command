#!/bin/bash
set -euo pipefail
CEP="$HOME/Library/Application Support/Adobe/CEP/extensions"
APP="$HOME/Library/Application Support/TomoTrackAI"
PANEL="$CEP/com.tomo.trackai"
ENGINE="$APP/engine/TomoPlateTrack"
ROOT="$APP/respaldos-extensiones"
echo "Restaurar extensiones anteriores de TomoTrackAI"
if pgrep -x "After Effects" >/dev/null 2>&1 || pgrep -x "After Effects 2024" >/dev/null 2>&1;then
  echo "Cerrá After Effects antes de restaurar.";exit 1
fi
LATEST=""
for b in "$ROOT"/unificacion_*;do
  [[ -d "$b/anteriores" ]] || continue
  if [[ -z "$LATEST" || "$b" -nt "$LATEST" ]];then LATEST="$b";fi
done
if [[ -z "$LATEST" ]];then echo "No hay respaldo previo.";exit 1;fi
echo "Restaurar desde: $LATEST"
echo "Esto volverá a mostrar paneles antiguos en AE. Usalo sólo como rollback."
read -r -p "¿Restaurar? [s/N]: " reply
[[ "$reply" == "s" || "$reply" == "S" ]] || exit 0
mkdir -p "$LATEST/rollback-unificado"
if [[ -d "$PANEL" ]];then mv "$PANEL" "$LATEST/rollback-unificado/com.tomo.trackai";fi
if [[ -d "$ENGINE" ]];then mv "$ENGINE" "$LATEST/rollback-unificado/TomoPlateTrack";fi
if [[ -d "$LATEST/unificado-anterior" ]];then mv "$LATEST/unificado-anterior" "$PANEL";fi
if [[ -d "$LATEST/motor-anterior" ]];then mv "$LATEST/motor-anterior" "$ENGINE";fi
for prior in "$LATEST"/anteriores/com.tomo.trackai[0-9]*;do
  [[ -d "$prior" ]] || continue
  dest="$CEP/$(basename "$prior")"
  if [[ -e "$dest" ]];then echo "Ya existe $dest — no sobreescribo";continue;fi
  mv "$prior" "$dest"
done
echo "Paneles previos restaurados. Ningún proyecto de AE modificado."
read -r -p "Enter para salir..." _ || true
