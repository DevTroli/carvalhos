from django.contrib import admin

from .models import Categoria, Contato, Custo, EntradaEstoque, Pedido, Servico

admin.site.register(Categoria)


@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ["nome", "categoria", "preco_custo", "preco", "estoque", "ativo"]
    list_filter = ["categoria", "ativo"]
    search_fields = ["nome", "descricao"]
    list_per_page = 25


@admin.register(Contato)
class ContatoAdmin(admin.ModelAdmin):
    list_display = ["nome", "email", "telefone"]
    search_fields = ["nome", "email", "mensagem"]


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ["usuario", "servico", "preco", "criado_em"]
    list_filter = ["criado_em"]


@admin.register(Custo)
class CustoAdmin(admin.ModelAdmin):
    list_display = ["descricao", "tipo", "valor", "data"]
    list_filter = ["tipo"]


@admin.register(EntradaEstoque)
class EntradaEstoqueAdmin(admin.ModelAdmin):
    list_display = ["servico", "quantidade", "custo_unitario", "usuario", "criado_em"]
