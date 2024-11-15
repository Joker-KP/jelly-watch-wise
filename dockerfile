FROM python:3.10-slim AS builder

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive TZ=Europe/Warsaw \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN python -m pip install --upgrade pip

RUN python -m pip install --upgrade libsass

FROM python:3.10-slim AS release
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
ARG VERSION

RUN python -m pip install --upgrade pip

RUN python -m pip install \
    nicegui[plotly,matplotlib]==$VERSION \
    isort \
    requests \
    python-i18n

WORKDIR /app

COPY main.py misc.py config.py ./
COPY jellyfin ./jellyfin
COPY lang ./lang
RUN mkdir /config
RUN mkdir /resources
COPY docker-entrypoint.sh /resources
RUN chmod 777 /resources/docker-entrypoint.sh

EXPOSE 8080
ENV PYTHONUNBUFFERED=True

ENTRYPOINT ["/resources/docker-entrypoint.sh"]
CMD ["python", "main.py"]