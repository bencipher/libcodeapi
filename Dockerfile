# Base stage
FROM python:3.12 as base
WORKDIR /app

# Copy the pyproject.toml and poetry.lock files
COPY pyproject.toml poetry.lock ./

RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# Final stage
FROM base as final
ARG SERVICE
WORKDIR /app

# Copy the entire project
COPY . .

RUN if [ -f ${SERVICE}/requirements.txt ]; then \
        poetry add $(cat ${SERVICE}/requirements.txt); \
    fi

