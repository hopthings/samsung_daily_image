# Contributing to Samsung Daily Image

Thank you for your interest in contributing to Samsung Daily Image! This document provides guidelines for contributing to this project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/samsung_daily_image.git`
3. Create a virtual environment: `python -m venv .venv && source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Create a branch for your changes: `git checkout -b feature/your-feature-name`

## Development Setup

1. Copy `.env.example` to `.env` and configure your settings
2. Run the linter: `flake8 .`
3. Run type checking: `mypy --strict .`
4. Run tests: `pytest`

## Code Style

- Follow PEP 8 with 88 character line length (Black compatible)
- Use type hints for all functions and classes
- Write Google-style docstrings for modules, classes, and functions
- Keep imports organized: stdlib, third-party, then local

## Submitting Changes

1. Ensure your code passes linting and type checking
2. Write or update tests for your changes
3. Commit with clear, descriptive messages
4. Push to your fork and open a pull request
5. Describe your changes in the PR description

## Reporting Issues

When reporting issues, please include:
- Python version
- Operating system
- Samsung TV model (if relevant)
- Steps to reproduce the issue
- Expected vs actual behavior
- Relevant log output

## Feature Requests

Feature requests are welcome! Please open an issue describing:
- The problem you're trying to solve
- Your proposed solution
- Any alternatives you've considered

## Questions

If you have questions, feel free to open an issue with the "question" label.
