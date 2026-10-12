#!/bin/bash
# TomoTrackAI v0.6.1: corrige botón de exportación, panel únicamente.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PANEL="$HOME/Library/Application Support/Adobe/CEP/extensions/com.tomo.trackai60"
BASE="$HOME/Library/Application Support/TomoTrackAI6/respaldos-ui"
BACKUP=""
on_error(){
  echo "ERROR: no se pudo instalar el parche."
  if [[ -n "$BACKUP" && -f "$BACKUP/panel.js" && -d "$PANEL" ]];then
    cp "$BACKUP/panel.js" "$PANEL/panel.js" || true
    echo "Se restauró el panel anterior."
  fi
  read -r -p "Enter para salir..." _ || true
}
trap on_error ERR
echo "TomoTrackAI v0.6.1 — corregir botón Crear capa estabilizada"
echo "Este parche cambia SÓLO el panel.js de la v0.6."
echo "No toca motor, máscaras, video, proyecto ni la v0.5."
if pgrep -x "After Effects" >/dev/null 2>&1 || pgrep -x "After Effects 2024" >/dev/null 2>&1;then
  echo "Cerrá After Effects con Cmd+Q y volvé a ejecutar este parche."
  read -r -p "Enter para salir..." _ || true;exit 1
fi
if [[ ! -f "$ROOT/panel.js" || ! -f "$PANEL/CSXS/manifest.xml" || ! -f "$PANEL/panel.js" ]];then
  echo "No se encontró un parche completo o el panel v0.6 instalado."
  read -r -p "Enter para salir..." _ || true;exit 1
fi
if ! grep -q 'com.tomo.trackai60' "$PANEL/CSXS/manifest.xml" ||
   ! grep -q 'platetrack-0.6.0-bridge-20261012' "$PANEL/panel.js" ||
   ! grep -q 'platetrack-0.6.0-bridge-20261012' "$ROOT/panel.js";then
  echo "Versión inesperada. Se cancela para evitar romper la instalación."
  read -r -p "Enter para salir..." _ || true;exit 1
fi
mkdir -p "$BASE"
BACKUP="$(mktemp -d "$BASE/pre-v0.6.1-XXXXXXXX")"
cp "$PANEL/panel.js" "$BACKUP/panel.js"
cp "$ROOT/panel.js" "$PANEL/panel.js.tmp_v061"
mv -f "$PANEL/panel.js.tmp_v061" "$PANEL/panel.js"
xattr -d com.apple.quarantine "$PANEL/panel.js" 2>/dev/null || true
trap - ERR
echo "Parche instalado. Respaldo: $BACKUP"
echo "Abrí AE > Ventana > Extensiones (heredadas) > TomoTrackAI · Estabilización v0.6."
echo "Es necesario repetir el análisis: cerrar AE reinicia la sesión del motor."
read -r -p "Enter para salir..." _ || true
