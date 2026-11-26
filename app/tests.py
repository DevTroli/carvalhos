from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from login.models import Perfil

from . import services, supabase_client as equipe
from .models import Categoria, Contato, Custo, EntradaEstoque, Pedido, Servico

EQUIPE = [{"id": 1, "nome": "Mariana", "cargo": "QA", "biografia": "x", "foto_url": ""}]


class Base(TestCase):
    def setUp(self):
        self.cliente = User.objects.create_user("ana", "ana@x.com", "senha-forte-123")
        Perfil.objects.create(usuario=self.cliente)
        self.admin = User.objects.create_superuser("root", "r@x.com", "senha-forte-123")
        self.prod = Servico.objects.create(nome="Tábua", preco="90", preco_custo="40", estoque=5, estoque_minimo=2)


class PublicoETestes(Base):
    def test_paginas_publicas(self):
        with mock.patch("app.views.equipe.listar_integrantes", return_value=EQUIPE), \
             mock.patch("app.views.produtos_parceiros", return_value=([], False)):
            for nome in ("index", "quem_somos", "produtos", "add_contato", "login", "cadastro", "password_reset"):
                self.assertEqual(self.client.get(reverse(nome)).status_code, 200, nome)

    def test_quem_somos_sobrevive_sem_supabase(self):
        with mock.patch("app.views.equipe.listar_integrantes", side_effect=equipe.EquipeIndisponivel):
            r = self.client.get(reverse("quem_somos"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Não foi possível carregar a equipe")

    def test_contato_sem_login(self):
        r = self.client.post(reverse("add_contato"), {"nome": "Z", "email": "z@z.com", "telefone": "", "mensagem": "oi"}, follow=True)
        self.assertEqual(Contato.objects.count(), 1)
        self.assertContains(r, "Mensagem enviada")

    def test_menu_publico_e_logado(self):
        r = self.client.get(reverse("index"))
        self.assertContains(r, "Entrar")
        self.assertNotContains(r, "Sair")
        self.client.force_login(self.cliente)
        r = self.client.get(reverse("index"))
        self.assertContains(r, "Dashboard")
        self.assertContains(r, "Sair")


class Acesso(Base):
    def test_gestao_exige_login(self):
        for nome in ("servicos", "addServicos", "contatos", "integrantes", "relatorios", "pedidos",
                     "entrada_estoque", "custos", "exportar_excel", "dashboard", "perfil"):
            r = self.client.get(reverse(nome))
            self.assertEqual(r.status_code, 302, nome)
            self.assertIn("/login/", r["Location"], nome)

    def test_exclusao_so_por_post(self):
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(reverse("delServicos", args=[self.prod.id])).status_code, 405)

    def test_redirecionamento_por_perfil(self):
        r = self.client.post(reverse("login"), {"username": "root", "password": "senha-forte-123"})
        self.assertRedirects(r, "/admin/", fetch_redirect_response=False)
        self.client.logout()
        r = self.client.post(reverse("login"), {"username": "ana", "password": "senha-forte-123"})
        self.assertRedirects(r, "/login/dashboard/", fetch_redirect_response=False)

    def test_admin_sem_perfil_nao_quebra_dashboard(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_logout_por_post(self):
        self.client.force_login(self.cliente)
        r = self.client.post(reverse("logout"))
        self.assertEqual(r.status_code, 302)

    def test_recuperar_senha_envia_email(self):
        from django.core import mail
        self.client.post(reverse("password_reset"), {"email": "ana@x.com"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/login/redefinir/", mail.outbox[0].body)

    def test_cadastro_cria_cliente(self):
        r = self.client.post(reverse("cadastro"), {"username": "novo", "email": "n@n.com",
                            "password1": "uma-senha-boa-987", "password2": "uma-senha-boa-987"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Perfil.objects.get(usuario__username="novo").tipo_usuario, "cliente")


class Pedidos(Base):
    def test_comprar_exige_login(self):
        r = self.client.post(reverse("comprar", args=[self.prod.id]))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Pedido.objects.count(), 0)

    def test_comprar_e_meus_pedidos(self):
        self.client.force_login(self.cliente)
        self.client.post(reverse("comprar", args=[self.prod.id]))
        self.client.post(reverse("comprar", args=[self.prod.id]))
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.estoque, 3)
        r = self.client.get(reverse("pedidos"))
        self.assertContains(r, "Tábua")
        self.assertEqual(r.context["total"], Decimal("180"))

    def test_botao_comprar_so_logado(self):
        with mock.patch("app.views.produtos_parceiros", return_value=([], False)):
            self.assertNotContains(self.client.get(reverse("produtos")), ">Comprar<")
            self.client.force_login(self.cliente)
            self.assertContains(self.client.get(reverse("produtos")), "Comprar")


class Produtos(Base):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.cliente)

    def test_crud(self):
        dados = {"nome": "Colher", "descricao": "", "preco_custo": "5", "preco": "20", "estoque": 3,
                 "estoque_minimo": 1, "link_ml": "", "ativo": "on"}
        self.assertEqual(self.client.post(reverse("addServicos"), dados).status_code, 302)
        s = Servico.objects.get(nome="Colher")
        dados["nome"] = "Colher G"
        self.client.post(reverse("editServicos", args=[s.id]), dados)
        s.refresh_from_db(); self.assertEqual(s.nome, "Colher G")
        self.client.post(reverse("delServicos", args=[s.id]))
        self.assertFalse(Servico.objects.filter(id=s.id).exists())

    def test_form_vazio_sem_erros_no_get(self):
        self.assertNotContains(self.client.get(reverse("addServicos")), "Este campo é obrigatório")

    def test_preco_abaixo_do_custo_e_rejeitado(self):
        r = self.client.post(reverse("addServicos"), {"nome": "X", "preco_custo": "50", "preco": "10",
                             "estoque": 0, "estoque_minimo": 0})
        self.assertContains(r, "prejuízo")

    def test_listagem_com_filtros(self):
        r = self.client.get(reverse("servicos"), {"busca": "tá", "preco": "medio", "ordem": "margem", "estoque": "baixo"})
        self.assertEqual(r.status_code, 200)

    def test_produto_com_pedido_so_desativa(self):
        Pedido.objects.create(usuario=self.cliente, servico=self.prod, preco=90)
        self.client.post(reverse("delServicos", args=[self.prod.id]))
        self.prod.refresh_from_db(); self.assertFalse(self.prod.ativo)


class Estoque(Base):
    def test_media_ponderada(self):
        # 5 un. a R$40 + 5 un. a R$60 = R$50
        services.registrar_entradas([(self.prod, 5, Decimal("60"))])
        self.prod.refresh_from_db()
        self.assertEqual((self.prod.estoque, self.prod.preco_custo), (10, Decimal("50.00")))
        self.assertEqual(EntradaEstoque.objects.count(), 1)

    def test_tudo_ou_nada(self):
        with self.assertRaises(services.ErroEntrada):
            services.registrar_entradas([(self.prod, 5, Decimal("10")), (self.prod, 0, Decimal("10"))])
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.estoque, 5)
        self.assertEqual(EntradaEstoque.objects.count(), 0)

    def test_formulario_e_csv(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_login(self.cliente)
        self.client.post(reverse("entrada_estoque"), {"produto": [self.prod.id, ""], "quantidade": ["3", ""], "custo": ["45,50", ""]})
        self.prod.refresh_from_db(); self.assertEqual(self.prod.estoque, 8)
        csv = "produto;quantidade;custo_unitario\r\nTábua;2;40,00\r\n".encode()
        self.client.post(reverse("entrada_estoque"), {"arquivo": SimpleUploadedFile("c.csv", csv)})
        self.prod.refresh_from_db(); self.assertEqual(self.prod.estoque, 10)
        r = self.client.post(reverse("entrada_estoque"), {"produto": [self.prod.id], "quantidade": ["x"], "custo": ["1"]}, follow=True)
        self.assertContains(r, "Nada foi salvo")


class Custos(Base):
    def test_ponto_de_equilibrio(self):
        Custo.objects.create(descricao="Aluguel", tipo="fixo", valor=1000, data="2026-11-01")
        Custo.objects.create(descricao="Caixa", tipo="variavel", valor=10, data="2026-11-01")
        ind = services.indicadores_custos()
        # margem 90-40=50, menos variável 10 = 40; 1000/40 = 25
        self.assertEqual(ind["ponto_equilibrio"], 25)

    def test_relatorios_e_excel(self):
        self.client.force_login(self.cliente)
        Custo.objects.create(descricao="Aluguel", tipo="fixo", valor=1000, data="2026-11-01")
        self.assertEqual(self.client.get(reverse("relatorios")).status_code, 200)
        self.assertEqual(self.client.get(reverse("custos")).status_code, 200)
        r = self.client.get(reverse("exportar_excel"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("spreadsheetml", r["Content-Type"])


class Equipe(Base):
    def test_editar_integrante(self):
        self.client.force_login(self.cliente)
        with mock.patch("app.views.equipe.obter_integrante", return_value=EQUIPE[0]), \
             mock.patch("app.views.equipe.atualizar_integrante") as up:
            self.assertContains(self.client.get(reverse("editIntegrante", args=[1])), "Mariana")
            r = self.client.post(reverse("editIntegrante", args=[1]), {"nome": "M", "cargo": "QA", "biografia": "", "foto_url": ""})
            self.assertEqual(r.status_code, 302)
            up.assert_called_once()

    def test_api_categorias_so_equipe(self):
        self.assertIn(self.client.get("/categoria-api/").status_code, (401, 403))
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/categoria-api/").status_code, 200)
