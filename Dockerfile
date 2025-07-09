FROM python:3.11-slim

# Install uv
RUN pip install --upgrade uv

WORKDIR /app
COPY . /app

# Install dependencies globally with uv pip
RUN uv pip install --system -e .

# Expose the port (default is 3000)
EXPOSE 3000

# Run the server directly
CMD ["python", "mcp_search_server.py"] 