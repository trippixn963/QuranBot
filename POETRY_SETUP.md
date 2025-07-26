# Poetry Setup Guide for QuranBot

## Installing Poetry

### macOS/Linux
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### Windows (PowerShell)
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

### Alternative: Using pip
```bash
pip install poetry
```

## Project Setup

1. **Install dependencies:**
   ```bash
   poetry install
   ```

2. **Activate virtual environment:**
   ```bash
   poetry shell
   ```

3. **Run the bot:**
   ```bash
   poetry run python main.py
   ```

## Development Commands

- **Add a new dependency:**
  ```bash
  poetry add package-name
  ```

- **Add a development dependency:**
  ```bash
  poetry add --group dev package-name
  ```

- **Update dependencies:**
  ```bash
  poetry update
  ```

- **Run tests:**
  ```bash
  poetry run pytest
  ```

- **Run code formatting:**
  ```bash
  poetry run black .
  ```

- **Run linting:**
  ```bash
  poetry run ruff check .
  ```

- **Run type checking:**
  ```bash
  poetry run mypy src/
  ```

## Migration from requirements.txt

The project has been migrated from `requirements.txt` to Poetry for better dependency management:

- **Old:** `pip install -r requirements.txt`
- **New:** `poetry install`

All Flask and web-related dependencies have been removed as part of the modernization process.

## Python Version Requirement

This project now requires Python 3.11 or higher. Make sure you have the correct Python version:

```bash
python --version  # Should show 3.11.x or higher
```