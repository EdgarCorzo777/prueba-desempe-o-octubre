FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt /app/requirements.txt
# Instalacion resiliente a redes inestables: reintentos con timeout extendido
# y caida a un espejo de PyPI si pypi.org falla (ej. proxy/firewall en Windows)
RUN python -m pip install --no-cache-dir --timeout 120 --retries 3 -r requirements.txt \
    || python -m pip install --no-cache-dir --timeout 120 --retries 3 \
        -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# Copy API and Airflow include modules for shared logic
COPY api/ /app/api/
COPY airflow/ /app/airflow/
COPY spark/ /app/spark/

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
