FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy API and Airflow include modules for shared logic
COPY api/ /app/api/
COPY airflow/ /app/airflow/
COPY spark/ /app/spark/

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
