FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY server.py engine.py docker_start.py ./
COPY web ./web
COPY data/source.json ./data/source.json
RUN useradd --create-home --uid 10001 arriva && mkdir -p /var/lib/arriva && chown -R arriva:arriva /app /var/lib/arriva
EXPOSE 8080
CMD ["python", "docker_start.py"]
