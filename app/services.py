"""Regras de negócio da Carvalhos: entrada de estoque e indicadores de custo."""
import csv
import io
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Avg, Count, F, Sum

from .models import Custo, EntradaEstoque, Servico

ZERO = Decimal("0")


class ErroEntrada(Exception):
    pass


def _decimal(texto):
    texto = str(texto).strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        raise ErroEntrada(f"Valor inválido: {texto!r}")
    if valor < 0:
        raise ErroEntrada("Valores não podem ser negativos.")
    return valor


def registrar_entradas(linhas, usuario=None):
    """Registra várias entradas de uma vez, tudo ou nada.

    linhas: lista de (servico, quantidade, custo_unitario).
    Soma ao estoque e atualiza o custo pela média ponderada.
    """
    linhas = [l for l in linhas if l]
    if not linhas:
        raise ErroEntrada("Informe ao menos um item.")
    with transaction.atomic():
        for servico, quantidade, custo in linhas:
            if quantidade <= 0:
                raise ErroEntrada(f"Quantidade inválida para {servico.nome}.")
            servico = Servico.objects.select_for_update().get(pk=servico.pk)
            total = servico.estoque + quantidade
            novo_custo = (
                (servico.preco_custo * servico.estoque + custo * quantidade) / total
            ).quantize(Decimal("0.01"))
            servico.estoque = total
            servico.preco_custo = novo_custo
            servico.save(update_fields=["estoque", "preco_custo", "atualizado_em"])
            EntradaEstoque.objects.create(
                servico=servico, quantidade=quantidade,
                custo_unitario=custo, usuario=usuario,
            )
    return len(linhas)


def linhas_do_formulario(post):
    ids = post.getlist("produto")
    qtds = post.getlist("quantidade")
    custos = post.getlist("custo")
    linhas = []
    for i, (pid, q, c) in enumerate(zip(ids, qtds, custos), start=1):
        if not (pid or q or c):
            continue  # linha em branco
        try:
            servico = Servico.objects.get(pk=pid)
            quantidade = int(q)
        except (Servico.DoesNotExist, ValueError):
            raise ErroEntrada(f"Linha {i}: escolha o produto e uma quantidade inteira.")
        linhas.append((servico, quantidade, _decimal(c or servico.preco_custo)))
    return linhas


def linhas_do_csv(arquivo):
    """CSV com colunas: produto (nome ou id), quantidade, custo_unitario."""
    texto = arquivo.read().decode("utf-8-sig", errors="replace")
    try:
        dialeto = csv.Sniffer().sniff(texto[:2000], delimiters=";,\t")
    except csv.Error:
        dialeto = csv.excel
    leitor = csv.DictReader(io.StringIO(texto), dialect=dialeto)
    linhas = []
    for i, linha in enumerate(leitor, start=2):
        linha = {(k or "").strip().lower(): (v or "").strip() for k, v in linha.items()}
        ref = linha.get("produto", "")
        if not ref:
            continue
        servico = (
            Servico.objects.filter(pk=int(ref)).first() if ref.isdigit() else None
        ) or Servico.objects.filter(nome__iexact=ref).first()
        if not servico:
            raise ErroEntrada(f"Linha {i}: produto {ref!r} não encontrado.")
        try:
            quantidade = int(linha.get("quantidade", ""))
        except ValueError:
            raise ErroEntrada(f"Linha {i}: quantidade inválida.")
        custo = linha.get("custo_unitario") or linha.get("custo") or ""
        linhas.append((servico, quantidade, _decimal(custo) if custo else servico.preco_custo))
    return linhas


def indicadores_custos():
    """Números da tela de Relatórios: custos, margem e ponto de equilíbrio."""
    fixo = Custo.objects.filter(tipo=Custo.FIXO).aggregate(t=Sum("valor"))["t"] or ZERO
    variavel = Custo.objects.filter(tipo=Custo.VARIAVEL).aggregate(m=Avg("valor"))["m"] or ZERO
    ativos = Servico.objects.filter(ativo=True)
    margem_bruta = ativos.aggregate(m=Avg(F("preco") - F("preco_custo")))["m"] or ZERO
    margem_unidade = margem_bruta - variavel
    equilibrio = None
    if margem_unidade > 0 and fixo > 0:
        equilibrio = int((fixo / margem_unidade).to_integral_value(rounding="ROUND_CEILING"))
    valor_estoque = sum((s.estoque * s.preco_custo for s in ativos), ZERO)
    return {
        "custo_fixo": fixo,
        "custo_variavel": variavel,
        "margem_media": margem_unidade,
        "ponto_equilibrio": equilibrio,
        "valor_estoque": valor_estoque,
        "estoque_baixo": sum(1 for s in ativos if s.estoque_baixo),
    }
