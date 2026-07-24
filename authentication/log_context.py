"""Expone el usuario de la request actual a los logs (contextvar por request/hilo)."""

import contextvars
import logging

_current_request = contextvars.ContextVar("current_request", default=None)


class RequestUserLogMiddleware:
    """Guarda la request en un contextvar mientras dura, para que RequestUserLogFilter
    pueda leer request.user en cualquier log emitido durante su procesamiento.

    DRF autentica (TokenAuthentication) dentro del dispatch de la vista y sincroniza
    el usuario resultante de vuelta a request.user, así que basta con envolver
    get_response para que los logs de la vista ya vean el usuario correcto.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _current_request.set(request)
        try:
            return self.get_response(request)
        finally:
            _current_request.reset(token)


class RequestUserLogFilter(logging.Filter):
    def filter(self, record):
        request = _current_request.get()
        email = None
        if request is not None:
            user = getattr(request, "user", None)
            if user is not None and getattr(user, "is_authenticated", False):
                email = getattr(user, "email", None) or getattr(user, "username", None)
        record.user_email = email or "anon"
        return True
