# Migration to uv Package Manager

## Summary

PharmaGuide now exclusively uses `uv` with `pyproject.toml` for dependency management. The `requirements.txt` file has been removed.

## Changes Made

### 1. Removed requirements.txt
- ✅ Deleted `requirements.txt`
- ✅ Added to `.gitignore` to prevent re-addition

### 2. Updated pyproject.toml
- ✅ Added explicit bcrypt version: `bcrypt>=4.1.2,<5.0.0`
- ✅ All dependencies now managed in `pyproject.toml`

### 3. Updated Documentation
- ✅ `docs/FAQ.md` - Changed pip to uv commands
- ✅ `docs/ENVIRONMENT_SETUP.md` - Changed pip to uv commands
- ✅ `docs/LOCAL_DEVELOPMENT.md` - Changed pip to uv commands
- ✅ `scripts/setup_local_dev.sh` - Removed pip fallback

### 4. Fixed bcrypt Issue
- ✅ Updated bcrypt to 4.3.0 (via uv sync)
- ✅ Updated `src/auth/security.py` to handle password truncation properly

## Why uv?

**Benefits:**
- ⚡ **Faster**: 10-100x faster than pip
- 🔒 **Reliable**: Deterministic dependency resolution
- 📦 **Modern**: Built-in virtual environment management
- 🎯 **Simple**: Single tool for all Python package management

## Usage

### Install Dependencies
```bash
uv sync
```

### Add a New Dependency
```bash
uv add package-name
```

### Add a Dev Dependency
```bash
uv add --dev package-name
```

### Update Dependencies
```bash
uv sync --upgrade
```

### Run Commands
```bash
uv run python script.py
uv run pytest
uv run uvicorn src.main:app
```

### Install Specific Package (without adding to pyproject.toml)
```bash
uv pip install package-name
```

## Migration Guide for Contributors

If you have an existing clone:

1. **Remove old virtual environment:**
   ```bash
   rm -rf venv/ .venv/
   ```

2. **Install uv (if not already installed):**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Sync dependencies:**
   ```bash
   uv sync
   ```

4. **Run the application:**
   ```bash
   uv run uvicorn src.main:app --reload
   ```

## Common Commands Comparison

| Task | Old (pip) | New (uv) |
|------|-----------|----------|
| Install deps | `pip install -r requirements.txt` | `uv sync` |
| Add package | `pip install package` | `uv add package` |
| Run script | `python script.py` | `uv run python script.py` |
| Run tests | `pytest` | `uv run pytest` |
| Update deps | `pip install -U -r requirements.txt` | `uv sync --upgrade` |

## pyproject.toml Structure

```toml
[project]
name = "pharmaguide"
version = "0.1.0"
dependencies = [
    "fastapi>=0.104.1",
    "bcrypt>=4.1.2,<5.0.0",
    # ... other dependencies
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.3",
    # ... dev dependencies
]

[tool.uv]
dev-dependencies = [
    "pytest>=7.4.3",
    # ... dev dependencies
]
```

## Troubleshooting

### Issue: "uv: command not found"

**Solution:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # or ~/.zshrc
```

### Issue: Dependencies not syncing

**Solution:**
```bash
# Remove lock file and resync
rm uv.lock
uv sync
```

### Issue: Want to use a specific Python version

**Solution:**
```bash
uv venv --python 3.11
uv sync
```

## Benefits for PharmaGuide

1. **Faster CI/CD**: Dependency installation is 10-100x faster
2. **Reproducible Builds**: `uv.lock` ensures exact versions
3. **Simpler Workflow**: One tool instead of pip + venv + pip-tools
4. **Better Error Messages**: Clear dependency conflict resolution
5. **Modern Standards**: Follows PEP 621 (pyproject.toml)

## Resources

- [uv Documentation](https://github.com/astral-sh/uv)
- [uv Installation Guide](https://github.com/astral-sh/uv#installation)
- [PEP 621 - pyproject.toml](https://peps.python.org/pep-0621/)

## Status

✅ **Migration Complete**

All scripts, documentation, and workflows now use `uv` exclusively.

---

**Note:** If you encounter any issues with the migration, please open an issue on GitHub.
