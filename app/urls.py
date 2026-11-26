from django.urls import path

from . import views

urlpatterns = [
    # públicas
    path("", views.index, name="index"),
    path("quem-somos/", views.quem_somos, name="quem_somos"),
    path("produtos", views.produtos, name="produtos"),
    path("contato/add-contato/", views.add_contato, name="add_contato"),
    # pedidos (cliente logado)
    path("comprar/<int:id_servico>/", views.comprar, name="comprar"),
    path("pedidos/", views.meus_pedidos, name="pedidos"),
    # gestão: contatos
    path("contato/contatos/", views.contatos, name="contatos"),
    path("contato/del-contato/<int:id_contato>/", views.del_contato, name="del_contato"),
    # gestão: produtos
    path("servicos", views.servicos, name="servicos"),
    path("add-servicos", views.addServicos, name="addServicos"),
    path("edit-servicos/<int:id_servico>", views.editServicos, name="editServicos"),
    path("del-servicos/<int:id_servico>", views.delServicos, name="delServicos"),
    # gestão: estoque e custos
    path("estoque/entrada/", views.entrada_estoque, name="entrada_estoque"),
    path("estoque/modelo.csv", views.modelo_csv, name="modelo_csv"),
    path("custos/", views.custos, name="custos"),
    path("custos/<int:id_custo>/excluir/", views.del_custo, name="del_custo"),
    # gestão: equipe (Supabase)
    path("integrantes", views.integrantes, name="integrantes"),
    path("add-integrante", views.addIntegrante, name="addIntegrante"),
    path("edit-integrante/<int:id_integrante>", views.editIntegrante, name="editIntegrante"),
    path("del-integrante/<int:id_integrante>", views.delIntegrante, name="delIntegrante"),
    # relatórios
    path("relatorios/", views.relatorios, name="relatorios"),
    path("relatorios/exportar.xlsx", views.exportar_excel, name="exportar_excel"),
    # API
    path("categoria-api/", views.categoriasAPI, name="categoriasAPI"),
    path("categoria-api/<int:id_categoria>", views.categoriaAPI, name="categoriaAPI"),
]
