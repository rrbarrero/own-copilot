FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

ARG UID=1000
ARG GID=1000

RUN groupadd -g $GID sandbox && \
    useradd -m -u $UID -g $GID sandbox

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

USER sandbox
WORKDIR /workspace

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD ["sleep", "infinity"]