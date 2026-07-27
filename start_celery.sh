
# =============================================================================
# Script de arranque para Celery Worker + Beat
# Ubicación: /home/edgar/ANAM/EjeCentral/eje_central_back/
#
# Uso:
#   ./start_celery.sh          → arranca worker + beat en terminales separadas
#   ./start_celery.sh combined → arranca ambos en un solo proceso (dev/simple)
# =============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$PROJECT_DIR/venv/bin/activate"

source "$VENV"

MODE="${1:-combined}"

if [ "$MODE" = "combined" ]; then
    echo "▶ Arrancando Celery Worker + Beat (modo combinado)..."
    celery -A eje_central_back worker \
        --beat \
        --loglevel=info \
        --scheduler django_celery_beat.schedulers:DatabaseScheduler
else
    echo "▶ Arrancando Celery Worker en background..."
    celery -A eje_central_back worker \
        --loglevel=info \
        --logfile="$PROJECT_DIR/logs/celery_worker.log" \
        --pidfile="$PROJECT_DIR/logs/celery_worker.pid" \
        --detach

    echo "▶ Arrancando Celery Beat en background..."
    celery -A eje_central_back beat \
        --loglevel=info \
        --logfile="$PROJECT_DIR/logs/celery_beat.log" \
        --pidfile="$PROJECT_DIR/logs/celery_beat.pid" \
        --scheduler django_celery_beat.schedulers:DatabaseScheduler \
        --detach

    echo "✅ Celery arrancado. Logs en: $PROJECT_DIR/logs/"
fi
