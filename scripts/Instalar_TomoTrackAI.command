#!/bin/bash
# v0.6.2 cámara estabilizada. Instala A LA PAR de la v0.5 funcional.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
BASE="$HOME/Library/Application Support/TomoTrackAI62"
CEP="$HOME/Library/Application Support/Adobe/CEP/extensions"
MOTOR="$BASE/engine/TomoPlateTrack"
PANEL="$CEP/com.tomo.trackai62"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACK="$BASE/respaldos/pre-v0.6.2-$STAMP"
STAGE=""
on_exit() {
  status=$?
  if [[ -n "$STAGE" && -d "$STAGE" ]];then rm -rf "$STAGE";fi
  if [[ "$status" -ne 0 ]];then
    echo "La instalación v0.6.2 se detuvo. v0.5 permanece intacta."
    read -r -p "Enter para cerrar..." _ || true
  fi
}
trap on_exit EXIT
echo "TomoTrackAI v0.6.2 — PlateTrack + estabilizador local Intel"
echo "Se instalará una extensión separada; NO se reemplazará tu v0.5 ni tu v0.6.1."
if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "x86_64" ]];then
 echo "Solo macOS Intel"; exit 1
fi
if pgrep -x "After Effects" >/dev/null 2>&1 || pgrep -x "After Effects 2024" >/dev/null 2>&1;then
 echo "Cerrá After Effects con Cmd+Q antes de instalar."; exit 1
fi
if [[ ! -x "$ROOT/TomoPlateTrack/TomoPlateTrack" || ! -f "$ROOT/extension/CSXS/manifest.xml" ]];then
 echo "Este .command debe estar en la carpeta principal junto a TomoPlateTrack/ y extension/."
 exit 1
fi
if ! grep -q 'com.tomo.trackai62' "$ROOT/extension/CSXS/manifest.xml";then
 echo "El paquete no contiene el panel v0.6.2 correcto.";exit 1
fi
mkdir -p "$BASE/staging" "$BASE/engine" "$CEP" "$BACK"
STAGE="$(mktemp -d "$BASE/staging/preflight-XXXXXXXX")"
ditto "$ROOT/TomoPlateTrack" "$STAGE/TomoPlateTrack"
chmod +x "$STAGE/TomoPlateTrack/TomoPlateTrack"
xattr -dr com.apple.quarantine "$STAGE/TomoPlateTrack" 2>/dev/null || true
echo "Comprobando arranque REAL v0.6.2, offline (hasta 75 segundos)..."
printf '{"cmd":"close"}\n' > "$STAGE/input"
"$STAGE/TomoPlateTrack/TomoPlateTrack" < "$STAGE/input" > "$STAGE/stdout" 2> "$STAGE/stderr" &
PID=$!
OK=0
for ((i=1;i<=300;i++));do
 if grep -q '"ready":true' "$STAGE/stdout" && grep -q '"PlateTrack"' "$STAGE/stdout";then OK=1;break;fi
 if ! kill -0 "$PID" 2>/dev/null;then break;fi
 sleep .25
done
if [[ "$OK" -ne 1 ]];then
 kill "$PID" 2>/dev/null || true
 sleep .2
 kill -9 "$PID" 2>/dev/null || true
 wait "$PID" 2>/dev/null || true
 echo "Motor no respondió: no se instaló v0.6.2."
 head -c 800 "$STAGE/stderr" || true
 exit 1
fi
wait "$PID" 2>/dev/null || true
echo "Motor validado. Instalando versión separada v0.6.2..."
if [[ -d "$MOTOR" ]];then
 ditto "$MOTOR" "$BACK/TomoPlateTrack-anterior"
 rm -rf "$MOTOR"
fi
ditto "$STAGE/TomoPlateTrack" "$MOTOR"
chmod +x "$MOTOR/TomoPlateTrack"
if [[ -d "$PANEL" ]];then
 ditto "$PANEL" "$BACK/panel-anterior"
 rm -rf "$PANEL"
fi
ditto "$ROOT/extension" "$PANEL"
xattr -dr com.apple.quarantine "$PANEL" 2>/dev/null || true
defaults write com.adobe.CSXS.11 PlayerDebugMode 1
defaults write com.adobe.CSXS.12 PlayerDebugMode 1
echo ""
echo "Listo. AE 2024 > Ventana > Extensiones (heredadas) > TomoTrackAI · Pins v0.6.2"
echo "v0.5 (com.tomo.trackai50) y v0.6.1 (com.tomo.trackai60) siguen intactas."
echo "Antes de usarlo duplicá tu proyecto AE. Es candidato experimental."
read -r -p "Enter para salir..." _ || true
