#!/bin/bash
set -euo pipefail
trap 'code=$?; if [[ "$code" -ne 0 ]]; then echo "Error de instalación: $code"; read -r -p "Enter para cerrar..." _ || true; fi' EXIT
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$HOME/Library/Application Support/TomoTrackAI2"
TARGET="$ROOT/engine/TomoTrackNano"
MODELS="$ROOT/models"
EXT="$HOME/Library/Application Support/Adobe/CEP/extensions/com.tomo.trackai2"
NATIVE="$DIR/TomoTrack_ROI_Select.plugin"
NATIVE_DEST="/Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore/TomoTrack_ROI_Select.plugin"
echo "TOMOTRACK AI 0.2 - Seguimiento NanoTrack (macOS Intel)"
echo "No requiere instalar Python ni compilar."
if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "x86_64" ]]; then
  echo "Este instalador es solamente para macOS Intel."
  exit 1
fi
if [[ ! -x "$DIR/TomoTrackNano/TomoTrackNano" ]]; then
  echo "Falta el motor TomoTrackNano junto a este instalador."
  exit 1
fi
mkdir -p "$ROOT/engine" "$ROOT/jobs" "$MODELS" "$(dirname "$EXT")"
if [[ -d "$TARGET" ]]; then rm -rf "$TARGET"; fi
ditto "$DIR/TomoTrackNano" "$TARGET"
chmod +x "$TARGET/TomoTrackNano"
xattr -dr com.apple.quarantine "$TARGET" 2>/dev/null || true
echo "[1/3] Motor local instalado."
# Los modelos originales se descargan de su propietario; NO se
# redistribuyen en nuestro repositorio ni en el ZIP.
BASE="https://raw.githubusercontent.com/HonglinChu/SiamTrackers/master/NanoTrack/models/nanotrackv2"
download_model(){
  local name="$1" expected="$2" out="$MODELS/$1" temp="$MODELS/$1.part"
  if [[ -s "$out" ]] && [[ "$(shasum -a 1 "$out" | awk '{print $1}')" == "$expected" ]]; then
    echo "Modelo verificado: $name"; return 0
  fi
  rm -f "$temp"
  curl --fail --location --retry 3 --connect-timeout 15 --max-time 180 --silent --show-error "$BASE/$name" -o "$temp"
  local actual
  actual="$(shasum -a 1 "$temp" | awk '{print $1}')"
  if [[ "$actual" != "$expected" ]]; then
     rm -f "$temp"
     echo "SHA1 de modelo inválido: $name"
     exit 1
  fi
  mv "$temp" "$out"
  echo "Modelo instalado: $name"
}
download_model "nanotrack_backbone_sim.onnx" "6e773a364457b78574f9f63a23b0659ee8646f8f"
download_model "nanotrack_head_sim.onnx" "39f168489671700cf739e402dfc67d41ce648aef"
echo "[2/3] Modelos NanoTrack V2 verificados."
# No sobrescribir el efecto nativo v0.1 que ya funciona.
if [[ ! -d "$NATIVE_DEST" ]]; then
  if [[ ! -d "$NATIVE" ]]; then echo "No encuentro el efecto ROI nativo.";exit 1;fi
  sudo mkdir -p "$(dirname "$NATIVE_DEST")"
  sudo ditto "$NATIVE" "$NATIVE_DEST"
  sudo xattr -dr com.apple.quarantine "$NATIVE_DEST" 2>/dev/null || true
  echo "Efecto ROI Select instalado."
else
  echo "Efecto ROI Select existente: preservado (no sobrescrito)."
fi
if [[ ! -d "$DIR/extension" ]]; then echo "Falta la extensión de control.";exit 1;fi
if [[ -d "$EXT" ]]; then rm -rf "$EXT"; fi
ditto "$DIR/extension" "$EXT"
defaults write com.adobe.CSXS.11 PlayerDebugMode 1
defaults write com.adobe.CSXS.12 PlayerDebugMode 1
echo "[3/3] Panel de control instalado."
echo "TERMINADO. Abrí AE 2024 > Ventana > Extensiones (heredadas) > TomoTrack AI 2 · NanoTrack."
echo "Seleccioná el video con TomoTrack ROI Select. Iniciá seguimiento desde el panel."
read -r -p "Enter para cerrar..." _
