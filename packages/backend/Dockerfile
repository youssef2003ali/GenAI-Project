FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync
CMD ["uv", "run", "uvicorn", "packages.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
