"""Ponto de entrada da API.

Rodar em dev:  uvicorn ai_jobs_radar.main:app --reload
Docs automáticas: http://127.0.0.1:8000/docs
"""

import time
from collections.abc import AsyncIterator
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query

from ai_jobs_radar.coletor import EmpresaNaoEncontrada, buscar_vagas_greenhouse, buscar_varias

# Os metadados abaixo alimentam o /docs (Swagger) e o /openapi.json.
app = FastAPI(
    title="AI Jobs Radar",
    description="Coleta vagas de AI Engineer e extrai os requisitos pedidos pelo mercado.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe: 200 significa que o processo subiu e responde.

    Usado pelo Docker (HEALTHCHECK) e pelo CI como smoke test.
    """
    # Por que `def` e não `async def` aqui? Não há nada para esperar: a função
    # só devolve um dict. O FastAPI roda `def` numa threadpool e `async def`
    # direto no event loop — os dois funcionam. A regra prática:
    #   - vai fazer `await` (rede, banco)?           → async def
    #   - vai chamar biblioteca bloqueante (requests,
    #     time.sleep, driver de banco síncrono)?     → def
    #   - async def + chamada bloqueante = trava o servidor INTEIRO.
    return {"status": "ok"}


async def get_http_client() -> AsyncIterator[httpx.AsyncClient]:
    """Dependency: entrega um AsyncClient e o fecha no fim do request.

    `async with` garante que as conexões são fechadas mesmo se der erro.
    Nos testes, `app.dependency_overrides` troca isto por um client falso —
    nenhum teste bate na internet de verdade.

    Próximo passo (quando o app crescer): um client único criado no
    `lifespan` do app, reaproveitado entre requests.
    """
    timeout = httpx.Timeout(20.0, connect=10.0)
    headers = {"User-Agent": "ai-jobs-radar/0.1 (projeto de estudo)"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        yield client


Client = Annotated[httpx.AsyncClient, Depends(get_http_client)]


@app.get("/vagas/greenhouse/{empresa}")
async def vagas_de_uma_empresa(empresa: str, client: Client) -> dict:
    """Vagas abertas de uma empresa no Greenhouse. Ex.: /vagas/greenhouse/anthropic"""
    try:
        vagas = await buscar_vagas_greenhouse(client, empresa)
    except EmpresaNaoEncontrada:
        raise HTTPException(404, f"empresa '{empresa}' não encontrada no Greenhouse")
    except httpx.HTTPError:
        # Timeout, 5xx, rede caída: o problema é a fonte, não o pedido → 502.
        raise HTTPException(502, "Greenhouse indisponível, tente de novo")

    return {
        "empresa": empresa,
        "total": len(vagas),
        # Só 10 títulos: a resposta crua tem centenas de vagas.
        "exemplos": [v["title"] for v in vagas[:10]],
    }


@app.get("/vagas/contagem")
async def contagem_por_empresa(
    client: Client,
    empresas: Annotated[list[str], Query(max_length=10)] = ["anthropic", "airbnb"],
) -> dict:
    """Conta vagas de várias empresas em paralelo e mede o tempo.

    Ex.: /vagas/contagem?empresas=anthropic&empresas=airbnb&empresas=stripe

    O campo `segundos` é o experimento: compare a versão sequencial com a
    versão com asyncio.gather no seu buscar_varias.
    """
    inicio = time.perf_counter()
    try:
        contagem = await buscar_varias(client, empresas)
    except httpx.HTTPError:
        raise HTTPException(502, "Greenhouse indisponível, tente de novo")
    return {"contagem": contagem, "segundos": round(time.perf_counter() - inicio, 2)}


# Próximo endpoint (depois que o modelo Vaga existir):
#
# @app.get("/vagas", response_model=list[Vaga])
# def listar_vagas() -> list[Vaga]:
#     ...
