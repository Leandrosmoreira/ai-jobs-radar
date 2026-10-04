"""Testes do modelo Vaga."""

import pytest
from pydantic import ValidationError

from ai_jobs_radar.vaga import Vaga

# Payload mínimo válido: contém só os campos obrigatórios. Cada teste parte
# daqui e altera UMA coisa — assim a falha aponta para a causa.
PAYLOAD_VALIDO = {
    "titulo": "AI Engineer",
    "empresa": "Acme",
    "url": "https://acme.com/jobs/1",
    "remoto": True,
    "requisitos": ["python", "rag"],
    "coletada_em": "2026-10-03T12:00:00Z",
}

OBRIGATORIOS = ["titulo", "empresa", "url", "remoto", "requisitos", "coletada_em"]


def test_payload_valido_cria_vaga():
    # model_validate é como se valida dado externo (dict vindo de uma API).
    vaga = Vaga.model_validate(PAYLOAD_VALIDO)
    assert vaga.titulo == "AI Engineer"


def test_strings_sao_convertidas_nos_tipos_certos():
    """O Pydantic faz o parse: string ISO entra, datetime/date/HttpUrl sai."""
    vaga = Vaga.model_validate(PAYLOAD_VALIDO | {"publicada_em": "2026-10-01"})
    assert vaga.coletada_em.year == 2026
    assert vaga.publicada_em.day == 1


def test_opcionais_ausentes_viram_none():
    """O bug que corrigimos: opcional ausente não deve quebrar a validação."""
    vaga = Vaga.model_validate(PAYLOAD_VALIDO)
    assert vaga.localizacao is None
    assert vaga.senioridade is None
    assert vaga.publicada_em is None


# parametrize roda o mesmo corpo de teste uma vez por valor, e cada um aparece
# como um teste separado na saída do pytest.
@pytest.mark.parametrize("campo", OBRIGATORIOS)
def test_campo_obrigatorio_ausente_falha(campo):
    payload = {k: v for k, v in PAYLOAD_VALIDO.items() if k != campo}

    with pytest.raises(ValidationError) as erro:
        Vaga.model_validate(payload)

    # Não basta falhar: tem que falhar apontando o campo certo.
    assert erro.value.errors()[0]["loc"] == (campo,)


def test_url_invalida_falha():
    with pytest.raises(ValidationError):
        Vaga.model_validate(PAYLOAD_VALIDO | {"url": "nao-e-url"})


def test_senioridade_fora_do_literal_falha():
    with pytest.raises(ValidationError):
        Vaga.model_validate(PAYLOAD_VALIDO | {"senioridade": "ceo"})


@pytest.mark.parametrize("nivel", ["junior", "pleno", "senior", "staff", "principal"])
def test_senioridade_valida_e_aceita(nivel):
    vaga = Vaga.model_validate(PAYLOAD_VALIDO | {"senioridade": nivel})
    assert vaga.senioridade == nivel
