#!/bin/bash
set -euo pipefail
ROOT="$HOME/Library/Application Support/TomoTrackAI2"
EXT="$HOME/Library/Application Support/Adobe/CEP/extensions/com.tomo.trackai2"
echo "Se quitará sólo el MOTOR y panel de TomoTrackAI 0.2."
echo "No se borrará el efecto nativo ROI Select ni versiones anteriores."
[[ -d "$EXT" ]] && rm -rf "$EXT"
[[ -d "$ROOT" ]] && rm -rf "$ROOT"
echo "Desinstalado. Native Check y ROI Select continúan intactos."
read -r -p "Enter para cerrar..." _
