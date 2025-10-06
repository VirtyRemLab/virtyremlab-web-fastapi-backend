# ─────────────────────────────────────────────────────────────
# Imagen ligera de Python para producción
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Evita .pyc y fuerza salida sin buffer (logs en tiempo real)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Instalamos dependencias del sistema mínimas
# (ca-certificates TLS hacia fuera)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# ─────────────────────────────────────────────────────────────
# Instala dependencias de Python
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# Copiamos el código de la app 
COPY ./main.py /app/main.py

# ─────────────────────────────────────────────────────────────
# Exponemos puertos:
#  - 8000: FastAPI (HTTP)
#  - 8765: WebSocket para el ESP32 (servidor websockets.serve)
# ─────────────────────────────────────────────────────────────
EXPOSE 8002

#  Uvicorn con UN SOLO worker.
# Con varios workers, cada uno intentaría abrir el 8765 → "address already in use".
CMD ["uvicorn", "main:socket_app", "--host", "0.0.0.0", "--port", "8002", "--workers", "1"]
