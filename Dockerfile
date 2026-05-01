FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext \
    && rm -rf /var/lib/apt/lists/*

COPY requirements /app/requirements
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements/prod.txt

COPY . /app

RUN groupadd --system appuser \
    && useradd --system --gid appuser --create-home --shell /bin/sh appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data \
    && chmod +x /app/scripts/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "settings.asgi:application"]
