# Stage 1: Builder
FROM python:3.10-slim AS builder

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive TZ=Europe/Warsaw \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN python -m pip install --upgrade pip

ARG TARGETPLATFORM

# Do not touch libsass on ARM64 (it fails)
RUN [ "$TARGETPLATFORM" = "linux/amd64" ] && python -m pip install --upgrade libsass || true

# Install all dependencies here
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

# Stage 2: Release
FROM python:3.10-slim AS release
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Set up working directory
WORKDIR /app

# Copy application files
COPY main.py misc.py config.py ./
COPY jellyfin ./jellyfin
COPY lang ./lang
RUN mkdir ./config
COPY config/config-sample.yaml ./config/config-sample.yaml

# Create and set up resources directory
RUN mkdir /resources
COPY docker-entrypoint.sh /resources
RUN chmod 755 /resources/docker-entrypoint.sh

VOLUME /app/config

EXPOSE 8080

ENV PYTHONUNBUFFERED=True
ENV TZ=Europe/Warsaw

RUN chmod +x /resources/docker-entrypoint.sh
ENTRYPOINT ["/resources/docker-entrypoint.sh"]
CMD ["python", "main.py"]