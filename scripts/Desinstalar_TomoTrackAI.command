#!/bin/bash
set -euo pipefail
ROOT="$HOME/Library/Application Support/TomoTrackAI3"
EXT="$HOME/Library/Application Support/Adobe/CEP/extensions/com.tomo.trackai41"
echo "Desinstalador TomoTrackAI v0.4.1"
echo "Se quitan solamente la extensión y el motor de TomoTrackAI v0.4.1."
echo "Los backups de plugins anteriores permanecen en su carpeta, si existen."
read -r -p "¿Desinstalar TomoTrackAI v0.4.1? [s/N]: " answer || answer=N
if [[ "$answer" =~ ^[sS]$ ]];then
  [[ -d "$EXT" ]] && rm -rf "$EXT"
  [[ -d "$ROOT/engine" ]] && rm -rf "$ROOT/engine"
  # Se conservan los modelos ONNX para que la versión estable pueda volver a usarlos.
  echo "TomoTrackAI v0.4.1 desinstalado. Los respaldos y datos guardados siguen disponibles."
else
  echo "No se modificó nada."
fi
read -r -p "Enter para salir..." _