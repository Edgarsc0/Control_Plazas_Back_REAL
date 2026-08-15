"""Expone el usuario de la request actual a los logs (contextvar por request/hilo)."""

import contextvars
import logging

_current_request = contextvars.ContextVar("current_request", default=None)

_access_logger = logging.getLogger("controlplazas.request")


class RequestUserLogMiddleware:
    """Guarda la request en un contextvar mientras dura, para que RequestUserLogFilter
    pueda leer request.user en cualquier log emitido durante su procesamiento.

    DRF autentica (TokenAuthentication) dentro del dispatch de la vista y sincroniza
    el usuario resultante de vuelta a request.user, así que basta con envolver
    get_response para que los logs de la vista ya vean el usuario correcto.

    También emite un log propio por request (el access log de gunicorn no pasa por
    el logging de Django, así que no lleva el correo ni el color resaltado).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _current_request.set(request)
        try:
            response = self.get_response(request)
            _access_logger.info("-> %s", getattr(response, "status_code", "-"))
            return response
        finally:
            _current_request.reset(token)


class RequestUserLogFilter(logging.Filter):
    def filter(self, record):
        request = _current_request.get()
        email = None
        endpoint = "-"
        if request is not None:
            user = getattr(request, "user", None)
            if user is not None and getattr(user, "is_authenticated", False):
                email = getattr(user, "email", None) or getattr(user, "username", None)
            endpoint = f"{request.method} {request.path}"
        record.user_email = email or "anon"
        record.endpoint = endpoint
        return True


_MAGENTA = "\033[1;35m"
_CYAN = "\033[1;36m"
_RESET = "\033[0m"


class UserEmailColorFormatter(logging.Formatter):
    """Resalta [user_email] en magenta y el endpoint en cyan para distinguirlos del resto de la línea."""

    def format(self, record):
        formatted = super().format(record)
        user_highlight = f"[{record.user_email}]"
        formatted = formatted.replace(user_highlight, f"{_MAGENTA}{user_highlight}{_RESET}", 1)
        endpoint_highlight = f"[{record.endpoint}]"
        formatted = formatted.replace(endpoint_highlight, f"{_CYAN}{endpoint_highlight}{_RESET}", 1)
        return formatted
