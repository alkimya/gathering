# Contributing

Thank you for considering contributing to GatheRing!

For the complete contributing guide, see [CONTRIBUTING.md](../../CONTRIBUTING.md) in the project root.

## Quick Start

### 1. Fork and Clone

```bash
git clone https://github.com/alkimya/gathering.git
cd gathering
git remote add upstream https://github.com/alkimya/gathering.git
```

### 2. Setup Development Environment

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 4. Make Changes

- Write tests first (TDD)
- Follow code style guidelines
- Update documentation

### 5. Run Tests

```bash
pytest
```

### 6. Submit PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Code Style

- **Black** for formatting
- **Flake8** for linting
- **MyPy** for type checking
- Google-style docstrings

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(agents): add emotional state tracking
fix(memory): prevent memory overflow
docs(api): update examples
```

## Getting Help

- GitHub Issues for bugs
- GitHub Discussions for questions
- Check [CONTRIBUTING.md](../../CONTRIBUTING.md) for details
