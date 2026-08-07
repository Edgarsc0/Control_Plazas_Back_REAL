"""
Notificaciones por correo de "Posición quedó vacante" / "Posición se ocupó".

Disparadas desde `procesar_suscripciones_posicion()`, enganchada en dos
puntos (ver docstrings en tasks.py/views.py de por qué son dos y no uno):

  1. `plantilla.tasks._invalidar_cache_ocupacion_vacancia` (import corre en
     este mismo servidor).
  2. `plantilla.views.InvalidarCacheZafiroView.post` (import corrió en la PC
     Windows remota y notificó a este servidor).

Flujo por corrida:
  - Se leen todas las `SuscripcionNotificacionPosicion` activas.
  - Se resuelve el estado actual (ocupada/vacante) de cada posición vía
    `get_posiciones_ocupadas_set()` (misma fuente de verdad que ya usa el
    resto del sistema, ver `plantilla/views.py`).
  - Si el estado actual difiere del snapshot tomado al suscribirse
    (`estado_conocido_al_suscribir`) Y coincide con lo que esa suscripción
    quiere avisar, se manda el correo y la suscripción se desactiva (un
    solo aviso, ver PLAN_NOTIFICACIONES_POSICION_2026-08-06.md §3).
"""

import logging
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Categoría de vacancia — mismos textos que CATEGORIA_VACANCIA_TOOLTIP /
# VACANCIA_CATEGORIA_STYLE en VacanciaDetalleModal.jsx (única fuente de
# verdad del lado frontend; se duplica aquí porque el correo se renderiza
# en el backend, sin acceso al bundle de React).
# ---------------------------------------------------------------------------
CATEGORIA_VACANCIA_LABEL = {
    "A": "Baja de Personal",
    "B": "Cambio de Posición",
    "C": "Nunca Ocupada",
}
CATEGORIA_VACANCIA_DESCRIPCION = {
    "A": "Posición vacante porque el empleado que la ocupaba causó baja.",
    "B": "Posición vacante porque el empleado que la ocupaba cambió a otra posición; la vacancia es la fecha en que tomó esa nueva posición.",
    "C": "Posición vacante porque jamás tuvo ocupante; la vacancia es la fecha de creación de la posición.",
}

EMAIL_ASSETS_DIR = None  # se resuelve perezosamente en _enviar_email_html


def _iniciales(nombre_completo):
    if not nombre_completo:
        return None
    partes = [p for p in str(nombre_completo).split() if p]
    return "".join(p[0] for p in partes[:2]).upper() or None


def _parse_fecha_charfield(valor):
    """Las fechas de EMPLEADOS_COMPLETOS_SIG son CharField pero, verificado
    contra datos reales, ya vienen en formato 'YYYY-MM-DD' — se parsean para
    poder compararlas contra los DateField de cp_tbl_mov_completo_29_05_26.
    Cualquier formato inesperado devuelve None (el filtro simplemente no
    matchea esa fila, no truena)."""
    if not valor:
        return None
    try:
        return datetime.strptime(str(valor).strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _enviar_email_html(subject, template_name, context, to_email):
    """Mismo patrón que authentication/views.py (OTP): HTML + texto plano +
    logo/ícono embebidos por Content-ID. `fail_silently=False` a propósito
    — el error se atrapa en el caller (`procesar_suscripciones_posicion`),
    que decide si reintentar en la siguiente corrida de Celery."""
    import os
    from email.mime.image import MIMEImage

    if not to_email:
        raise ValueError("El usuario no tiene email configurado; no se puede notificar.")

    html_message = render_to_string(template_name, context)
    plain_message = strip_tags(html_message)
    from_email = settings.EMAIL_HOST_USER

    msg = EmailMultiAlternatives(subject, plain_message, from_email, [to_email])
    msg.attach_alternative(html_message, "text/html")

    assets_dir = os.path.join(os.path.dirname(__file__), "templates", "emails", "assets")
    inline_images = {
        "anam_logo": "anam_logo.png",
        "icon_control_plazas": "icon_control_plazas.png",
    }
    for content_id, filename in inline_images.items():
        path = os.path.join(assets_dir, filename)
        if not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            image = MIMEImage(f.read())
        image.add_header("Content-ID", f"<{content_id}>")
        image.add_header("Content-Disposition", "inline", filename=filename)
        msg.attach(image)

    msg.send(fail_silently=False)


# ---------------------------------------------------------------------------
# Detalle de vacancia (extraído de MovPosVacanciaDetalleView, ver refactor
# en views.py — misma lógica exacta, ahora reutilizable por el correo)
# ---------------------------------------------------------------------------

def construir_detalle_vacancia(mov_row):
    """
    Dado un renglón de MOV_POS (el más reciente de una posición), arma el
    detalle dinámico (por categoría A/B/C) del registro decisivo que originó
    su fecha de vacancia. Devuelve un dict con la MISMA forma que ya
    consumía el endpoint `MovPosVacanciaDetalleView` (no se le cambió el
    contrato), reutilizado también por `enviar_correo_vacancia`.
    """
    from .models import CpTblMovCompleto290526, MovPos

    categoria = (mov_row.categoria_vacancia or "").strip().upper()
    id_decisivo = mov_row.id_registro_desicivo

    tuvo_insubsistencia = (mov_row.tuvo_insubsistencia or "").strip().upper()
    insubsistencia = None
    if tuvo_insubsistencia == "S" and mov_row.id_insubsistencia_detectada:
        try:
            reg_ins = CpTblMovCompleto290526.objects.get(id=mov_row.id_insubsistencia_detectada)
            insubsistencia = {
                "empleado": {
                    "num_empleado": reg_ins.num_empleado,
                    "nombre_completo": " ".join(
                        p for p in [reg_ins.nombre, reg_ins.ap_pat, reg_ins.ap_mat] if p
                    ).strip(),
                },
                "posicion": reg_ins.posicion,
                "motivo": reg_ins.motivo,
                "motivo_nombre": reg_ins.motivo_nombre,
                "accion": reg_ins.accion,
                "accion_nombre": reg_ins.accion_nombre,
                "fecha_efectiva": reg_ins.fecha_efectiva,
                "fecha_captura": reg_ins.fecha_captura,
            }
        except CpTblMovCompleto290526.DoesNotExist:
            insubsistencia = {
                "error": "Registro de insubsistencia no encontrado en cp_tbl_mov_completo_29_05_26."
            }

    base = {
        "categoria_vacancia": categoria,
        "no_pos_actual": mov_row.no_pos_actual,
        "fecha_vacancia": mov_row.fecha_vacancia,
        "tuvo_insubsistencia": tuvo_insubsistencia,
        "insubsistencia": insubsistencia,
    }

    if not categoria or not id_decisivo:
        return {**base, "error": "No hay registro decisivo asociado a esta vacancia."}

    if categoria in ("A", "B"):
        try:
            registro = CpTblMovCompleto290526.objects.get(id=id_decisivo)
        except CpTblMovCompleto290526.DoesNotExist:
            return {
                **base,
                "error": "Registro decisivo no encontrado en cp_tbl_mov_completo_29_05_26.",
            }

        empleado_nombre = " ".join(
            p for p in [registro.nombre, registro.ap_pat, registro.ap_mat] if p
        ).strip()

        detalle = {
            **base,
            "empleado": {
                "num_empleado": registro.num_empleado,
                "nombre_completo": empleado_nombre,
            },
            "accion": registro.accion,
            "accion_nombre": registro.accion_nombre,
            "motivo": registro.motivo,
            "motivo_nombre": registro.motivo_nombre,
            "fecha_efectiva": registro.fecha_efectiva,
            "fecha_captura": registro.fecha_captura,
        }

        if categoria == "B":
            detalle["posicion_origen"] = mov_row.no_pos_actual
            detalle["posicion_destino"] = registro.posicion

        return detalle

    if categoria == "C":
        try:
            registro = MovPos.objects.get(id=id_decisivo)
        except MovPos.DoesNotExist:
            return {**base, "error": "Registro decisivo no encontrado en MOV_POS."}

        return {
            **base,
            "fecha_efectiva": registro.f_efva,
            "fecha_captura": registro.fecha_captura,
        }

    return {**base, "error": f"Categoría de vacancia desconocida: {categoria}"}


# ---------------------------------------------------------------------------
# Correo de VACANCIA
# ---------------------------------------------------------------------------

def enviar_correo_vacancia(sub):
    """Manda el correo de "la posición quedó vacante" para la suscripción
    `sub` (SuscripcionNotificacionPosicion, tipo VACANTE). Devuelve True si
    se envió; deja propagar la excepción si algo falla (el caller decide
    reintentar)."""
    from .models import MovPos, MovPosLatest

    latest = MovPosLatest.objects.get(no_pos_actual=sub.posicion)
    mov_row = MovPos.objects.get(id=latest.mov_pos_id)

    detalle = construir_detalle_vacancia(mov_row)
    categoria = detalle.get("categoria_vacancia") or "C"
    empleado = detalle.get("empleado") or {}

    context = {
        "no_pos_actual": mov_row.no_pos_actual,
        "fecha_vacancia": detalle.get("fecha_vacancia"),
        "categoria_vacancia": categoria,
        "categoria_label": CATEGORIA_VACANCIA_LABEL.get(categoria, "Vacancia"),
        "categoria_descripcion": CATEGORIA_VACANCIA_DESCRIPCION.get(
            categoria, detalle.get("error") or ""
        ),
        "empleado_nombre": empleado.get("nombre_completo"),
        "empleado_num": empleado.get("num_empleado"),
        "empleado_iniciales": _iniciales(empleado.get("nombre_completo")),
        "empleado_rol_label": "Empleado Saliente (Baja)" if categoria == "A" else "Empleado Trasladado",
        "accion": detalle.get("accion"),
        "accion_nombre": detalle.get("accion_nombre"),
        "motivo": detalle.get("motivo"),
        "motivo_nombre": detalle.get("motivo_nombre"),
        "fecha_efectiva": detalle.get("fecha_efectiva"),
        "fecha_captura": detalle.get("fecha_captura"),
        "por": mov_row.por,
        "posicion_destino": detalle.get("posicion_destino"),
        "tuvo_insubsistencia": detalle.get("tuvo_insubsistencia") == "S",
        "url_ver_detalle": f"{settings.FRONTEND_URL}/dashboard/plantilla_empleados?tab=movimientos&posicion={sub.posicion}" if getattr(settings, "FRONTEND_URL", None) else "#",
    }

    _enviar_email_html(
        subject=f"Posición {sub.posicion} quedó vacante — Sistema de Control de Plazas",
        template_name="emails/notificacion_vacante.html",
        context=context,
        to_email=sub.usuario.email,
    )
    return True


# ---------------------------------------------------------------------------
# Correo de OCUPACIÓN
# ---------------------------------------------------------------------------

def _buscar_movimiento_ocupacion(emp):
    """Resuelve `accion`/`accion_nombre`/`por` para el correo de ocupación,
    ausentes en EMPLEADOS_COMPLETOS_SIG (confirmado contra BD viva). Match
    definido junto con el usuario: posición + num_empleado + motivo (nombre,
    no código — así lo guarda EMPLEADOS_COMPLETOS_SIG.Motivo) + fecha
    efectiva + fecha de captura; desempate por `sec` más alto si hay
    varias filas candidatas."""
    from .models import CpTblMovCompleto290526

    fecha_efectiva = _parse_fecha_charfield(emp.fecha_efectiva_personal)
    fecha_captura = _parse_fecha_charfield(emp.fecha_de_captura)
    id_empleado = (emp.id_empleado or "").strip()
    motivo = (emp.motivo or "").strip()

    if not id_empleado or not motivo or not fecha_efectiva or not fecha_captura:
        return None

    return (
        CpTblMovCompleto290526.objects
        .filter(
            posicion=emp.posicion,
            num_empleado=id_empleado,
            motivo_nombre=motivo,
            fecha_efectiva=fecha_efectiva,
            fecha_captura=fecha_captura,
        )
        .order_by("-sec")
        .first()
    )


def enviar_correo_ocupacion(sub):
    """Manda el correo de "la posición se ocupó" para la suscripción `sub`
    (tipo OCUPACION). Devuelve True si se envió; deja propagar la excepción
    si algo falla."""
    from .models import EmpleadosCompletosSig

    emp = EmpleadosCompletosSig.objects.get(posicion=sub.posicion)
    movimiento = _buscar_movimiento_ocupacion(emp)

    context = {
        "posicion": emp.posicion,
        "nombres": emp.nombres,
        "numempleado": emp.numempleado or emp.id_empleado,
        "empleado_iniciales": _iniciales(emp.nombres),
        "motivo": emp.motivo,
        "fecha_efectiva": emp.fecha_efectiva_personal,
        "fecha_captura": emp.fecha_de_captura,
        "rfc": emp.rfc,
        "curp": emp.curp,
        "fecha_prevista_de_salida": emp.fecha_prevista_de_salida,
        "accion": movimiento.accion if movimiento else None,
        "accion_nombre": movimiento.accion_nombre if movimiento else None,
        "por": movimiento.por if movimiento else None,
        "url_ver_detalle": f"{settings.FRONTEND_URL}/dashboard/plantilla_empleados?tab=plantilla_detalle&posicion={sub.posicion}" if getattr(settings, "FRONTEND_URL", None) else "#",
    }

    _enviar_email_html(
        subject=f"Posición {sub.posicion} fue ocupada — Sistema de Control de Plazas",
        template_name="emails/notificacion_ocupacion.html",
        context=context,
        to_email=sub.usuario.email,
    )
    return True


# ---------------------------------------------------------------------------
# Orquestador — llamado desde tasks.py e InvalidarCacheZafiroView
# ---------------------------------------------------------------------------

def procesar_suscripciones_posicion():
    """
    Recorre las suscripciones activas y, para cada una cuyo estado actual ya
    no coincide con el snapshot tomado al suscribirse, manda el correo
    correspondiente y la desactiva (un solo aviso). Nunca deja que el fallo
    de UNA suscripción tumbe el resto — se loguea y se reintenta en la
    siguiente corrida de Celery (cada 30 min) porque `activa` no se apaga
    si el envío falla.
    """
    from .models import SuscripcionNotificacionPosicion
    from .views import get_posiciones_ocupadas_set

    posiciones_ocupadas = get_posiciones_ocupadas_set()
    suscripciones = (
        SuscripcionNotificacionPosicion.objects
        .filter(activa=True)
        .select_related("usuario")
    )

    enviados = 0
    errores = 0
    for sub in suscripciones:
        estado_actual = "O" if sub.posicion in posiciones_ocupadas else "V"
        if estado_actual == sub.estado_conocido_al_suscribir:
            continue  # sin cambio respecto al snapshot, no dispara nada

        tipo_dispara = "OCUPACION" if estado_actual == "O" else "VACANTE"
        if sub.tipo != tipo_dispara:
            continue  # cambió, pero no es el tipo que le interesa a esta suscripción

        try:
            if estado_actual == "O":
                enviar_correo_ocupacion(sub)
            else:
                enviar_correo_vacancia(sub)
            sub.activa = False
            sub.notificado_en = timezone.now()
            sub.save(update_fields=["activa", "notificado_en"])
            enviados += 1
        except Exception:
            logger.exception(
                "Error notificando SuscripcionNotificacionPosicion id=%s (posicion=%s, tipo=%s)",
                sub.id, sub.posicion, sub.tipo,
            )
            errores += 1

    if enviados or errores:
        logger.info(
            "procesar_suscripciones_posicion: %d correo(s) enviado(s), %d error(es).",
            enviados, errores,
        )
    return {"enviados": enviados, "errores": errores}
