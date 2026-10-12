#!/bin/bash
set -euo pipefail
trap 'code=$?; if [[ $code -ne 0 ]]; then echo "Parche interrumpido (código $code).";read -r -p "Enter para salir..." _ || true;fi' EXIT
BASE="$(cd "$(dirname "$0")" && pwd)"
PANEL="$BASE/extension"
USER_EXT="$HOME/Library/Application Support/Adobe/CEP/extensions"
ENGINE="$HOME/Library/Application Support/TomoTrackAI3/engine/TomoTrackNano/TomoTrackNano"
DEST="$USER_EXT/com.tomo.trackai32"
BACKUP="$HOME/Library/Application Support/TomoTrackAI3/respaldos/panel-$(date +%Y%m%d-%H%M%S)"
echo "TomoTrackAI v0.3.2 - PARCHE LIVIANO"
echo "No reinstala modelos ni motor. No necesita Internet."
if [[ ! -f "$PANEL/CSXS/manifest.xml" || ! -f "$PANEL/jsx/host.jsx" ]]; then
  echo "Faltan archivos del parche junto al instalador.";exit 1
fi
if [[ ! -x "$ENGINE" ]]; then
  echo "No se encontró el motor NanoTrack v0.3 instalado."
  echo "Instalá el paquete completo v0.3.1 antes de este parche.";exit 1
fi
if pgrep -fl "After Effects" >/dev/null 2>&1; then
  echo "After Effects parece estar abierto."
  echo "Cerralo COMPLETAMENTE antes de continuar (Cmd+Q)."
  read -r -p "Enter cuando lo hayas cerrado o Ctrl+C para cancelar..." _
fi
mkdir -p "$USER_EXT" "$BACKUP"
archive_and_remove(){
 local old="$1" label="$2"
 if [[ -d "$old" ]]; then
    echo "Respaldando panel anterior: $label"
    ditto "$old" "$BACKUP/$label"
    rm -rf "$old"
 fi
}
archive_and_remove "$USER_EXT/com.tomo.trackai3" "panel-v03"
archive_and_remove "$USER_EXT/com.tomo.trackai2" "panel-v02"
archive_and_remove "$USER_EXT/com.tomo.trackai32" "panel-v032-previo"
ditto "$PANEL" "$DEST"
xattr -dr com.apple.quarantine "$DEST" 2>/dev/null || true
defaults write com.adobe.CSXS.11 PlayerDebugMode 1
defaults write com.adobe.CSXS.12 PlayerDebugMode 1
echo ""
echo "PANEL v0.3.2 INSTALADO."
echo "La extensión antigua se respaldó en: $BACKUP"
echo "No se tocó NanoTrack, sus modelos ni ningún proyecto de AE."
echo "Ahora abrí AE 2024 > Ventana > Extensiones (heredadas) > TomoTrackAI."
echo "Deberías leer: Puente AE: v0.3.2 verificado."
read -r -p "Enter para terminar..." _
