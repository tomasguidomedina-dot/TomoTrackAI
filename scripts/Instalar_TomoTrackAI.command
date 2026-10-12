#!/bin/bash
# TomoTrackAI PlateTrack v0.5.0 — offline Mac Intel / AE2024.
# Keeps v0.3.2 and v0.4.1 engines untouched; backs up old CEP panels.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
HOME5="$HOME/Library/Application Support/TomoTrackAI5"
CEP="$HOME/Library/Application Support/Adobe/CEP/extensions"
MOTOR="$HOME5/engine/TomoPlateTrack"
PANEL="$CEP/com.tomo.trackai50"
BACKUP="$HOME5/respaldos/pre-v0.5.0-$(date +%Y%m%d-%H%M%S)"
STAGE=""
clean() {
  code=$?
  if [[ -n "$STAGE" && -d "$STAGE" ]]; then rm -rf "$STAGE"; fi
  if [[ "$code" -ne 0 ]];then
    echo "Instalación interrumpida (código $code). Revisá el mensaje anterior."
    read -r -p "Enter para salir..." _ || true
  fi
}
trap clean EXIT
echo "TomoTrackAI v0.5 — PlateTrack OpenCV · 100 % LOCAL"
echo "No instala modelos ONNX, ni ejecuta curl, ni modifica tus otros plugins."
if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "x86_64" ]];then
  echo "Requiere macOS Intel.";exit 1
fi
if pgrep -fl "After Effects" >/dev/null 2>&1;then
  echo "Cerrá After Effects con Cmd+Q antes de instalar.";exit 1
fi
if [[ ! -x "$ROOT/TomoPlateTrack/TomoPlateTrack" || ! -f "$ROOT/extension/CSXS/manifest.xml" ]];then
  echo "Faltan el motor PlateTrack o el panel CEP en el paquete.";exit 1
fi
mkdir -p "$HOME5/staging" "$HOME5/engine" "$CEP" "$BACKUP"
STAGE="$(mktemp -d "$HOME5/staging/precheck-XXXXXX")"
ditto "$ROOT/TomoPlateTrack" "$STAGE/TomoPlateTrack"
chmod +x "$STAGE/TomoPlateTrack/TomoPlateTrack"
xattr -dr com.apple.quarantine "$STAGE/TomoPlateTrack" 2>/dev/null || true
echo "Probando arranque del motor PlateTrack ANTES de tocar la instalación (límite 20 segundos)..."
printf '{"cmd":"close"}\n' > "$STAGE/input"
"$STAGE/TomoPlateTrack/TomoPlateTrack" < "$STAGE/input" > "$STAGE/out" 2> "$STAGE/err" &
PID=$!
OK=0
for ((i=1;i<=80;i++));do
  if /usr/bin/grep -q '"ready":true' "$STAGE/out" && /usr/bin/grep -q '"PlateTrack"' "$STAGE/out";then
    OK=1;break
  fi
  if ! kill -0 "$PID" 2>/dev/null;then break;fi
  sleep .25
done
if [[ "$OK" -ne 1 ]];then
  kill "$PID" 2>/dev/null || true
  sleep .2
  kill -9 "$PID" 2>/dev/null || true
  wait "$PID" 2>/dev/null || true
  echo "El motor nuevo NO respondió a tiempo: NO se reemplazó ningún panel ni motor."
  /usr/bin/head -c 500 "$STAGE/err" || true
  exit 1
fi
wait "$PID" 2>/dev/null || true
echo "Motor PlateTrack local: listo."
# Use a different Application Support root, never overwrite the proven NanoTrack engine.
if [[ -d "$MOTOR" ]];then
  ditto "$MOTOR" "$BACKUP/TomoPlateTrack-anterior"
  rm -rf "$MOTOR"
fi
ditto "$STAGE/TomoPlateTrack" "$MOTOR"
chmod +x "$MOTOR/TomoPlateTrack"
for id in com.tomo.trackai3 com.tomo.trackai32 com.tomo.trackai40 com.tomo.trackai41 com.tomo.trackai50;do
  if [[ -d "$CEP/$id" ]];then
    ditto "$CEP/$id" "$BACKUP/$id"
    rm -rf "$CEP/$id"
  fi
done
ditto "$ROOT/extension" "$PANEL"
xattr -dr com.apple.quarantine "$PANEL" 2>/dev/null || true
defaults write com.adobe.CSXS.11 PlayerDebugMode 1
defaults write com.adobe.CSXS.12 PlayerDebugMode 1
echo ""
echo "TomoTrackAI v0.5 instalado. AE 2024 > Ventana > Extensiones (heredadas) > TomoTrackAI"
echo "Motor v0.3.2 y sus modelos anteriores intactos. Panel anterior respaldado en $BACKUP"
echo "Este es un candidato experimental hasta probarlo en After Effects en tu Mac."
read -r -p "Enter para cerrar..." _ || true
