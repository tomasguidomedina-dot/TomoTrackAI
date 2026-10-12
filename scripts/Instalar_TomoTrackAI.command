#!/bin/bash
# TomoTrackAI 0.4.1 — instalador verificado, offline y con rollback.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/Library/Application Support/TomoTrackAI3"
CEP="$HOME/Library/Application Support/Adobe/CEP/extensions"
MOTOR="$APP/engine/TomoTrackNano"
MODELS="$APP/models"
DEST="$CEP/com.tomo.trackai41"
BACKUP="$APP/respaldos/pre-v0.4.1-$(date +%Y%m%d-%H%M%S)"
STAGE=""
cleanup() {
  code=$?
  if [[ -n "$STAGE" && -d "$STAGE" ]]; then rm -rf "$STAGE"; fi
  if [[ $code -ne 0 ]]; then
    echo ""
    echo "INSTALACIÓN CANCELADA (código $code)."
    echo "No se reemplazó el motor anterior salvo que ya hubiera pasado la prueba."
    read -r -p "Enter para salir..." _ || true
  fi
}
trap cleanup EXIT

echo "TomoTrackAI v0.4.1 · SEGUIMIENTO P/S/R · COMPATIBLE MAC INTEL"
echo "Instalación y verificación 100 % offline; no se descargan modelos."
[[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "x86_64" ]] || {
  echo "Este instalador solo se diseñó para Mac Intel.";exit 1;
}
[[ -x "$ROOT/TomoTrackNano/TomoTrackNano" ]] || {
  echo "No hay motor Intel en el ZIP.";exit 1;
}
[[ -f "$ROOT/extension/CSXS/manifest.xml" ]] || {
  echo "No hay extensión AE en el ZIP.";exit 1;
}

# El paquete NO accede a Internet. Es obligatorio reutilizar modelos locales.
check_model() {
  local model="$1" sha="$2" file="$MODELS/$model" current=""
  [[ -s "$file" ]] || { echo "Falta modelo ONNX local: $model";exit 1; }
  current="$(shasum -a 1 "$file" | awk '{print $1}')"
  [[ "$current" == "$sha" ]] || { echo "Modelo corrupto o diferente: $model";exit 1; }
  echo "Modelo local verificado: $model"
}
check_model nanotrack_backbone_sim.onnx 6e773a364457b78574f9f63a23b0659ee8646f8f
check_model nanotrack_head_sim.onnx 39f168489671700cf739e402dfc67d41ce648aef

# Evitar sobrescribir binarios que están en uso.
if pgrep -fl 'After Effects' >/dev/null 2>&1; then
  echo "Cerrá COMPLETAMENTE After Effects (Cmd+Q) y ejecutá el instalador de nuevo."
  exit 1
fi
mkdir -p "$APP/staging" "$APP/engine" "$CEP" "$BACKUP"
STAGE="$(mktemp -d "$APP/staging/TomoTrack41-XXXXXX")"
ditto "$ROOT/TomoTrackNano" "$STAGE/TomoTrackNano"
chmod +x "$STAGE/TomoTrackNano/TomoTrackNano"
xattr -dr com.apple.quarantine "$STAGE/TomoTrackNano" 2>/dev/null || true

echo ""
echo "Verificando arranque LOCAL del motor nuevo ANTES de instalar (límite: 18 s)..."
printf '{"cmd":"close"}\n' > "$STAGE/probe.in"
"$STAGE/TomoTrackNano/TomoTrackNano" < "$STAGE/probe.in" > "$STAGE/probe.out" 2> "$STAGE/probe.err" &
PID=$!
READY=0
for ((i=1;i<=72;i++)); do
  if grep -q '"ready":true' "$STAGE/probe.out" 2>/dev/null; then READY=1;break;fi
  if ! kill -0 "$PID" 2>/dev/null; then break; fi
  sleep 0.25
done
if [[ "$READY" -ne 1 ]]; then
  kill "$PID" 2>/dev/null || true
  sleep 0.5
  kill -9 "$PID" 2>/dev/null || true
  wait "$PID" 2>/dev/null || true
  echo "El motor v0.4.1 NO pasó la comprobación de arranque."
  echo "No se reemplazará el motor ni el panel actual."
  echo "Diagnóstico: $(head -c 400 "$STAGE/probe.err")"
  exit 1
fi
wait "$PID" 2>/dev/null || true
echo "Motor nuevo respondió correctamente en la prueba previa."

# Recién ahora modificamos la instalación activa y guardamos un respaldo.
if [[ -d "$MOTOR" ]]; then
  mv "$MOTOR" "$BACKUP/TomoTrackNano"
  echo "Motor previo archivado en: $BACKUP/TomoTrackNano"
fi
mv "$STAGE/TomoTrackNano" "$MOTOR"
if [[ ! -x "$MOTOR/TomoTrackNano" ]]; then
  echo "No se pudo instalar el motor nuevo. Revirtiendo..."
  rm -rf "$MOTOR"
  [[ ! -d "$BACKUP/TomoTrackNano" ]] || mv "$BACKUP/TomoTrackNano" "$MOTOR"
  exit 1
fi

# Única entrada CEP visible. Los paneles antiguos se archivan.
for old in com.tomo.trackai3 com.tomo.trackai32 com.tomo.trackai40 com.tomo.trackai41; do
  if [[ -d "$CEP/$old" ]]; then
    ditto "$CEP/$old" "$BACKUP/$old"
    rm -rf "$CEP/$old"
  fi
done
ditto "$ROOT/extension" "$DEST"
xattr -dr com.apple.quarantine "$DEST" 2>/dev/null || true
defaults write com.adobe.CSXS.11 PlayerDebugMode 1
defaults write com.adobe.CSXS.12 PlayerDebugMode 1
echo ""
echo "INSTALACIÓN CORRECTA · v0.4.1"
echo "Única entrada: AE 2024 > Ventana > Extensiones (heredadas) > TomoTrackAI"
echo "Guardamos respaldos en: $BACKUP"
echo "Nunca se envió metraje a Internet."
echo "El nuevo motor no sustituye tu rama estable en GitHub."
read -r -p "Enter para terminar..." _
