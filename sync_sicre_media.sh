#!/usr/bin/env bash
# Sincroniza fotografías (y firmas, cuando se habilite) de empleados desde
# SICRE/Credencialización hacia este proyecto, vía rsync sobre SSH con una
# llave dedicada de solo lectura (rrsync -ro del lado de SICRE). Pensado para
# correr por cron cada 15-30 min — no es tiempo real.
#
# --delete dejo el destino en espejo del origen: si en SICRE se borra una
# foto, aquí también se borra. Es intencional (ver conversación de diseño).
set -uo pipefail

SSH_KEY="$HOME/.ssh/mediasync_sicre"
REMOTE_USER_HOST="mediasync@168.231.73.222"
BASE_DIR="/srv/controlPlazas/Control_Plazas_Back_REAL"
LOG_FILE="$BASE_DIR/logs/sicre_media_sync.log"
LOCK_FILE="/tmp/sicre_media_sync.lock"

FOTOS_DEST="$BASE_DIR/media/empleados_fotos/"
# FIRMAS_DEST="$BASE_DIR/media/empleados_firmas/"

RSYNC_OPTS=(-az --delete --timeout=120)
SSH_OPTS=(-e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new -o BatchMode=yes -o ConnectTimeout=15 -p 22")

log() {
    printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S%z')" "$1" >> "$LOG_FILE"
}

# Evita sync solapados si una corrida anterior sigue viva (conexión lenta,
# servidor de SICRE tardado, etc.) — flock libera solo si el proceso termina.
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    log "SKIP: ya hay una sincronización en curso (lock tomado). Se aborta esta corrida."
    exit 0
fi

mkdir -p "$BASE_DIR/logs" "$FOTOS_DEST"

log "INICIO sync fotos SICRE -> $FOTOS_DEST"
if rsync "${RSYNC_OPTS[@]}" "${SSH_OPTS[@]}" "${REMOTE_USER_HOST}:fotos/" "$FOTOS_DEST" >> "$LOG_FILE" 2>&1; then
    log "OK fotos: sincronización completada sin errores."
else
    status=$?
    log "ERROR fotos: rsync terminó con código $status. Revisar conexión/llave/servidor SICRE."
fi

# --- Firmas: deshabilitado hasta confirmar la ruta remota y crear el destino ---
# Descomentar cuando se confirme el path remoto de firmas (probar antes con
# `rsync -av --list-only -e "ssh -i ~/.ssh/mediasync_sicre" mediasync@168.231.73.222:FIRMAS/`)
# y crear FIRMAS_DEST arriba.
#
# log "INICIO sync firmas SICRE -> $FIRMAS_DEST"
# mkdir -p "$FIRMAS_DEST"
# if rsync "${RSYNC_OPTS[@]}" "${SSH_OPTS[@]}" "${REMOTE_USER_HOST}:FIRMAS/" "$FIRMAS_DEST" >> "$LOG_FILE" 2>&1; then
#     log "OK firmas: sincronización completada sin errores."
# else
#     status=$?
#     log "ERROR firmas: rsync terminó con código $status."
# fi

log "FIN sync SICRE"
