# Contributing to Universal Memory

Thank you for your interest in contributing to **Universal Memory**! We welcome contributions from everyone.

To make the contribution process smooth and efficient, please follow these guidelines.

---

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please report any unacceptable behavior to `dev@amorelliaoyan.com`.

## Getting Started

### Prerequisites

This project uses [uv](https://github.com/astral-sh/uv) for fast Python package and environment management. You will need:

- Python 3.12 or newer.
- `uv` installed on your machine. You can install it via:
  ```bash
  # macOS/Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Windows
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
  # Or via Homebrew (macOS)
  brew install uv
  ```

### Development Setup

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/universal-memory.git
   cd universal-memory
   ```
3. **Set up the virtual environment** and sync dependencies:
   ```bash
   uv sync --locked --all-groups
   ```
   This will create a `.venv` directory and install all production and development dependencies (including `pytest`, `ruff`, and `pyright`).

---

## Development Workflow

### 1. Create a Branch

Create a descriptive branch for your changes:
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b bugfix/your-bug-name
```

### 2. Make Your Changes

Write clean, documented, and typed Python code. Make sure to follow the existing patterns and directory layout.

### 3. Run Quality Checks Locally

Before submitting your code, ensure it passes all local checks. Our CI/CD pipeline runs these checks on every Pull Request, and they must pass.

* **Linting & Code Style:**
  ```bash
  uv run ruff check .
  ```
* **Auto-formatting:**
  ```bash
  uv run ruff format .
  ```
* **Type Checking:**
  ```bash
  uv run pyright
  ```
* **Unit Tests:**
  ```bash
  uv run pytest
  ```

Make sure any new features or bug fixes have corresponding tests in the `tests/` directory.

### 4. Commit and Push

Use clear, descriptive commit messages. Push your branch to your fork:
```bash
git push origin feature/your-feature-name
```

### 5. Open a Pull Request

Go to the [original repository](https://github.com/YanAmorelli/universal-memory) and open a Pull Request.
- Follow the instructions in the Pull Request Template.
- Explain the problem you are solving and the solution you implemented.
- Wait for the CI/CD checks to pass and a maintainer to review your PR.

---

## Asking for Help

If you have questions about the codebase, need help setting up the environment, or want to discuss a feature design before writing code, feel free to open a [GitHub Issue](https://github.com/YanAmorelli/universal-memory/issues) or reach out to the maintainer.
