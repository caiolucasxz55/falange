FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias primeiro: essa camada so reconstroi quando requirements muda.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Nao roda como root.
RUN useradd --create-home --uid 1000 falange && chown -R falange:falange /app
USER falange

EXPOSE 8000 8765

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
