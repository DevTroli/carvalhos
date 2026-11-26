-- Rode no SQL Editor do Supabase.
create table if not exists public.integrantes (
  id bigint generated always as identity primary key,
  nome text not null,
  cargo text not null,
  biografia text,
  foto_url text
);

-- RLS ligado e sem politicas: so a chave service_role (usada no servidor Django) acessa.
alter table public.integrantes enable row level security;

insert into public.integrantes (nome, cargo, biografia, foto_url) values
('Mariana', 'QA', 'Responsável pela qualidade do projeto', ''),
('Felipe', 'Desenvolvedor', 'Responsável pelo desenvolvimento do projeto', ''),
('Juliano', 'Desenvolvedor', 'Responsável pelo desenvolvimento do projeto', '');
