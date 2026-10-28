# Development/evaluation only. Use a recorded official image digest for replay.
ARG PYTHON_IMAGE=python:3.13-slim-bookworm
FROM ${PYTHON_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
WORKDIR /opt/physicsguard
COPY dev/repair-requirements.txt /tmp/repair-requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/repair-requirements.txt
# Explicit copies exclude credentials, .git, research assets and host artifacts.
COPY pyproject.toml README.md ./
COPY src ./src
COPY tests ./tests
COPY benchmarks ./benchmarks
RUN python -m pip install --no-deps --no-build-isolation -e . \
    && mkdir /artifacts && chown 65532:65532 /artifacts
USER 65532:65532
VOLUME /artifacts
CMD ["python", "-m", "benchmarks.source_repair.evaluate", "--output", "/artifacts/source-repair-evaluator.json"]
