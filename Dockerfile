FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---

FROM python:3.12-slim

COPY --from=builder /install /usr/local

RUN groupadd --gid 1000 scrapper \
    && useradd --uid 1000 --gid scrapper --shell /bin/false scrapper

WORKDIR /app

COPY src/ src/
COPY scripts/ scripts/
COPY main.py pyproject.toml ./

USER scrapper

CMD ["python", "main.py"]
