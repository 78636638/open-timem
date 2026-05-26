# [OPEN] startup-failure

## Problem
- Symptom: project startup still fails after previous fixes.
- Expected: FastAPI service starts successfully and stays running.

## Hypotheses
- H1: PostgreSQL credentials or target database are still mismatched.
- H2: Qdrant or another dependent service is unavailable during startup.
- H3: Environment variables are being overridden by config reload logic.
- H4: A later import or initialization dependency is still missing.

## Evidence
- Reproduced startup with current `.env`; service passes PostgreSQL and Qdrant initialization.
- Runtime failure occurs later during workflow initialization with `ModuleNotFoundError: No module named 'torch'`.
- `llm/__init__.py` eagerly imports `Qwen3EmbeddingService`, which imports `torch` at module import time.
- `config/settings.yaml` sets `llm.embedding.provider: qwen_local`, so local embedding path is part of the startup chain.

## Next Step
- Explain confirmed root cause and provide two remediation paths:
- install local embedding dependencies (`torch`, `transformers`) and model files; or
- switch embedding provider / make adapter imports lazy to remove hard startup dependency.
