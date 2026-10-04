# ============================================================================
# Estágio 1: build — instala tudo num venv isolado.
# Esta imagem é gorda (tem compilador, cache do pip) e NÃO vai pra produção.
# ============================================================================
FROM python:3.12-slim AS builder

# O venv em /opt/venv existe para ser copiado inteiro no estágio final.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Ordem das camadas: metadados e código antes do install.
# Nota: o hatchling precisa do src/ presente para construir o pacote, então
# aqui não dá pra cachear "só as dependências". Num projeto maior você geraria
# um requirements.txt (ou usaria `uv lock`) e instalaria as deps numa camada
# separada — aí mudar o código não reinstalaria o FastAPI inteiro.
COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

# ============================================================================
# Estágio 2: runtime — só o venv pronto. Sem pip cache, sem código-fonte.
# ============================================================================
FROM python:3.12-slim

# Usuário sem privilégios: se alguém escapar da aplicação, não cai como root.
RUN useradd --create-home --uid 1000 app

COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER app
WORKDIR /home/app

EXPOSE 8000

# Reusa o /health. python já está na imagem, então não precisa instalar curl.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status == 200 else 1)"

# 0.0.0.0 e não 127.0.0.1: dentro do container, localhost não é alcançável
# de fora. Esse é o erro nº 1 de quem containeriza web app pela primeira vez.
CMD ["uvicorn", "ai_jobs_radar.main:app", "--host", "0.0.0.0", "--port", "8000"]
