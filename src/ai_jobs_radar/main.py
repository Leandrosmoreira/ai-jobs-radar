"""Ponto de entrada da API.

Rodar em dev:  uvicorn ai_jobs_radar.main:app --reload
Docs automáticas: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI

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
    return {"status": "ok"}


# Próximo endpoint (depois que o modelo Vaga existir):
#
# @app.get("/vagas", response_model=list[Vaga])
# def listar_vagas() -> list[Vaga]:
#     ...
