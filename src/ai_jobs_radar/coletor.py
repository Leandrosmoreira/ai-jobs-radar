"""Coletor de vagas: busca vagas na API pública do Greenhouse.

API usada (pública, sem autenticação):
    GET https://boards-api.greenhouse.io/v1/boards/{empresa}/jobs
    → {"jobs": [{"id", "title", "absolute_url", "location": {"name"}, ...}],
       "meta": {"total": N}}
    Empresa inexistente → 404.

Por que async aqui?
    Buscar vaga é 99% ESPERA: o programa manda o pedido e fica parado ~0,4s
    até a resposta voltar pela rede. Com `async`, enquanto um pedido espera,
    o Python dispara os outros. Buscar 5 empresas leva ~0,4s em vez de ~2s.

    Analogia: um garçom (o event loop) atendendo 5 mesas. Ele anota o pedido
    da mesa 1, entrega na cozinha e — em vez de ficar parado olhando o fogão —
    vai anotar a mesa 2. `await` é o "vou fazer outra coisa enquanto isso".
"""

import asyncio  # você vai usar no buscar_varias

import httpx

GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{empresa}/jobs"


class EmpresaNaoEncontrada(Exception):
    """A empresa não tem quadro de vagas no Greenhouse (a API devolveu 404)."""


async def buscar_vagas_greenhouse(client: httpx.AsyncClient, empresa: str) -> list[dict]:
    """Busca as vagas abertas de UMA empresa no Greenhouse.

    Recebe o `client` pronto em vez de criar um: abrir conexão custa caro, e
    um client reaproveitado mantém a conexão aberta entre pedidos. Isso também
    facilita os testes, que passam um client falso.

    Retorna a lista crua de `jobs` da API.
    Levanta `EmpresaNaoEncontrada` se a API responder 404.
    """
    url = GREENHOUSE_URL.format(empresa=empresa)
    resposta = await client.get(url)
    if resposta.status_code == 404:
        raise EmpresaNaoEncontrada(empresa)
    resposta.raise_for_status()
    return resposta.json()["jobs"]


    raise NotImplementedError



async def buscar_varias(client: httpx.AsyncClient, empresas: list[str]) -> dict[str, int]:
    """Busca várias empresas AO MESMO TEMPO e retorna {empresa: qtd_de_vagas}.

    Empresa inexistente entra com -1, sem derrubar as outras.
    """
    # gather dispara todas as buscas de uma vez e espera todas juntas.
    # return_exceptions=True: um erro vira ITEM da lista em vez de ser
    # levantado — assim uma empresa inexistente não cancela as outras.
    resultados = await asyncio.gather(
        *(buscar_vagas_greenhouse(client, e) for e in empresas),
        return_exceptions=True,
    )

    resultado = {}
    # gather devolve na mesma ordem de `empresas`, então o zip casa os pares.
    for empresa, r in zip(empresas, resultados):
        if isinstance(r, EmpresaNaoEncontrada):
            resultado[empresa] = -1
        elif isinstance(r, BaseException):
            raise r  # erro desconhecido (500, timeout) não pode virar -1
        else:
            resultado[empresa] = len(r)
    return resultado
