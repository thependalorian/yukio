# Yukio Development Setup Guide

This guide covers how to set up a development environment for the Yukio project. The project uses `uv` for fast package management and `pyproject.toml` for dependency definition.

## 1. Prerequisites

### Python Version
- The project requires **Python 3.10, 3.11, or 3.12**.
- It is highly recommended to manage your Python versions using `pyenv`.

### `uv` Installer
- The project uses `uv` for creating virtual environments and installing packages. It's an extremely fast, modern replacement for `pip` and `venv`.
- **Installation**:
  ```bash
  # macOS / Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # Windows
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- Verify the installation with `uv --version`.

## 2. Environment Setup

Follow these steps from the root of the `yukio` project directory.

### Step 1: Set Your Python Version (Recommended)

Using `pyenv`, set a compatible Python version for the project. Python 3.12 is recommended.

```bash
# Set the local python version for this directory
pyenv local 3.12.8
```

### Step 2: Create the Virtual Environment

Use `uv` to create a new virtual environment. `uv` will automatically detect the Python version set by `pyenv`.

```bash
# This will create a .venv directory
uv venv
```
If `uv` doesn't find the right Python version, you can specify it manually:
```bash
# Find your python path
pyenv which python

# Create venv with a specific python interpreter
uv venv -p /path/to/your/python
```

### Step 3: Install Dependencies

Use `uv` to install all project dependencies from `pyproject.toml` and the `dia` sub-project.

```bash
# Install the main project, dev tools, and the dia sub-project
uv pip install -e .[dev] -e dia
```
- `.` installs the `yukio-agent` project.
- `-e` installs it in "editable" mode, so your code changes are reflected immediately.
- `[dev]` installs the optional development dependencies (like `pytest`, `black`).
- `-e dia` installs the local `dia` sub-project, which is required for Text-to-Speech.

Your environment is now fully set up.

## 3. Running the Application

Ensure your virtual environment is activated. `uv` automatically detects and uses the `.venv` directory, but activating it makes running commands easier.

```bash
source .venv/bin/activate
```

### Running the CLI
To interact with Yukio via the command line:
```bash
python cli.py
```
To enable voice output (requires TTS setup):
```bash
python cli.py --voice
```

### Running the API Server
To run the FastAPI server (for the web frontend):
```bash
# Method 1: Using Python module
python -m agent.api

# Method 2: Using uvicorn directly
uvicorn agent.api:app --reload --port 8058
```

The API will be available at `http://localhost:8058`

**Note**: The frontend (`yukio-frontend`) expects the backend on port 8058. Make sure this port matches your `.env.local` configuration in the frontend.

## 4. Troubleshooting

- **`llvmlite` build error**:
  - **Error**: `RuntimeError: Cannot install on Python version X; only versions Y are supported.`
  - **Cause**: The Python version in your virtual environment is incompatible with a sub-dependency of the `dia` project.
  - **Solution**: Delete the `.venv` directory (`rm -rf .venv`) and re-create it using a compatible Python version (3.10-3.12) as shown in Step 1 and 2.

- **`hatchling` build error**:
  - **Error**: `ValueError: Unable to determine which files to ship...`
  - **Cause**: The `pyproject.toml` is missing the `[tool.hatch.build.targets.wheel]` section that tells the builder which directories contain the source code.
  - **Solution**: Ensure your `pyproject.toml` contains:
    ```toml
    [tool.hatch.build.targets.wheel]
    packages = ["agent"]
    ```

- **Command `uv` not found**:
  - **Cause**: `uv` is not installed or not in your system's PATH.
  - **Solution**: Follow the installation instructions in the Prerequisites section.
