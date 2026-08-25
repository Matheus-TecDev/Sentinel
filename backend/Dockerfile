FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get upgrade -y --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip uninstall --yes pip setuptools && \
    groupadd --gid 10001 sentinel && \
    useradd --uid 10001 --gid sentinel --home-dir /home/sentinel \
        --create-home --shell /usr/sbin/nologin sentinel

COPY --chown=sentinel:sentinel alembic.ini .
COPY --chown=sentinel:sentinel alembic ./alembic
COPY --chown=sentinel:sentinel app ./app
COPY --chown=sentinel:sentinel entrypoint.sh .

RUN chmod +x /app/entrypoint.sh

USER sentinel:sentinel

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
