
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

COPY . .

EXPOSE 5000

CMD ["flask", "--app", "app", "run", "--host=0.0.0.0", "--port=5000"]
