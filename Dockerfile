# 1. Base Image
FROM python:3.12-slim

# 2. Set Environment Variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:${PATH}"

# 3. Set Working Directory
WORKDIR /app

# 4. Install system dependencies (curl for uv installation)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# 5. Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# 6. Copy Dependency Files
# Copying these first leverages Docker's layer caching.
COPY pyproject.toml ./
COPY dia/pyproject.toml ./dia/pyproject.toml
COPY dia/LICENSE ./dia/LICENSE
COPY dia/README.md ./dia/README.md
# If you have a uv.lock file, you should copy it here as well
# COPY uv.lock ./

# 7. Install Dependencies
# This creates a virtual environment in /app/.venv and installs dependencies into it.
RUN uv venv && \
    uv pip install --no-cache -e .[dev] -e dia

# 8. Copy Application Code
# Copy the rest of your application's code
COPY . .

# 9. Expose Port
# Expose the port that the FastAPI application will run on
EXPOSE 8058

# 10. Run Application
# Command to run the Uvicorn server
CMD ["uvicorn", "agent.api:app", "--host", "0.0.0.0", "--port", "8058"]
