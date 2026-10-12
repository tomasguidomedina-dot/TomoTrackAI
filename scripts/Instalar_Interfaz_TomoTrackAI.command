#!/bin/bash
# TomoTrackAI v0.5.1 -- Sólo interfaz. Nunca reemplaza motor PlateTrack.
set -eEuo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PANEL="$HOME/Library/Application Support/Adobe/CEP/extensions/com.tomo.trackai50"
MOTOR="$HOME/Library/Application Support/TomoTrackAI5/engine/TomoPlateTrack/TomoPlateTrack"
BACKROOT="$HOME/Library/Application Support/TomoTrackAI5/respaldos-ui"
BACKUP=""
restore_failed() {
  echo "Error al actualizar la interfaz."
  if [[ -n "$BACKUP" && -d "$BACKUP" ]];then
    cp "$BACKUP/index.html" "$PANEL/index.html" 2>/dev/null || true
    cp "$BACKUP/panel.js" "$PANEL/panel.js" 2>/dev/null || true
    echo "Se intentó restaurar el panel previo."
  fi
  read -r -p "Enter para salir..." _ || true
}
trap restore_failed ERR
echo "TomoTrackAI v0.5.1 · Nueva interfaz estilo Adobe"
echo "NO se modifica PlateTrack, ni ONNX, ni el motor ni las máscaras."
echo "Antes de continuar, cerrá After Effects con Cmd+Q."
if [[ ! -f "$ROOT/index.html" || ! -f "$ROOT/panel.js" ]];then
  echo "El parche debe ejecutarse junto a index.html y panel.js."; exit 1
fi
if [[ ! -f "$PANEL/CSXS/manifest.xml" || ! -f "$PANEL/jsx/host.jsx" || ! -x "$MOTOR" ]];then
  echo "No se encontró una instalación completa de TomoTrackAI v0.5 PlateTrack."
  echo "Primero instalá la versión funcional del plugin.";exit 1
fi
if ! grep -q 'com.tomo.trackai50' "$PANEL/CSXS/manifest.xml";then
 echo "La extensión encontrada no corresponde a v0.5.";exit 1
fi
mkdir -p "$BACKROOT"
BACKUP="$(mktemp -d "$BACKROOT/panel-previo-XXXXXXXX")"
cp "$PANEL/index.html" "$BACKUP/index.html"
cp "$PANEL/panel.js" "$BACKUP/panel.js"
# Copias temporales en el MISMO volumen, reemplazo rápido.
cp "$ROOT/index.html" "$PANEL/index.html.actualizar"
cp "$ROOT/panel.js" "$PANEL/panel.js.actualizar"
mv -f "$PANEL/index.html.actualizar" "$PANEL/index.html"
mv -f "$PANEL/panel.js.actualizar" "$PANEL/panel.js"
xattr -d com.apple.quarantine "$PANEL/index.html" 2>/dev/null || true
xattr -d com.apple.quarantine "$PANEL/panel.js" 2>/dev/null || true
trap - ERR
echo "Interfaz instalada; motor PlateTrack intacto."
echo "Respaldo UI: $BACKUP"
echo "Abrí After Effects > Ventana > Extensiones (heredadas) > TomoTrackAI"
read -r -p "Enter para cerrar..." _ || true
