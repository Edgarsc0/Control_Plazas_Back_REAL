# Plan de implementación: actualización en tiempo real de `PlantillaDetalleTab`

**Fecha del diagnóstico:** 2026-07-14 (revisado el mismo día, 2do escaneo)
**Servidor auditado:** `root@89.116.51.124` (solo lectura — no se modificó nada)
**Feature:** cuando un trabajador edita una celda en el tab "Detalle" de Plantilla, los demás usuarios con la tabla abierta deben ver el cambio sin recargar la página.

**Restricción vigente (actualizada):** SÍ se puede detener, cerrar o modificar `controlplazas_back.service`, `controlplazas_front.service` y el bloque nginx propio de `controlplazas` (archivo `/etc/nginx/sites-available/controlplazas`, que es exclusivo de este stack, no compartido). NO se toca nada de `declaracion`, `rendicion`, `scg`, ni sus servicios/archivos.

---

## 0. Resumen ejecutivo

Con el primer diagnóstico (sin poder tocar servicios) se recomendó parchar el SSE existente (`bitacora/sse`) por multiplexado, como workaround. **Esa restricción ya no aplica.** Con permiso para modificar `controlplazas_back`/`controlplazas_front` y su nginx propio, se puede implementar el feature de forma limpia:

- **Endpoint SSE dedicado nuevo** (no un hack sobre el endpoint de bitácora), con su propio canal de Redis y su propia autenticación por permiso.
- **Bloque nginx dedicado** para ese endpoint, dentro del archivo que ya es exclusivo de `controlplazas` — no se toca ningún archivo de los otros 3 sitios.
- **Se corrige de paso un problema real y preexistente**: `controlplazas_back` corre con gunicorn en modo síncrono puro (`--workers 9`, sin threads), y cada conexión SSE abierta (incluida la de bitácora, montada en el layout raíz para *todos* los usuarios) ocupa un worker completo mientras dura. Con solo 9 workers para servir toda la API, ~9 pestañas abiertas ya saturan el backend hoy. Como ahora se permite reiniciar el servicio, se corrige cambiando el worker class a `gthread`, sin necesidad de migrar a ASGI/Channels.
- Se mantiene **SSE en vez de WebSockets**: el feature es *push* de servidor a cliente únicamente (nadie necesita mandar datos por el socket), y SSE ya tiene un patrón probado en este mismo repo (`ZafiroSSEView`). WebSockets seguiría siendo viable ahora que se puede tocar el servicio, pero agregaría Channels + `channels-redis` + cambiar todo el stack a ASGI para un caso de uso que no necesita duplex — complejidad sin beneficio real aquí. Se documenta igual como alternativa en la sección 2.

---

## 1. Hallazgos del 2do escaneo (todo de solo lectura)

| Chequeo | Resultado |
|---|---|
| CPUs | 8 |
| RAM | 31 Gi total, 28 Gi disponible |
| `gunicorn --version` | 26.0.0 |
| Módulo `uvicorn.workers` en el venv del server | **presente** (`uvicorn==0.48.0` ya instalado) — usable si más adelante se quiere ASGI real |
| Conexiones activas a `127.0.0.1:8080` en este momento | 2 |
| Conexiones activas a `127.0.0.1:3001` en este momento | 0 |
| `/etc/systemd/system/controlplazas_back.service.d/` | no existe — no hay overrides previos, se puede crear uno limpio |
| Script de deploy que instale dependencias automáticamente | **no existe** (ni en back ni en front) — el `pip install` y `npm install` son manuales, hay que incluirlos explícitos en este plan |
| `nginx -t` | sintaxis OK (baseline sano antes de tocar nada) |
| `worker_connections` (nginx, global) | 768 por worker de nginx — de sobra |

Nada de esto cambió respecto al primer escaneo en systemd/nginx (mismo `ExecStart`, mismo `location` afinado solo para `bitacora/sse`, mismo diff sin commitear en `settings.py` del server — sigue pendiente de resolver antes de cualquier `git pull`, ver sección 6).

---

## 2. Decisión de arquitectura: SSE dedicado (no WebSockets)

| | SSE dedicado (recomendado) | WebSockets/Channels |
|---|---|---|
| Dirección de datos necesaria | Solo servidor→cliente (exactamente lo que se necesita) | Full-duplex (no se necesita para este feature) |
| Dependencias nuevas | Ninguna (reusa `redis-py`, ya está) | `channels`, `channels-redis`, cambiar `asgi.py` a `ProtocolTypeRouter` |
| Cambio al proceso que sirve Django | Ninguno (sigue WSGI, solo se ajusta worker class — ver §3) | Migrar todo `controlplazas_back` a ASGI (`gunicorn -k uvicorn.workers.UvicornWorker` o `daphne`) |
| Cambio a nginx | 1 `location` nuevo (streaming) | 1 `location` nuevo (`Upgrade`/`Connection: upgrade`) — similar costo |
| Patrón ya probado en este repo | Sí (`ZafiroSSEView`) | No |
| Reconexión automática | Nativa del navegador (`EventSource`) | Hay que programarla a mano |

Con el permiso ampliado, ambas son técnicamente posibles. Se recomienda SSE por ser la opción de menor superficie de cambio para un caso 100% unidireccional, y porque reutiliza un patrón que ya está corriendo en producción sin incidentes. Si en el futuro se necesita algo bidireccional (p. ej. "usuario X está editando esta celda ahora mismo" en vivo), ahí sí conviene reconsiderar WebSockets — no es el caso de este feature.

---

## 3. Cambio de infraestructura: worker class de `controlplazas_back`

### 3.1 El problema (ya existe hoy, no lo crea este feature)
```ini
ExecStart=.../gunicorn --access-logfile - --workers 9 --bind 127.0.0.1:8080 eje_central_back.wsgi:application
```
Gunicorn con worker class `sync` (default) asigna **un worker por conexión**, todo el tiempo que esa conexión dure. `ZafiroUpdatesProvider` (front, montado en `layout.js`) abre una conexión SSE por cada pestaña de cada usuario logueado, indefinidamente. Con 9 workers totales para *toda* la API (no solo SSE), ~9 pestañas abiertas ya dejan sin workers libres para cualquier otro request.

### 3.2 La corrección (ahora en alcance, antes no)
Cambiar el worker class a `gthread` (threads dentro de cada worker, mismo gunicorn, sin tocar el código de la app, sin migrar a ASGI):
```ini
ExecStart=/srv/controlPlazas/Control_Plazas_Back_REAL/.venv/bin/gunicorn \
  --access-logfile - --worker-class gthread --workers 4 --threads 8 \
  --bind 127.0.0.1:8080 eje_central_back.wsgi:application
```
Con 8 CPUs y 28 Gi libres, `4 workers × 8 threads = 32` conexiones concurrentes atendibles (vs. 9 hoy), y las conexiones SSE (que pasan la mayor parte del tiempo bloqueadas esperando en `pubsub.get_message(timeout=20.0)`, es decir I/O-bound, no CPU-bound) son exactamente el caso que `gthread` maneja bien sin necesitar un proceso por conexión. Esto arregla de paso el techo de capacidad de la bitácora existente, no solo el feature nuevo.

**Cómo aplicarlo sin editar el `.service` a mano** (más seguro, reversible con un solo comando):
```bash
systemctl edit controlplazas_back.service
# abre editor, se crea /etc/systemd/system/controlplazas_back.service.d/override.conf
```
```ini
[Service]
ExecStart=
ExecStart=/srv/controlPlazas/Control_Plazas_Back_REAL/.venv/bin/gunicorn --access-logfile - --worker-class gthread --workers 4 --threads 8 --bind 127.0.0.1:8080 eje_central_back.wsgi:application
```
(el `ExecStart=` vacío antes del real es obligatorio en systemd para limpiar el valor heredado del unit original, si no se concatenan). Luego:
```bash
systemctl daemon-reload
systemctl restart controlplazas_back.service
systemctl status controlplazas_back.service   # confirmar "active (running)"
```
Rollback instantáneo si algo sale mal: `rm /etc/systemd/system/controlplazas_back.service.d/override.conf && systemctl daemon-reload && systemctl restart controlplazas_back.service`.

No se toca `controlplazas_front.service` — Next.js no participa del transporte SSE (el `EventSource` del navegador habla directo con el backend en el puerto 8080 vía nginx, no pasa por el proceso de Next).

---

## 4. Cambio de infraestructura: nginx (solo el archivo de `controlplazas`)

Agregar un `location` nuevo en `/etc/nginx/sites-available/controlplazas`, mirror exacto del que ya existe para `bitacora/sse` (mismo patrón probado), apuntando a la ruta nueva del endpoint dedicado:

```nginx
# SSE de cambios en tiempo real — tab Detalle de Plantilla (no debe bufferear)
location /api/plantilla/empleados_completos_sig/celda-updates/sse/ {
    proxy_pass http://127.0.0.1:8080;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600s;
    chunked_transfer_encoding on;
}
```
Aplicar:
```bash
nginx -t                 # valida sintaxis antes de aplicar — no interrumpe nada
systemctl reload nginx   # reload, NO restart: no tumba conexiones activas de ningún sitio
```
**Nota importante:** `nginx` en sí es un proceso compartido por los 4 sitios (`controlplazas`, `declaracion`, `rendicion`, `scg`), pero el archivo que se edita es exclusivo de `controlplazas` — no se toca ni una línea de los otros 3. `reload` (a diferencia de `restart`) aplica el nuevo config de forma atómica sin cerrar conexiones existentes de ningún sitio, es la forma estándar y segura de aplicar cambios de nginx en producción. Si preferís que confirme explícitamente antes de correr `systemctl reload nginx` en el momento del deploy, avisame y lo dejo como paso manual documentado en vez de automatizarlo.

---

## 5. Cambios de código (backend)

**`requirements.txt`: sin cambios** — sigue sin hacer falta `channels` ni nada nuevo, el endpoint es una vista Django plana + `redis-py` (igual que `ZafiroSSEView`).

### 5.1 `plantilla/celda_override.py` — notificar el cambio
```python
from django.conf import settings
import json

def notificar_cambio_celda(posicion, columna, valor_nuevo, usuario, fecha_modificacion):
    import redis
    r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
    r.publish("plantilla_celda_updates", json.dumps({
        "type": "cell_update",
        "posicion": posicion,
        "columna": columna,
        "valor_nuevo": valor_nuevo,
        "usuario": usuario.username,
        "usuario_nombre": usuario.get_full_name() or usuario.username,
        "fecha_modificacion": fecha_modificacion.isoformat() if fecha_modificacion else None,
    }))
```

### 5.2 `plantilla/views.py` — `EmpleadosCompletosCeldaOverrideView`
En `.post()` (línea ~1080) y `.delete()` (línea ~1108), justo después de `self._invalidar_cache_detalle()`:
```python
notificar_cambio_celda(posicion, columna, override.valor_nuevo, request.user, override.fecha_modificacion)
```
Para `.delete()`: `valor_nuevo=None`, `fecha_modificacion=timezone.now()` (revisar si conviene que `borrar_contenido_celda` retorne el override para no improvisar la fecha ahí).

### 5.3 `plantilla/views.py` — nuevo `CeldaUpdatesSSEView`
Vista nueva, independiente de `ZafiroSSEView` (no se toca el endpoint de bitácora — cero riesgo de regresión sobre una feature que ya está en producción):
```python
class CeldaUpdatesSSEView(View):
    """
    SSE dedicado a cambios de celdas de EMPLEADOS_COMPLETOS_SIG (tab Detalle),
    para reflejar ediciones de otros usuarios en tiempo real. Requiere
    permiso view_plantilla_detalle — a diferencia de ZafiroSSEView (bitácora),
    esto sí lleva datos de personal.
    """

    def get(self, request):
        import redis
        from django.http import HttpResponseForbidden, StreamingHttpResponse
        from rest_framework.authtoken.models import Token

        token_key = request.GET.get("token")
        token = Token.objects.filter(key=token_key).select_related("user").first() if token_key else None
        user = token.user if token else None
        if not user or not user.has_perm("authentication.view_plantilla_detalle"):
            return HttpResponseForbidden("No autorizado.")

        def event_stream():
            r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
            pubsub = r.pubsub()
            pubsub.subscribe("plantilla_celda_updates")
            yield "data: init\n\n"
            try:
                while True:
                    message = pubsub.get_message(ignore_subscribe_messages=True, timeout=20.0)
                    if message:
                        yield f"data: {message['data'].decode('utf-8')}\n\n"
                    else:
                        yield ": ping\n\n"
            except GeneratorExit:
                try:
                    pubsub.unsubscribe("plantilla_celda_updates")
                    pubsub.close()
                except Exception:
                    pass

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        response["Content-Encoding"] = "identity"
        return response
```
La verificación de permiso pasa **antes** de aceptar la conexión (a diferencia del approach de multiplexado descartado, que solo podía filtrar mensajes post-conexión) — más correcto: usuarios sin permiso reciben `403` directo, la conexión SSE nunca se abre.

### 5.4 `plantilla/urls.py`
```python
path(
    "empleados_completos_sig/celda-updates/sse/",
    CeldaUpdatesSSEView.as_view(),
    name="celda_updates_sse",
),
```

---

## 6. Cambios de código (frontend)

No se toca `ZafiroUpdatesContext.jsx` en absoluto — feature completamente independiente, cero riesgo de regresión sobre la bitácora existente.

### 6.1 Nuevo contexto/hook `_hooks/useCeldaUpdatesRealtime.js`
Mismo patrón de reconexión que ya usa `ZafiroUpdatesContext.jsx` (backoff 5s→60s):
```js
export function useCeldaUpdatesRealtime(onCellUpdate) {
  const { hasPermission } = useAuth();
  useEffect(() => {
    if (!hasPermission(PERMISSIONS.VIEW_PLANTILLA_DETALLE)) return;
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const token = Cookies.get('auth_token');
    const url = `${apiBaseUrl}/api/plantilla/empleados_completos_sig/celda-updates/sse/?token=${token}`;
    let eventSource, reconnectTimer, retryDelay = 5000, active = true;

    const connect = () => {
      if (!active) return;
      eventSource = new EventSource(url);
      eventSource.onopen = () => { retryDelay = 5000; };
      eventSource.onmessage = (event) => {
        if (event.data === 'init' || event.data === 'ping' || !event.data) return;
        try {
          const parsed = JSON.parse(event.data);
          if (parsed?.type === 'cell_update') {
            onCellUpdate(parsed.posicion, parsed.columna, parsed.valor_nuevo);
          }
        } catch { /* ignorar mensajes no JSON */ }
      };
      eventSource.onerror = () => {
        eventSource?.close();
        if (!active) return;
        reconnectTimer = setTimeout(connect, retryDelay);
        retryDelay = Math.min(retryDelay * 2, 60000);
      };
    };
    connect();

    return () => {
      active = false;
      clearTimeout(reconnectTimer);
      eventSource?.close();
    };
  }, [hasPermission, onCellUpdate]);
}
```

### 6.2 `ClientComponent.jsx`
Junto a `updateDetalleCell` (línea 99):
```js
useCeldaUpdatesRealtime(updateDetalleCell);
```
Reutiliza el mismo reducer que ya usa la edición local — el trabajador B ve el cambio reflejado sin refetch.

### 6.3 (Opcional, fase 2) UX de aviso
Toast/resaltado de celda cuando `usuario` del payload ≠ usuario actual. No bloqueante para la primera entrega.

---

## 7. Plan de despliegue

1. Desarrollar y probar local (backend con `redis-server` local + `runserver`, front con `npm run dev`).
2. Resolver antes del `git pull` el diff pendiente de `eje_central_back/settings.py` en el server (reordena `DEFAULT_AUTHENTICATION_CLASSES`, sin commitear) — commitearlo si es intencional o descartarlo, para que el pull no truene.
3. **Ventana de mantenimiento corta** (server hoy tiene solo 2 conexiones activas a 8080, buen momento):
   - `git pull` en ambos repos.
   - `pip install -r requirements.txt` en el venv del back (por si acaso; en este caso no hay paquetes nuevos, pero es buena práctica dejarlo en el checklist).
   - `npm install && npm run build` en el front (por el JSX nuevo).
   - Agregar el `location` nuevo a `/etc/nginx/sites-available/controlplazas` (sección 4) → `nginx -t` → `systemctl reload nginx`.
   - Crear el override de `gthread` (sección 3.2) → `systemctl daemon-reload` → `systemctl restart controlplazas_back.service`.
   - `systemctl restart controlplazas_front.service` (para tomar el build nuevo).
4. Smoke test:
   - `systemctl status controlplazas_back controlplazas_front` → ambos `active (running)`.
   - `curl -N http://127.0.0.1:3030/api/plantilla/empleados_completos_sig/celda-updates/sse/?token=<token_valido>` → debe quedarse colgado emitiendo `data: init` y luego `: ping` cada 20s, sin cerrar.
   - Dos pestañas con el tab Detalle abierto, editar una celda en una, confirmar que la otra la refleja sin recargar.
   - Confirmar que "última actualización de ZAFIRO" sigue funcionando (no se tocó `ZafiroSSEView`, pero vale confirmar que el restart del back no rompió nada).
   - Cargar un poco el endpoint (varias pestañas) y confirmar con `ss -tnp | grep 8080 | wc -l` que ya no hay un techo de 9.

---

## 8. Nota de seguridad fuera de alcance

`DEPLOY.md` (ambos repos) tiene la contraseña root del servidor en texto plano dentro del historial de git. No es parte de este feature, pero se recomienda rotarla y sacarla del repo en algún momento.
