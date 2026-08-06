# syntax=docker/dockerfile:1
FROM mcr.microsoft.com/devcontainers/python:3.13@sha256:a193ef0a42790e4bcaeeb13665d7bd3cb538a1cf4be721797e18f5dceaa92b1e
ENV DEBIAN_FRONTEND=noninteractive
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates direnv git pkg-config \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.12.0@sha256:606e70c71c852d03f611b1e56a195d08648507018a7057fab82c4974c4eae105 /uv /uvx /usr/local/bin/
COPY --from=ghcr.io/getsops/sops:v3.11.0@sha256:6ce00ac946e1a52b2d1e5b7087441f7b6ef7bad907753104013f8bdb8f5fd891 /usr/local/bin/sops /usr/local/bin/sops
ENV UV_PROJECT_ENVIRONMENT=.venv
ENV UV_LINK_MODE=copy
ENV PATH="/home/vscode/.venv/bin:${PATH}"
