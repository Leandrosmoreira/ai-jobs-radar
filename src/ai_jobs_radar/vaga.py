"""Modelo de domínio: uma vaga de AI Engineer."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

# Literal fecha o conjunto de valores aceitos: qualquer outra string vira
# ValidationError. Alias separado porque dá pra reusar em filtros de endpoint.
Senioridade = Literal["junior", "pleno", "senior", "staff", "principal"]


class Vaga(BaseModel):
    # Obrigatórios primeiro, opcionais depois — o Pydantic não exige essa
    # ordem (ao contrário de dataclass), mas facilita a leitura.
    titulo: str = Field(description="Título da vaga como publicado.")
    empresa: str
    url: HttpUrl = Field(description="Link para a vaga original.")
    remoto: bool
    requisitos: list[str] = Field(
        description='Tecnologias pedidas, normalizadas: ["python", "rag"].'
    )
    coletada_em: datetime

    # `| None = None` → o campo é opcional E aceita null.
    # Só `| None` (sem o `= None`) deixaria o campo obrigatório, exigindo que
    # você passasse None na mão. Era esse o bug.
    localizacao: str | None = None
    senioridade: Senioridade | None = None
    publicada_em: date | None = None
