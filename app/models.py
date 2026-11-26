from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Categoria(models.Model):
    nome = models.CharField(max_length=100, default="Geral")
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome


class Servico(models.Model):
    """Produto vendido pela Carvalhos (o nome da tabela segue o enunciado)."""

    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    preco = models.DecimalField(
        "Preço de venda", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    preco_custo = models.DecimalField(
        "Preço de custo", max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal("0"))],
    )
    estoque = models.PositiveIntegerField("Estoque atual", default=0)
    estoque_minimo = models.PositiveIntegerField("Estoque mínimo", default=0)
    link_ml = models.URLField("Link do anúncio no Mercado Livre", blank=True)
    imagem = models.ImageField(upload_to="servicos/", blank=True, null=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="servicos",
        null=True, blank=True,
    )

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    @property
    def margem(self):
        """Quanto sobra em cada venda (venda menos custo)."""
        return self.preco - self.preco_custo

    @property
    def margem_percentual(self):
        if not self.preco:
            return Decimal("0")
        return (self.margem / self.preco) * 100

    @property
    def estoque_baixo(self):
        return self.estoque <= self.estoque_minimo


class Contato(models.Model):
    nome = models.CharField(max_length=100)
    email = models.EmailField()
    telefone = models.CharField(max_length=20, blank=True)
    mensagem = models.TextField()

    class Meta:
        db_table = "contato_contato"
        verbose_name = "Contato"
        verbose_name_plural = "Contatos"

    def __str__(self):
        return self.nome


class Pedido(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pedidos"
    )
    servico = models.ForeignKey(Servico, on_delete=models.PROTECT, related_name="pedidos")
    # Preço no momento da compra: não muda se o produto for reajustado depois.
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.usuario} - {self.servico}"


class Custo(models.Model):
    """Custo da operação. Fixo = valor por mês. Variável = valor por unidade."""

    FIXO = "fixo"
    VARIAVEL = "variavel"
    TIPOS = [(FIXO, "Fixo (por mês)"), (VARIAVEL, "Variável (por unidade vendida)")]

    descricao = models.CharField("Descrição", max_length=150)
    tipo = models.CharField(max_length=10, choices=TIPOS, default=FIXO)
    valor = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    data = models.DateField()

    class Meta:
        ordering = ["-data", "descricao"]

    def __str__(self):
        return f"{self.descricao} ({self.get_tipo_display()})"


class EntradaEstoque(models.Model):
    """Histórico de cada entrada de mercadoria (auditoria do estoque)."""

    servico = models.ForeignKey(Servico, on_delete=models.PROTECT, related_name="entradas")
    quantidade = models.PositiveIntegerField()
    custo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Entrada de estoque"
        verbose_name_plural = "Entradas de estoque"

    def __str__(self):
        return f"{self.servico} +{self.quantidade}"
