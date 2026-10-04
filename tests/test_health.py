"""Testes do endpoint /health."""

from fastapi.testclient import TestClient

from ai_jobs_radar.main import app

# O TestClient sobe o app em memória: nenhuma porta de rede é aberta e o
# uvicorn não entra na jogada. É o httpx (dependência de dev) que faz o
# transporte internamente — por isso ele está em [dev] no pyproject.
client = TestClient(app)


def test_health_retorna_200():
    """O endpoint responde, e responde com sucesso."""
    resposta = client.get("/health")
    assert resposta.status_code == 200


def test_health_retorna_status_ok():
    """O corpo é exatamente o contrato combinado — nada a mais, nada a menos."""
    resposta = client.get("/health")
    assert resposta.json() == {"status": "ok"}
