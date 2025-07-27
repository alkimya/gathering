# Installation Guide

This guide covers the installation process for GatheRing.

## Requirements

| Component         | Requirement                |
|------------------|-----------------------------|
| Python           | 3.11 or higher              |
| Operating System | Linux, macOS, Windows       |
| Memory           | 4GB minimum, 8GB recommended|
| Storage          | 1GB for base installation   |

## Installation Methods

### From Source (Recommended)

```bash
# Clone repository
git clone https://github.com/alkimya/gathering.git
cd gathering

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Using pip (coming soon)

```bash
pip install gathering
```

### Using Docker

```bash
# Build image
docker build -t gathering:latest .

# Run container
docker run -it gathering:latest
```

## Verifying Installation

Run the quick start script:

```bash
python quick_start.py
```

Or run tests:

```bash
pytest tests/
```
