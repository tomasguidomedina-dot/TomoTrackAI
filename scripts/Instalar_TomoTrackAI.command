#!/bin/bash
set -euo pipefail
trap 'code=$?; if [[ $code -ne 0 ]]; then echo "";echo "Instalación detenida (error $code). Revisá el mensaje anterior.";read -r -p "Enter para cerrar..." _ || true; fi' EXIT
ROOT="$(cd "$(dirname "$0")" && pwd)"
HOME3="$HOME/Library/Application Support/TomoTrackAI3"
EXT="$HOME/Library/Application Support/Adobe/CEP/extensions/com.tomo.trackai3"
MODELS="$HOME3/models"
ENGINE="$HOME3/engine/TomoTrackNano"
MODELS_URL="https://raw.githubusercontent.com/HonglinChu/SiamTrackers/master/NanoTrack/models/nanotrackv2"

echo ""
echo "=================================================="
echo " TOMOTRACKAI v0.3.1 · PLUGIN ÚNICO / MÁSCARAS AE"
echo "=================================================="
echo "Sin efecto ROI Select ni otros plugins separados."
if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "x86_64" ]];then
  echo "Solo compatible con Mac Intel.";exit 1
fi
if [[ ! -x "$ROOT/TomoTrackNano/TomoTrackNano" ]];then
  echo "El ejecutable NanoTrack no está en el paquete.";exit 1
fi
if [[ ! -f "$ROOT/extension/CSXS/manifest.xml" ]];then
  echo "No se encontró la extensión única TomoTrackAI.";exit 1
fi

mkdir -p "$HOME3/engine" "$HOME3/jobs" "$MODELS" "$(dirname "$EXT")"
if [[ -e "$ENGINE" ]];then rm -rf "$ENGINE";fi
ditto "$ROOT/TomoTrackNano" "$ENGINE"
chmod +x "$ENGINE/TomoTrackNano"
xattr -dr com.apple.quarantine "$ENGINE" 2>/dev/null || true
echo "[1/4] Motor local instalado."

download_model(){
  local name="$1" expected="$2" out="$MODELS/$1" tmp="$MODELS/$1.part" digest
  if [[ -s "$out" ]];then
     digest="$(shasum -a 1 "$out" | awk '{print $1}')"
     if [[ "$digest" == "$expected" ]];then
        echo "  Reutilizado: $name";return 0
     fi
  fi
  # Si hay modelos ya verificados de v0.2, reutilizarlos sin nueva descarga.
  local previous
  previous="$HOME/Library/Application Support/TomoTrackAI2/models/$name"
  if [[ -s "$previous" ]];then
     digest="$(shasum -a 1 "$previous" | awk '{print $1}')"
     if [[ "$digest" == "$expected" ]];then
       cp "$previous" "$out"
       echo "  Reutilizado modelo v0.2: $name"
       return 0
     fi
  fi
  rm -f "$tmp"
  curl --fail --location --retry 3 --connect-timeout 20 --max-time 180 \
       --silent --show-error "$MODELS_URL/$name" -o "$tmp"
  digest="$(shasum -a 1 "$tmp" | awk '{print $1}')"
  if [[ "$digest" != "$expected" ]];then
     rm -f "$tmp";echo "Checksum incorrecto: $name";exit 1
  fi
  mv "$tmp" "$out"
  echo "  Verificado: $name"
}
download_model "nanotrack_backbone_sim.onnx" "6e773a364457b78574f9f63a23b0659ee8646f8f"
download_model "nanotrack_head_sim.onnx" "39f168489671700cf739e402dfc67d41ce648aef"
echo "[2/4] Modelos NanoTrack verificados."

# Una única extensión con una única entrada en Ventana.
if [[ -d "$EXT" ]];then rm -rf "$EXT";fi
ditto "$ROOT/extension" "$EXT"
defaults write com.adobe.CSXS.11 PlayerDebugMode 1
defaults write com.adobe.CSXS.12 PlayerDebugMode 1
echo "[3/4] TomoTrackAI instalado como una única extensión."

echo ""
echo "LIMPIEZA DE VERSIONES ANTERIORES"
echo "Antes de borrar copias viejas, se guardará una copia de seguridad."
echo "AVISO: los proyectos que utilizaron el viejo efecto ROI Select"
echo "pueden mostrar efecto faltante después de quitarlo."
read -r -p "¿Archivar y quitar entradas antiguas de TomoTrackAI? [s/N]: " answer || answer="N"
if [[ "$answer" =~ ^[sS]$ ]];then
  BACKUP="$HOME3/respaldos/$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$BACKUP"
  remove_known(){
    local src="$1" name="$2"
    if [[ ! -e "$src" ]];then return;fi
    echo "  Archivar: $src"
    if [[ -w "$(dirname "$src")" ]];then
       ditto "$src" "$BACKUP/$name"
       rm -rf "$src"
    else
       sudo ditto "$src" "$BACKUP/$name"
       sudo rm -rf "$src"
    fi
  }
  USER_CEP="$HOME/Library/Application Support/Adobe/CEP/extensions"
  SYS_CEP="/Library/Application Support/Adobe/CEP/extensions"
  MEDIA="/Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore"
  remove_known "$USER_CEP/com.tomo.trackai" "panel-antiguo"
  remove_known "$USER_CEP/com.tomo.trackai2" "panel-v02"
  remove_known "$USER_CEP/com.tomo.trackai.nativebridge" "panel-nativebridge"
  remove_known "$SYS_CEP/com.tomo.trackai" "panel-sistema-antiguo"
  remove_known "$SYS_CEP/com.tomo.trackai2" "panel-sistema-v02"
  remove_known "$SYS_CEP/com.tomo.trackai.nativebridge" "panel-sistema-nativebridge"
  remove_known "$MEDIA/TomoTrack_Native_Check.plugin" "nativo-diagnostico"
  remove_known "$MEDIA/TomoTrack_ROI_Select.plugin" "nativo-roi"
  remove_known "$MEDIA/TomoTrackAINative.plugin" "nativo-experimental"
  remove_known "$HOME/Library/Application Support/Adobe/Plug-ins/TomoTrackAINative.plugin" "nativo-usuario"
  remove_known "/Applications/Adobe After Effects 2024/Plug-ins/TomoTrackAINative.plugin" "nativo-app"
  remove_known "/Applications/Adobe After Effects 2024/Plug-ins/Effects/TomoTrackAINative.plugin" "nativo-app-efectos"
  echo "  Versiones anteriores respaldadas en: $BACKUP"
else
  echo "  Sin cambios en las instalaciones antiguas."
  echo "  Para ver SOLO TomoTrackAI en la lista, ejecutá de nuevo"
  echo "  el instalador y aceptá la limpieza."
fi
echo "[4/4] Operación completada."
echo ""
echo "Cerrá y reabrí After Effects 2024."
echo "Ventana > Extensiones (heredadas) > TomoTrackAI."
echo "Seleccioná una capa de video, dibujá una máscara con la Pluma (G)"
echo "y pulsá Iniciar. Se mostrará el seguimiento fotograma a fotograma."
read -r -p "Enter para cerrar..." _
