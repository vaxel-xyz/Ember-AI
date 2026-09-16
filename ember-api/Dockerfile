FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY ember_api ./ember_api
RUN pip install --no-cache-dir . && useradd -m -u 1000 ember
USER ember
ENV EMBER_SERVICES_DIR=/app/services
EXPOSE 3002
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3002/api/health', timeout=4)"
CMD ["uvicorn", "ember_api.main:app", "--host", "0.0.0.0", "--port", "3002"]
