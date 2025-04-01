# Samsung Daily Image Project Guidelines

## Commands
- Setup: `source .venv/bin/activate && pip install -r requirements.txt`
- Run: `python main.py`
- Lint: `flake8 .`
- Type checking: `mypy --strict .`
- Test: `pytest`
- Single test: `pytest test_file.py::test_function -v`

## Code Style
- **Format**: Follow PEP 8, 88 char line length (Black compatible)
- **Imports**: stdlib → third-party → local; alphabetized in groups
- **Types**: Full type hints for all functions and classes
- **Naming**: snake_case (vars, functions), PascalCase (classes), UPPERCASE (constants)
- **Documentation**: Google-style docstrings for modules, classes, and functions
- **Error handling**: Use specific exceptions with informative messages
- **Security**: No credentials in code, use .env with python-dotenv
- **Art Generation**: Always use 16:9 aspect ratio, palette knife/impasto style