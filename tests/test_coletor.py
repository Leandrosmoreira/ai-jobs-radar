"""Testes do coletor async — sem internet.

`httpx.MockTransport` troca a rede por uma função nossa: o client acha que
falou com o Greenhouse, mas quem respondeu foi `greenhouse_falso`.

`@pytest.mark.anyio` faz o pytest rodar testes `async def`. O plugin vem
com o anyio, que já é dependência do FastAPI — por isso não há pytest-asyncio.
"""

import asyncio
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from ai_jobs_radar.coletor import EmpresaNaoEncontrada, buscar_vagas_greenhouse, buscar_varias
from ai_jobs_radar.main import app, get_http_client

# Formato real da API (conferido em boards-api.greenhouse.io), só os campos usados.
VAGAS_FALSAS = {
    "anthropic": [
        {"id": 1, "title": "AI Engineer", "absolute_url": "https://x/1"},
        {"id": 2, "title": "ML Engineer", "absolute_url": "https://x/2"},
    ],
    "airbnb": [{"id": 3, "title": "Data Scientist", "absolute_url": "https://x/3"}],
}

ATRASO_S = 0.3  # cada resposta falsa demora isso, para medir concorrência


async def greenhouse_falso(request: httpx.Request) -> httpx.Response:
    """Imita a API: /v1/boards/{empresa}/jobs. 'quebrada' simula pane do servidor."""
    await asyncio.sleep(ATRASO_S)  # sleep ASYNC: libera o event loop
    empresa = request.url.path.split("/")[3]
    if empresa == "quebrada":
        return httpx.Response(500)
    if empresa not in VAGAS_FALSAS:
        return httpx.Response(404)
    jobs = VAGAS_FALSAS[empresa]
    return httpx.Response(200, json={"jobs": jobs, "meta": {"total": len(jobs)}})


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.MockTransport(greenhouse_falso)) as c:
        yield c


# --- buscar_vagas_greenhouse -------------------------------------------------


@pytest.mark.anyio
async def test_retorna_as_vagas_da_empresa(client):
    vagas = await buscar_vagas_greenhouse(client, "anthropic")
    assert [v["title"] for v in vagas] == ["AI Engineer", "ML Engineer"]


@pytest.mark.anyio
async def test_404_vira_empresa_nao_encontrada(client):
    with pytest.raises(EmpresaNaoEncontrada):
        await buscar_vagas_greenhouse(client, "nao-existe")


@pytest.mark.anyio
async def test_500_vira_erro_http(client):
    """Erro do servidor NÃO pode ser confundido com 'empresa não existe'."""
    with pytest.raises(httpx.HTTPStatusError):
        await buscar_vagas_greenhouse(client, "quebrada")


# --- buscar_varias -----------------------------------------------------------


@pytest.mark.anyio
async def test_conta_vagas_por_empresa(client):
    contagem = await buscar_varias(client, ["anthropic", "airbnb"])
    assert contagem == {"anthropic": 2, "airbnb": 1}


@pytest.mark.anyio
async def test_empresa_inexistente_vira_menos_um(client):
    """Uma empresa inexistente não derruba as outras."""
    contagem = await buscar_varias(client, ["anthropic", "nao-existe"])
    assert contagem == {"anthropic": 2, "nao-existe": -1}


@pytest.mark.anyio
async def test_erro_desconhecido_sobe(client):
    """Um 500 não pode virar -1: isso seria dado errado silencioso."""
    with pytest.raises(httpx.HTTPStatusError):
        await buscar_varias(client, ["anthropic", "quebrada"])


@pytest.mark.anyio
async def test_busca_e_concorrente(client):
    """O teste que prova o async: 3 empresas × 0,3s cada.

    Sequencial → ~0,9s.  Com asyncio.gather → ~0,3s (todas esperam juntas).
    Se este teste falha mas os outros passam, seu buscar_varias está com o
    `for ... await` em vez do gather.
    """
    inicio = time.perf_counter()
    await buscar_varias(client, ["anthropic", "airbnb", "nao-existe"])
    duracao = time.perf_counter() - inicio
    assert duracao < ATRASO_S * 2, f"levou {duracao:.2f}s — está sequencial?"


# --- endpoints ---------------------------------------------------------------


async def client_falso():
    async with httpx.AsyncClient(transport=httpx.MockTransport(greenhouse_falso)) as c:
        yield c


@pytest.fixture
def api():
    # dependency_overrides: no lugar do get_http_client real, o FastAPI usa o falso.
    app.dependency_overrides[get_http_client] = client_falso
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_endpoint_uma_empresa(api):
    r = api.get("/vagas/greenhouse/anthropic")
    assert r.status_code == 200
    assert r.json() == {"empresa": "anthropic", "total": 2, "exemplos": ["AI Engineer", "ML Engineer"]}


def test_endpoint_empresa_inexistente_da_404(api):
    r = api.get("/vagas/greenhouse/nao-existe")
    assert r.status_code == 404


def test_endpoint_fonte_fora_do_ar_da_502(api):
    r = api.get("/vagas/greenhouse/quebrada")
    assert r.status_code == 502


def test_endpoint_contagem(api):
    r = api.get("/vagas/contagem", params={"empresas": ["anthropic", "airbnb"]})
    assert r.status_code == 200
    assert r.json()["contagem"] == {"anthropic": 2, "airbnb": 1}
