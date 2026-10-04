"""Modelos de domínio do AI Jobs Radar.

=============================================================================
ESTE ARQUIVO É SEU. O modelo `Vaga` está deliberadamente vazio.
=============================================================================

Objetivo: representar uma vaga de AI Engineer com validação automática,
para que dado sujo (vindo de scraping/API) nunca entre na aplicação.

Roteiro sugerido:

1. Importe o que precisar:
       from pydantic import BaseModel, Field, HttpUrl

2. Crie `class Vaga(BaseModel):` com campos candidatos:
       titulo: str
       empresa: str
       localizacao: str | None      # None = não informado pela fonte
       remoto: bool
       senioridade: ...             # bom caso para um Enum / Literal
       requisitos: list[str]        # ex.: ["python", "rag", "docker"]
       url: HttpUrl                 # Pydantic valida que é uma URL de verdade
       publicada_em: date | None
       coletada_em: datetime

3. Decida, para cada campo, três coisas:
       - é obrigatório ou tem default?
       - o tipo certo já valida sozinho? (HttpUrl, EmailStr, PositiveInt...)
       - precisa de restrição extra? (Field(min_length=1), Field(ge=0)...)

Pontos que valem experimentar enquanto aprende Pydantic v2:

  - `Field(..., description="...")` aparece no /docs automaticamente.
  - `model_config = ConfigDict(extra="forbid")` rejeita campos desconhecidos —
    útil pra detectar quando a fonte de dados mudou de formato.
  - `@field_validator("requisitos")` para normalizar (lowercase, deduplicar).
  - `Vaga.model_validate(dict_cru)` é como você valida dado externo;
    `vaga.model_dump(mode="json")` é como você serializa de volta.
  - Campo ausente na fonte deve virar `None` explícito, nunca string vazia
    ou valor inventado.

Quando o modelo estiver pronto, importe-o em main.py e troque o
endpoint /vagas comentado por um de verdade.
"""
from pydantic import BaseModel, Field, HttpUrl

class Vaga(BaseModel):
       titulo: str
       empresa: str
       localizacao: str | None      # None = não informado pela fonte
       remoto: bool
       senioridade: ...             # bom caso para um Enum / Literal
       requisitos: list[str]        # ex.: ["python", "rag", "docker"]
       url: HttpUrl                 # Pydantic valida que é uma URL de verdade
       publicada_em: date | None
       coletada_em: datetime