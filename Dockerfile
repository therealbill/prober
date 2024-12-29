FROM python:3.11-slim

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

#
RUN apt update
RUN apt install iputils-ping -y 

# Install poetry
RUN pip install "poetry==$POETRY_VERSION"

# Create and set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml poetry.lock ./
COPY prober/ ./prober/

# Install dependencies
RUN poetry install --no-dev

# Create non-root user
RUN useradd -m -u 1000 appuser
USER appuser

# Set the entrypoint
ENTRYPOINT ["poetry", "run", "email-probe"]
