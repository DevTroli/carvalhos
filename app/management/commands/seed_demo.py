"""Dados de exemplo para a apresentação: python manage.py seed_demo"""
from datetime import date

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from app.models import Categoria, Custo, Servico
from login.models import Perfil

PRODUTOS = [
    ("Tábua de Corte Carvalho", "Tábua maciça de carvalho, 40x25 cm.", "Cozinha", "38.00", "89.90", 24, 8),
    ("Porta-Copos de Madeira (kit 6)", "Kit com 6 unidades, acabamento natural.", "Casa", "12.50", "34.90", 40, 15),
    ("Caixa Organizadora Artesanal", "Caixa de madeira com tampa deslizante.", "Casa", "45.00", "129.90", 6, 8),
    ("Suporte para Notebook", "Suporte ergonômico dobrável.", "Escritório", "30.00", "79.90", 18, 6),
    ("Colher de Pau Grande", "Colher artesanal de 35 cm.", "Cozinha", "6.00", "19.90", 3, 10),
]


class Command(BaseCommand):
    help = "Cria categorias, produtos, custos e usuários de exemplo (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument("--usuarios", action="store_true",
                            help="Cria também admin e cliente de teste (somente desenvolvimento).")

    def handle(self, *args, **opts):
        for nome, desc, cat, custo, venda, est, minimo in PRODUTOS:
            categoria, _ = Categoria.objects.get_or_create(nome=cat)
            Servico.objects.get_or_create(nome=nome, defaults=dict(
                descricao=desc, categoria=categoria, preco_custo=custo, preco=venda,
                estoque=est, estoque_minimo=minimo))
        if not Custo.objects.exists():
            hoje = date.today()
            Custo.objects.create(descricao="Aluguel do galpão", tipo="fixo", valor="1200", data=hoje)
            Custo.objects.create(descricao="Internet e energia", tipo="fixo", valor="380", data=hoje)
            Custo.objects.create(descricao="Embalagem", tipo="variavel", valor="2.50", data=hoje)
            Custo.objects.create(descricao="Etiqueta e fita", tipo="variavel", valor="0.80", data=hoje)
        if opts["usuarios"]:
            if not User.objects.filter(username="admin").exists():
                User.objects.create_superuser("admin", "admin@carvalhos.local", "admin12345")
            if not User.objects.filter(username="cliente").exists():
                u = User.objects.create_user("cliente", "cliente@carvalhos.local", "cliente12345", first_name="Ana")
                Perfil.objects.get_or_create(usuario=u)
            self.stdout.write("Usuários de teste: admin / admin12345 e cliente / cliente12345 (troque depois).")
        self.stdout.write(self.style.SUCCESS("Dados de exemplo prontos."))
