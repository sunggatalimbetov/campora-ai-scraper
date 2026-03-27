FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---

FROM python:3.12-slim

COPY --from=builder /install /usr/local

RUN groupadd --gid 1000 scraper \
    && useradd --uid 1000 --gid scraper --shell /bin/false scraper

WORKDIR /app

COPY src/ src/
COPY scripts/ scripts/
COPY main.py pyproject.toml ./

USER scraper

CMD ["python", "main.py"]
