import io
import logging
from decimal import Decimal

import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import transaction
from django.db.models import Avg, Count, F, Max, Min, Q, Sum
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from . import services, supabase_client as equipe
from .forms import FormContato, FormCusto, FormIntegrante, FormServico
from .models import Categoria, Contato, Custo, EntradaEstoque, Pedido, Servico
from .serializers import CategoriaSerializer

logger = logging.getLogger(__name__)

# Área de gestão: hoje exige login (como nas telas de referência do PDF).
# Para restringir só à equipe, troque por user_passes_test(lambda u: u.is_staff).
gestao_required = login_required


# ---------------------------------------------------------------- páginas públicas
def index(request):
    destaques = Servico.objects.filter(ativo=True).select_related("categoria")[:3]
    return render(request, "index.html", {"destaques": destaques})


def quem_somos(request):
    try:
        integrantes = equipe.listar_integrantes()
        indisponivel = False
    except equipe.EquipeIndisponivel:
        integrantes, indisponivel = [], True
    return render(request, "quem_somos.html",
                  {"integrantes": integrantes, "indisponivel": indisponivel})


def produtos_parceiros():
    """Produtos da API externa. Com cache e fallback para nunca derrubar a página."""
    dados = cache.get("produtos_api")
    if dados is not None:
        return dados, True
    try:
        resposta = requests.get("https://fakestoreapi.com/products", timeout=5)
        resposta.raise_for_status()
        dados = resposta.json()
        cache.set("produtos_api", dados, 600)
        return dados, True
    except (requests.RequestException, ValueError):
        logger.warning("API externa de produtos indisponível", exc_info=True)
        return [], False


def produtos(request):
    locais = Servico.objects.filter(ativo=True).select_related("categoria")
    api, api_ok = produtos_parceiros()
    return render(request, "produtos.html",
                  {"servicos": locais, "produtos_api": api, "api_ok": api_ok})


def add_contato(request):
    """Formulário público: qualquer visitante pode enviar, sem login."""
    form = FormContato(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Mensagem enviada. Obrigado pelo contato, responderemos em breve.")
        return redirect("add_contato")
    return render(request, "add-contato.html", {"form": form})


# ---------------------------------------------------------------- pedidos
@require_POST
@login_required
def comprar(request, id_servico):
    with transaction.atomic():
        servico = get_object_or_404(Servico.objects.select_for_update(), id=id_servico, ativo=True)
        Pedido.objects.create(usuario=request.user, servico=servico, preco=servico.preco)
        if servico.estoque > 0:
            servico.estoque = F("estoque") - 1
            servico.save(update_fields=["estoque"])
    messages.success(request, f"“{servico.nome}” foi adicionado aos seus pedidos.")
    return redirect("produtos")


@login_required
def meus_pedidos(request):
    pedidos = request.user.pedidos.select_related("servico")
    total = pedidos.aggregate(t=Sum("preco"))["t"] or Decimal("0")
    return render(request, "pedidos.html", {"pedidos": pedidos, "total": total})


# ---------------------------------------------------------------- contatos (gestão)
@gestao_required
def contatos(request):
    lista = Contato.objects.all().order_by("-id")
    return render(request, "contatos.html", {"contatos": lista})


@require_POST
@gestao_required
def del_contato(request, id_contato):
    get_object_or_404(Contato, id=id_contato).delete()
    messages.success(request, "Contato excluído.")
    return redirect("contatos")


# ---------------------------------------------------------------- produtos (gestão)
FAIXAS_PRECO = {
    "baixo": ("Até R$ 50", Q(preco__lte=50)),
    "medio": ("R$ 50 a R$ 200", Q(preco__gt=50, preco__lte=200)),
    "alto": ("Acima de R$ 200", Q(preco__gt=200)),
}
ORDENS = {
    "nome": ("Nome (A-Z)", "nome"),
    "menor": ("Menor preço", "preco"),
    "maior": ("Maior preço", "-preco"),
    "margem": ("Maior margem", "-margem_calc"),
    "estoque": ("Menor estoque", "estoque"),
}


@gestao_required
def servicos(request):
    todos = Servico.objects.all()
    estat = todos.aggregate(menor=Min("preco"), maior=Max("preco"), margem=Avg(F("preco") - F("preco_custo")))
    estat.update(total=todos.count(), ativos=todos.filter(ativo=True).count(),
                 baixo=sum(1 for s in todos if s.ativo and s.estoque_baixo))

    busca = request.GET.get("busca", "").strip()
    categoria = request.GET.get("categoria", "")
    faixa = request.GET.get("preco", "")
    ordem = request.GET.get("ordem", "nome")
    so_baixo = request.GET.get("estoque") == "baixo"

    lista = todos.select_related("categoria").annotate(margem_calc=F("preco") - F("preco_custo"))
    if busca:
        lista = lista.filter(nome__icontains=busca)
    if categoria.isdigit():
        lista = lista.filter(categoria_id=categoria)
    if faixa in FAIXAS_PRECO:
        lista = lista.filter(FAIXAS_PRECO[faixa][1])
    if so_baixo:
        lista = lista.filter(estoque__lte=F("estoque_minimo"))
    lista = lista.order_by(ORDENS.get(ordem, ORDENS["nome"])[1])

    return render(request, "servicos.html", {
        "servicos": lista, "estat": estat,
        "categorias": Categoria.objects.filter(ativo=True),
        "faixas": {k: v[0] for k, v in FAIXAS_PRECO.items()},
        "ordens": {k: v[0] for k, v in ORDENS.items()},
        "busca": busca, "categoria": categoria, "faixa": faixa,
        "ordem": ordem, "so_baixo": so_baixo,
    })


@gestao_required
def addServicos(request):
    form = FormServico(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Produto cadastrado.")
        return redirect("servicos")
    return render(request, "servico-form.html", {"form": form, "editando": False})


@gestao_required
def editServicos(request, id_servico):
    servico = get_object_or_404(Servico, id=id_servico)
    form = FormServico(request.POST or None, request.FILES or None, instance=servico)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Produto atualizado.")
        return redirect("servicos")
    return render(request, "servico-form.html", {"form": form, "editando": True, "servico": servico})


@require_POST
@gestao_required
def delServicos(request, id_servico):
    servico = get_object_or_404(Servico, id=id_servico)
    if servico.pedidos.exists():
        servico.ativo = False
        servico.save(update_fields=["ativo"])
        messages.warning(request, "Este produto já tem pedidos, então foi apenas desativado.")
    else:
        servico.delete()
        messages.success(request, "Produto excluído.")
    return redirect("servicos")


# ---------------------------------------------------------------- estoque e custos
@gestao_required
def entrada_estoque(request):
    if request.method == "POST":
        try:
            if request.FILES.get("arquivo"):
                linhas = services.linhas_do_csv(request.FILES["arquivo"])
            else:
                linhas = services.linhas_do_formulario(request.POST)
            qtd = services.registrar_entradas(linhas, request.user)
            messages.success(request, f"{qtd} entrada(s) registradas. Estoque e custo atualizados.")
            return redirect("entrada_estoque")
        except services.ErroEntrada as erro:
            messages.error(request, f"Nada foi salvo. {erro}")
    return render(request, "entrada-estoque.html", {
        "produtos": Servico.objects.filter(ativo=True),
        "historico": EntradaEstoque.objects.select_related("servico", "usuario")[:15],
    })


@gestao_required
def modelo_csv(request):
    resposta = HttpResponse(content_type="text/csv; charset=utf-8")
    resposta["Content-Disposition"] = 'attachment; filename="modelo-entrada-estoque.csv"'
    resposta.write("produto;quantidade;custo_unitario\r\n")
    for p in Servico.objects.filter(ativo=True)[:3]:
        resposta.write(f"{p.nome};10;{str(p.preco_custo).replace('.', ',')}\r\n")
    return resposta


@gestao_required
def custos(request):
    form = FormCusto(request.POST or None, initial={"data": timezone.localdate()})
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Custo registrado.")
        return redirect("custos")
    return render(request, "custos.html", {
        "form": form, "custos": Custo.objects.all(), "ind": services.indicadores_custos(),
    })


@require_POST
@gestao_required
def del_custo(request, id_custo):
    get_object_or_404(Custo, id=id_custo).delete()
    messages.success(request, "Custo excluído.")
    return redirect("custos")


# ---------------------------------------------------------------- relatórios
@gestao_required
def relatorios(request):
    todos = Servico.objects.all()
    categorias = todos.values("categoria__nome").annotate(quantidade=Count("id")).order_by("categoria__nome")
    ind = services.indicadores_custos()
    return render(request, "relatorio.html", {
        "total": todos.count(),
        "ativos": todos.filter(ativo=True).count(),
        "inativos": todos.filter(ativo=False).count(),
        "ind": ind,
        "grafico": {
            "categorias": [c["categoria__nome"] or "Sem categoria" for c in categorias],
            "quantidades": [c["quantidade"] for c in categorias],
            "ativos": todos.filter(ativo=True).count(),
            "inativos": todos.filter(ativo=False).count(),
            "margem_nomes": [s.nome for s in todos.filter(ativo=True)[:10]],
            "margem_valores": [float(s.margem) for s in todos.filter(ativo=True)[:10]],
            "estoque_nomes": [s.nome for s in todos.filter(ativo=True)[:10]],
            "estoque_qtd": [s.estoque for s in todos.filter(ativo=True)[:10]],
            "estoque_min": [s.estoque_minimo for s in todos.filter(ativo=True)[:10]],
        },
    })


@gestao_required
def exportar_excel(request):
    from openpyxl import Workbook
    from openpyxl.chart import BarChart, Reference
    from openpyxl.styles import Alignment, Font, PatternFill

    verde = PatternFill("solid", fgColor="0B3D2A")
    cab = Font(bold=True, color="FFFFFF")

    def cabecalho(ws, colunas):
        ws.append(colunas)
        for c in ws[1]:
            c.fill, c.font, c.alignment = verde, cab, Alignment(horizontal="center")
        ws.freeze_panes = "A2"

    wb = Workbook()
    ws = wb.active
    ws.title = "Produtos"
    cabecalho(ws, ["Produto", "Categoria", "Custo (R$)", "Venda (R$)", "Margem (R$)",
                   "Margem (%)", "Estoque", "Mínimo", "Situação"])
    produtos = list(Servico.objects.select_related("categoria"))
    for i, p in enumerate(produtos, start=2):
        ws.append([p.nome, p.categoria.nome if p.categoria else "Sem categoria",
                   float(p.preco_custo), float(p.preco), f"=D{i}-C{i}",
                   f"=IF(D{i}=0,0,E{i}/D{i})", p.estoque, p.estoque_minimo,
                   f'=IF(G{i}<=H{i},"Estoque baixo","OK")'])
        ws[f"F{i}"].number_format = "0.0%"
        for col in "CDE":
            ws[f"{col}{i}"].number_format = '"R$" #,##0.00'
    fim = len(produtos) + 1
    if produtos:
        ws.append(["Total", "", f"=SUM(C2:C{fim})", f"=SUM(D2:D{fim})", f"=SUM(E2:E{fim})",
                   "", f"=SUM(G2:G{fim})"])
        for c in ws[fim + 1]:
            c.font = Font(bold=True)
        graf = BarChart()
        graf.title, graf.y_axis.title = "Estoque atual por produto", "Unidades"
        graf.add_data(Reference(ws, min_col=7, min_row=1, max_row=fim), titles_from_data=True)
        graf.set_categories(Reference(ws, min_col=1, min_row=2, max_row=fim))
        graf.width, graf.height = 22, 10
        ws.add_chart(graf, "K2")

    wc = wb.create_sheet("Custos")
    cabecalho(wc, ["Descrição", "Tipo", "Valor (R$)", "Data"])
    lista = list(Custo.objects.all())
    for c in lista:
        wc.append([c.descricao, c.get_tipo_display(), float(c.valor), c.data])
    for linha in wc.iter_rows(min_row=2):
        linha[2].number_format = '"R$" #,##0.00'
        linha[3].number_format = "dd/mm/yyyy"
    if lista:
        n = len(lista) + 1
        wc.append([])
        wc.append(["Total fixo (mês)", "", f'=SUMIF(B2:B{n},"Fixo*",C2:C{n})'])
        wc.append(["Variável (média por unidade)", "", f'=IFERROR(AVERAGEIF(B2:B{n},"Variável*",C2:C{n}),0)'])

    we = wb.create_sheet("Entradas de estoque")
    cabecalho(we, ["Data", "Produto", "Quantidade", "Custo unitário (R$)", "Total (R$)"])
    for i, e in enumerate(EntradaEstoque.objects.select_related("servico"), start=2):
        we.append([timezone.localtime(e.criado_em).replace(tzinfo=None), e.servico.nome,
                   e.quantidade, float(e.custo_unitario), f"=C{i}*D{i}"])
        we[f"A{i}"].number_format = "dd/mm/yyyy hh:mm"
        we[f"D{i}"].number_format = we[f"E{i}"].number_format = '"R$" #,##0.00'

    wp = wb.create_sheet("Pedidos")
    cabecalho(wp, ["Data", "Cliente", "Produto", "Valor (R$)"])
    for p in Pedido.objects.select_related("usuario", "servico"):
        wp.append([timezone.localtime(p.criado_em).replace(tzinfo=None), p.usuario.username,
                   p.servico.nome, float(p.preco)])
    for linha in wp.iter_rows(min_row=2):
        linha[0].number_format = "dd/mm/yyyy hh:mm"
        linha[3].number_format = '"R$" #,##0.00'

    for planilha in wb.worksheets:
        for col in planilha.columns:
            largura = max(len(str(c.value or "")) for c in col[:50])
            planilha.column_dimensions[col[0].column_letter].width = min(max(12, largura + 2), 45)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    nome = f"carvalhos-{timezone.localdate():%Y-%m-%d}.xlsx"
    return FileResponse(buf, as_attachment=True, filename=nome)


# ---------------------------------------------------------------- equipe (Supabase)
def _dados_integrante(form):
    d = form.cleaned_data
    return {"nome": d["nome"], "cargo": d["cargo"],
            "biografia": d["biografia"], "foto_url": d["foto_url"]}


@gestao_required
def integrantes(request):
    try:
        lista, indisponivel = equipe.listar_integrantes(), False
    except equipe.EquipeIndisponivel:
        lista, indisponivel = [], True
    return render(request, "integrantes.html", {"integrantes": lista, "indisponivel": indisponivel})


@gestao_required
def addIntegrante(request):
    form = FormIntegrante(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            equipe.criar_integrante(_dados_integrante(form))
            messages.success(request, "Integrante cadastrado.")
            return redirect("integrantes")
        except equipe.EquipeIndisponivel:
            messages.error(request, "Não foi possível falar com o banco remoto. Tente novamente.")
    return render(request, "integrante-form.html", {"form": form, "editando": False})


@gestao_required
def editIntegrante(request, id_integrante):
    try:
        atual = equipe.obter_integrante(id_integrante)
    except equipe.EquipeIndisponivel:
        messages.error(request, "Banco remoto indisponível no momento.")
        return redirect("integrantes")
    if not atual:
        messages.error(request, "Integrante não encontrado.")
        return redirect("integrantes")
    inicial = {k: atual.get(k) or "" for k in ("nome", "cargo", "biografia", "foto_url")}
    form = FormIntegrante(request.POST or None, initial=inicial)
    if request.method == "POST" and form.is_valid():
        try:
            equipe.atualizar_integrante(id_integrante, _dados_integrante(form))
            messages.success(request, "Integrante atualizado.")
            return redirect("integrantes")
        except equipe.EquipeIndisponivel:
            messages.error(request, "Não foi possível salvar no banco remoto.")
    return render(request, "integrante-form.html",
                  {"form": form, "editando": True, "integrante": atual})


@require_POST
@gestao_required
def delIntegrante(request, id_integrante):
    try:
        equipe.excluir_integrante(id_integrante)
        messages.success(request, "Integrante excluído.")
    except equipe.EquipeIndisponivel:
        messages.error(request, "Não foi possível excluir no banco remoto.")
    return redirect("integrantes")


# ---------------------------------------------------------------- API (somente equipe)
@api_view(["GET", "POST"])
@permission_classes([IsAdminUser])
def categoriasAPI(request):
    if request.method == "GET":
        return Response(CategoriaSerializer(Categoria.objects.all(), many=True).data)
    serializer = CategoriaSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "DELETE", "PUT"])
@permission_classes([IsAdminUser])
def categoriaAPI(request, id_categoria):
    categoria = get_object_or_404(Categoria, id=id_categoria)
    if request.method == "GET":
        return Response(CategoriaSerializer(categoria).data)
    if request.method == "DELETE":
        categoria.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = CategoriaSerializer(categoria, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
