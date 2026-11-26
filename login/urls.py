from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.EntrarView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("perfil/", views.perfil, name="perfil"),
    path("alterar-senha/", auth_views.PasswordChangeView.as_view(
        template_name="alterar_senha.html", success_url="/login/perfil/"), name="alterar_senha"),
    path("cadastro/", views.cadastro, name="cadastro"),
    # Recuperação de senha nativa do Django (telas padrão do Django).
    path("esqueci-senha/", auth_views.PasswordResetView.as_view(), name="password_reset"),
    path("esqueci-senha/enviado/", auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("redefinir/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("redefinir/concluido/", auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
