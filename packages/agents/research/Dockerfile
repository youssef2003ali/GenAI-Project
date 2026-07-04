FROM python:3.11-slim
WORKDIR /app

# Install Node.js (needed for the open-websearch MCP server via npx)
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install uv && uv sync
CMD ["uv", "run", "python", "-m", "research.server"]