# Carvalhos Hub

Vitrine pública e central de gestão da Carvalhos (loja do Mercado Livre). Projeto de Web III (Django).

- Público: Home, Quem Somos (equipe vinda do Supabase), Produtos (banco local + API externa), Contato, Entrar.
- Logado: Dashboard com Editar Perfil, Contatos, Produtos, Equipe, Meus Pedidos e Relatórios.
- Carvalhos: preço de custo e de venda, estoque e estoque mínimo, custos fixos e variáveis, ponto de equilíbrio, entrada de estoque em lote (tela e CSV) e exportação para Excel.
- Admin entra direto em `/admin/`; cliente vai para o Dashboard.

## Rodar local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # preencha SUPABASE_URL e SUPABASE_KEY
python manage.py migrate
python manage.py seed_demo --usuarios   # dados de exemplo + admin/cliente de teste
python manage.py runserver
python manage.py test
```

## Supabase (banco remoto da Equipe)

1. Rode `docs/supabase.sql` no SQL Editor.
2. Em Project Settings > API copie a Project URL e a chave `service_role`.
3. Coloque em `SUPABASE_URL` e `SUPABASE_KEY`. A chave fica só no servidor, nunca no Git.

## Deploy no Railway

1. Novo projeto a partir deste repositório e adicione o plugin PostgreSQL.
2. Variáveis: `SECRET_KEY` (longa e aleatória), `DATABASE_URL` (referência ao Postgres do Railway), `SUPABASE_URL`, `SUPABASE_KEY`. `DEBUG` fica ausente ou 0.
3. Para manter as imagens enviadas, crie um Volume em `/data` e defina `MEDIA_ROOT=/data/media`.
4. O `Procfile` já migra, coleta estáticos e inicia o gunicorn. Depois: `railway run python manage.py createsuperuser` e `railway run python manage.py seed_demo`.
5. Gere o domínio público; `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` leem `RAILWAY_PUBLIC_DOMAIN` sozinhos.

## Fase 2 (fora da entrega)

Projeção de vendas, chatbot com IA e sincronização com a API do Mercado Livre (OAuth). O campo `link_ml` do produto já guarda o anúncio.
