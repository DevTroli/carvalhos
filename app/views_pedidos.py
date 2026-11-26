from decimal import ROUND_HALF_UP, Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Pedido, Servico


@require_POST
@login_required
def comprar(request, id_servico):
    """Registra o pedido e leva o cliente à página de confirmação."""
    with transaction.atomic():
        servico = get_object_or_404(
            Servico.objects.select_for_update(), id=id_servico, ativo=True
        )
        pedido = Pedido.objects.create(
            usuario=request.user, servico=servico, preco=servico.preco
        )
        if servico.estoque > 0:
            servico.estoque = F("estoque") - 1
            servico.save(update_fields=["estoque"])
    return redirect("pedido_confirmado", id_pedido=pedido.id)


@login_required
def pedido_confirmado(request, id_pedido):
    pedido = get_object_or_404(
        Pedido.objects.select_related("servico"), id=id_pedido, usuario=request.user
    )
    return render(request, "pedido-confirmado.html", {"pedido": pedido})


@login_required
def meus_pedidos(request):
    pedidos = request.user.pedidos.select_related("servico").order_by("-criado_em")
    total = pedidos.aggregate(t=Sum("preco"))["t"] or Decimal("0")
    total = Decimal(total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return render(request, "pedidos.html", {"pedidos": pedidos, "total": total})
