"""Cliente do Supabase (banco remoto da Equipe).

Criado sob demanda: se as variaveis nao estiverem configuradas o site
continua no ar e apenas a pagina da equipe avisa o problema.
"""
import logging
import os

logger = logging.getLogger(__name__)
_client = None


class EquipeIndisponivel(Exception):
    """Banco remoto fora do ar ou sem configuracao."""


def get_client():
    global _client
    if _client is None:
        url, chave = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
        if not url or not chave:
            raise EquipeIndisponivel("SUPABASE_URL e SUPABASE_KEY não configurados.")
        from supabase import create_client

        _client = create_client(url, chave)
    return _client


def _tabela():
    try:
        return get_client().table("integrantes")
    except EquipeIndisponivel:
        raise
    except Exception as exc:  # falha de configuração/rede
        logger.exception("Supabase indisponível")
        raise EquipeIndisponivel(str(exc)) from exc


def _executar(consulta):
    try:
        return consulta.execute().data
    except Exception as exc:
        logger.exception("Erro ao consultar o Supabase")
        raise EquipeIndisponivel(str(exc)) from exc


def listar_integrantes():
    return _executar(_tabela().select("*").order("id")) or []


def obter_integrante(id_integrante):
    dados = _executar(_tabela().select("*").eq("id", id_integrante))
    return dados[0] if dados else None


def criar_integrante(dados):
    return _executar(_tabela().insert(dados))


def atualizar_integrante(id_integrante, dados):
    return _executar(_tabela().update(dados).eq("id", id_integrante))


def excluir_integrante(id_integrante):
    return _executar(_tabela().delete().eq("id", id_integrante))
