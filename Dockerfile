# syntax=docker/dockerfile:1

FROM python:3.12-slim

# Instala git (essencial para o dbt)
RUN apt-get update \
    && apt-get install -y git \
    && rm -rf /var/lib/apt/lists/*

    
    # Instala o uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Sincronizar a .venv do root e runtime
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

# Evita que o Python gere .pyc e força logs imediatos
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copia apenas os arquivos de dependências primeiro
# para aproveitar o cache do Docker
COPY pyproject.toml uv.lock ./

# Instala as dependências sem instalar o projeto
RUN uv sync --frozen --no-install-project

# Agora copia o código
COPY . .

# Instala o projeto
RUN uv sync --frozen

# Executa a aplicação usando o ambie criado pelo uv
CMD ["uv", "run", "dbt", "debug"]