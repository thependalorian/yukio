# GitHub Actions Workflows

This directory contains CI/CD workflows for the Yukio Backend.

## Workflows

### `ci.yml`
Main CI pipeline that runs on every push and pull request:
- **Lint**: Runs Black, isort, and Flake8 for code quality
- **Type Check**: Validates Python types with mypy
- **Test**: Runs pytest with coverage reporting
- **Security**: Scans dependencies with Safety

### `deploy.yml`
Deployment workflow that runs on pushes to `main`:
- **Docker Build**: Builds and pushes Docker image to Docker Hub
- **Railway Deploy**: Deploys to Railway (optional)

### `code-quality.yml`
Code quality checks for pull requests:
- **Format Check**: Ensures code follows Black and isort formatting
- **Complexity Check**: Analyzes code complexity with Radon

### `dependency-review.yml`
Security workflow that reviews dependencies:
- **Dependency Review**: Checks for known vulnerabilities in Python packages

## Required Secrets

For deployment to work, add these secrets in GitHub Settings > Secrets:

- `DOCKER_USERNAME`: Docker Hub username
- `DOCKER_PASSWORD`: Docker Hub password or access token
- `RAILWAY_TOKEN`: Railway deployment token (optional)

## Environment Variables

The following environment variables are used in tests (set in GitHub Secrets if needed):
- `OLLAMA_BASE_URL`: Ollama API URL (default: http://localhost:11434)
- `EMBEDDING_MODEL`: Embedding model name (default: nomic-embed-text)
- `LLM_MODEL`: LLM model name (default: llama3.2)

## Usage

Workflows run automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`
- Manual trigger via `workflow_dispatch`

