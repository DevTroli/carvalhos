from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from .forms import CadastroForm, PerfilForm
from .models import Perfil


def eh_administrador(usuario):
    if usuario.is_staff or usuario.is_superuser:
        return True
    perfil = Perfil.objects.filter(usuario=usuario).first()
    return bool(perfil and perfil.tipo_usuario == "administrador")


class EntrarView(LoginView):
    """Login com redirecionamento por perfil: admin -> /admin, cliente -> Dashboard."""

    template_name = "login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        destino = self.get_redirect_url()
        if destino:
            return destino
        return "/admin/" if eh_administrador(self.request.user) else "/login/dashboard/"


@login_required
def dashboard(request):
    # Garante perfil mesmo para contas criadas pelo createsuperuser.
    Perfil.objects.get_or_create(usuario=request.user)
    return render(request, "dashboard.html")


@login_required
def perfil(request):
    form = PerfilForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Dados atualizados.")
        return redirect("perfil")
    return render(request, "perfil.html", {"form": form})


def cadastro(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = CadastroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        Perfil.objects.create(usuario=usuario, tipo_usuario="cliente")
        messages.success(request, "Conta criada. Entre com seu usuário e senha.")
        return redirect("login")
    return render(request, "cadastro.html", {"form": form})
