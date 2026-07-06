import subprocess
from pathlib import Path

from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


def _get_last_commit(repo_path: Path):
    """Devuelve el último commit de `main` en `repo_path`, o None si no se puede leer."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=format:%H|%cI|%s"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        commit_hash, date_iso, message = result.stdout.split("|", 2)
        return {"hash": commit_hash[:7], "fecha": date_iso, "mensaje": message}
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
        ValueError,
    ):
        return None


class SystemLastUpdateView(APIView):
    """Última actualización de código (commit más reciente entre back y front)."""

    permission_classes = [AllowAny]

    def get(self, request):
        back_commit = _get_last_commit(settings.BASE_DIR)

        front_path = Path(
            getattr(settings, "FRONTEND_REPO_PATH", settings.BASE_DIR.parent / "eje_central_front")
        )
        front_commit = _get_last_commit(front_path)

        candidates = [
            {**back_commit, "repo": "back"} if back_commit else None,
            {**front_commit, "repo": "front"} if front_commit else None,
        ]
        candidates = [c for c in candidates if c]

        if not candidates:
            return Response(
                {"detail": "No se pudo determinar la última actualización."}, status=503
            )

        latest = max(candidates, key=lambda c: c["fecha"])
        return Response(latest)
