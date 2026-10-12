#!/bin/bash
# Undo only the changes made by v0.4.1 installer.
set -euo pipefail
APP="$HOME/Library/Application Support/TomoTrackAI3"
CEP="$HOME/Library/Application Support/Adobe/CEP/extensions"
MOTOR="$APP/engine/TomoTrackNano"
echo "Restaurar la versión que estaba instalada ANTES de v0.4.1"
echo "AVISO: si antes tenías v0.4, restaurará v0.4, NO necesariamente v0.3.2."
if pgrep -fl 'After Effects' >/dev/null 2>&1;then
  echo "Cerrá After Effects con Cmd+Q.";exit 1
fi
BACKUP=""
for dir in "$APP"/respaldos/pre-v0.4.1-*;do
  [[ -d "$dir/TomoTrackNano" ]] && BACKUP="$dir"
done
if [[ -z "$BACKUP" ]];then
  echo "No existe un backup compatible. No se modificó nada."
  read -r -p "Enter para cerrar..." _ || true
  exit 1
fi
echo "Respaldo encontrado: $BACKUP"
read -r -p "¿Restaurar esa versión? [s/N]: " confirm || confirm="N"
[[ "$confirm" =~ ^[sS]$ ]] || exit 0
SAVED="$APP/respaldos/retirada-v0.4.1-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$SAVED" "$CEP"
if [[ -d "$MOTOR" ]];then mv "$MOTOR" "$SAVED/TomoTrackNano";fi
ditto "$BACKUP/TomoTrackNano" "$MOTOR"
if [[ -d "$CEP/com.tomo.trackai41" ]];then
  mv "$CEP/com.tomo.trackai41" "$SAVED/com.tomo.trackai41"
fi
for id in com.tomo.trackai32 com.tomo.trackai40 com.tomo.trackai3;do
  if [[ -d "$BACKUP/$id" ]];then
    if [[ -d "$CEP/$id" ]];then
      ditto "$CEP/$id" "$SAVED/$id"
      rm -rf "$CEP/$id"
    fi
    ditto "$BACKUP/$id" "$CEP/$id"
    echo "Panel restaurado: $id"
  fi
done
echo "Restauración terminada. Se conservaron los modelos y respaldos."
read -r -p "Enter para cerrar..." _
