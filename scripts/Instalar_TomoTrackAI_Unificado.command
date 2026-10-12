#!/bin/bash
# Una extensión: TomoTrackAI. Renombra versiones viejas con BACKUP, no las borra.
# Sólo el motor canónico se instala bajo TomoTrackAI/engine/TomoPlateTrack.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
CEP="$HOME/Library/Application Support/Adobe/CEP/extensions"
APP="$HOME/Library/Application Support/TomoTrackAI"
PANEL="$CEP/com.tomo.trackai"
ENGINE="$APP/engine/TomoPlateTrack"
BACKUP_ROOT="$APP/respaldos-extensiones"
STAMP="$(date '+%Y%m%d_%H%M%S')"
BACKUP="$BACKUP_ROOT/unificacion_$STAMP"
STAGE=""
MOVED=0
on_failure() {
  status=$?
  if [[ "$status" -ne 0 && "$MOVED" -eq 1 ]];then
    echo "Falló la instalación. Se intenta restaurar la instalación anterior..."
    [[ -d "$PANEL" ]] && mv "$PANEL" "$BACKUP/unificado-nuevo-fallido" || true
    [[ -d "$ENGINE" ]] && mv "$ENGINE" "$BACKUP/motor-nuevo-fallido" || true
    [[ -d "$BACKUP/unificado-anterior" ]] && mv "$BACKUP/unificado-anterior" "$PANEL" || true
    [[ -d "$BACKUP/motor-anterior" ]] && mv "$BACKUP/motor-anterior" "$ENGINE" || true
    for prior in "$BACKUP"/anteriores/com.tomo.trackai[0-9]*;do
       [[ -d "$prior" ]] || continue
       mv "$prior" "$CEP/$(basename "$prior")" || true
    done
  fi
  [[ -n "$STAGE" && -d "$STAGE" ]] && rm -rf "$STAGE" || true
  if [[ "$status" -ne 0 ]];then
    echo "Se canceló la unificación. No se han borrado proyectos de After Effects."
    read -r -p "Enter para salir..." _ || true
  fi
}
trap on_failure EXIT
echo "TomoTrackAI v0.6.3 — INSTALADOR UNIFICADO"
echo "Un panel: Tracking + Estabilización + cuatro puntos de corrección."
echo "Las extensiones anteriores se archivan; los motores antiguos se conservan."
if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "x86_64" ]];then
  echo "Este ZIP requiere macOS Intel.";exit 1
fi
if pgrep -f '/After Effects( 2024)?\.app/Contents/MacOS/After Effects' >/dev/null 2>&1 ||
   pgrep -x "After Effects" >/dev/null 2>&1 ||
   pgrep -x "After Effects 2024" >/dev/null 2>&1;then
  echo "Cerrá completamente After Effects con Cmd+Q y ejecutá nuevamente.";exit 1
fi
if [[ ! -x "$ROOT/TomoPlateTrack/TomoPlateTrack" ||
      ! -f "$ROOT/extension/CSXS/manifest.xml" ||
      ! -f "$ROOT/extension/jsx/host.jsx" ||
      ! -f "$ROOT/extension/panel.js" ]];then
  echo "Descomprimí TODO el ZIP antes de ejecutar el .command.";exit 1
fi
if ! grep -q 'ExtensionBundleId="com.tomo.trackai"' "$ROOT/extension/CSXS/manifest.xml" ||
   ! grep -q 'platetrack-0.6.3-bridge-20261012' "$ROOT/extension/panel.js" ||
   ! grep -q 'platetrack-0.6.3-bridge-20261012' "$ROOT/extension/jsx/host.jsx";then
  echo "Paquete incompatible: el panel y bridge no corresponden a la v0.6.3.";exit 1
fi
mkdir -p "$CEP" "$APP/engine" "$APP/staging" "$BACKUP_ROOT"
STAGE="$(mktemp -d "$APP/staging/validar-XXXXXXXX")"
ditto "$ROOT/TomoPlateTrack" "$STAGE/TomoPlateTrack"
ditto "$ROOT/extension" "$STAGE/extension"
chmod +x "$STAGE/TomoPlateTrack/TomoPlateTrack"
xattr -dr com.apple.quarantine "$STAGE/TomoPlateTrack" 2>/dev/null || true
printf '{"cmd":"close"}\n' > "$STAGE/input"
echo "Validando motor Mac Intel offline (hasta 75 s)..."
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
  wait "$PID" 2>/dev/null || true
  echo "El motor no completó el inicio. No se tocaron extensiones anteriores."
  head -c 500 "$STAGE/stderr" || true;exit 1
fi
wait "$PID" 2>/dev/null || true
mkdir -p "$BACKUP/anteriores"
MOVED=1
# La v0.5 estable y las 0.6.1 / 0.6.2 pasan a respaldo, no se pierden.
for prior in "$CEP"/com.tomo.trackai[0-9]*;do
  [[ -d "$prior" && -f "$prior/CSXS/manifest.xml" ]] || continue
  if grep -q 'com.tomo.trackai' "$prior/CSXS/manifest.xml" &&
     grep -q 'TomoTrackAI' "$prior/CSXS/manifest.xml";then
    echo "Archivando panel previo: $(basename "$prior")"
    mv "$prior" "$BACKUP/anteriores/$(basename "$prior")"
  fi
done
if [[ -d "$PANEL" ]];then mv "$PANEL" "$BACKUP/unificado-anterior";fi
if [[ -d "$ENGINE" ]];then mv "$ENGINE" "$BACKUP/motor-anterior";fi
mv "$STAGE/TomoPlateTrack" "$ENGINE"
mv "$STAGE/extension" "$PANEL"
chmod +x "$ENGINE/TomoPlateTrack"
xattr -dr com.apple.quarantine "$PANEL" 2>/dev/null || true
defaults write com.adobe.CSXS.11 PlayerDebugMode 1
defaults write com.adobe.CSXS.12 PlayerDebugMode 1
# Don't remove separate data/engines: projects and old versions remain recoverable.
echo ""
echo "LISTO: UNA SOLA EXTENSIÓN, TomoTrackAI."
echo "Menú: AE > Ventana > Extensiones (heredadas) > TomoTrackAI"
echo "Respaldo de paneles anteriores: $BACKUP"
if [[ -d "/Library/Application Support/Adobe/CEP/extensions" ]];then
  for old in "/Library/Application Support/Adobe/CEP/extensions"/com.tomo.trackai[0-9]*;do
    [[ -d "$old" ]] || continue
    echo "AVISO: detecté también una extensión antigua instalada para todos los usuarios: $old"
    echo "No la modifiqué porque puede requerir permisos de administrador."
  done
fi
echo "Primera prueba: usá una copia del proyecto; la herramienta de 4 puntos todavía debe validarse en AE real."
read -r -p "Enter para salir..." _ || true
