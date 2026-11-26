from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .views import eh_administrador


def gestao_required(view):
    """Exige login e perfil de administrador/staff. Cliente logado recebe 403."""

    @wraps(view)
    @login_required
    def interna(request, *args, **kwargs):
        if not eh_administrador(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return interna
