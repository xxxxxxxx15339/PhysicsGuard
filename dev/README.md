# Non-root Linux repair evaluation

Docker and Podman were unavailable during Milestone 3.1 implementation. This
recipe has **not been built or run**. The executed evidence is from non-root
Linux and the historical published GitHub Actions matrix, not this container.
It provides a supported-OS development route from macOS, not arbitrary-code safety.

Use an already authorized Docker Desktop or preferably a rootless Linux engine;
do not install/configure a privileged daemon or use `sudo` for this task. See
[Docker rootless mode](https://docs.docker.com/engine/security/rootless/) and
[runtime restrictions](https://docs.docker.com/engine/containers/run/).

From the repository root:

```sh
# For a reproducible build, replace the default tag with a verified official
# python:3.13-slim-bookworm@sha256:... digest obtained for your target platform.
# Record that digest, platform, resulting image ID and pip freeze with the run.
docker build -f dev/repair.Dockerfile -t physicsguard-repair:3.1 .
docker image inspect physicsguard-repair:3.1 --format '{{.Id}}'
docker run --name physicsguard-repair-eval \
  --network none --read-only --user 65532:65532 \
  --cap-drop ALL --security-opt no-new-privileges \
  --cpus 2 --memory 3g --pids-limit 128 \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=256m,mode=1777 \
  physicsguard-repair:3.1
docker cp physicsguard-repair-eval:/artifacts/source-repair-evaluator.json artifacts/source-repair-evaluator-container.json
docker rm -v physicsguard-repair-eval
```

Build-time network is used only for pinned development dependencies; runtime
evaluation has no network. Source is copied into the image, never writable host
mounts. The named container's anonymous artifact volume and temporary files are
disposable; copy the evaluator report to a **host-only** location, then remove
the container and its volume. No host home, `.env`, cloud credentials, Docker
socket, SSH agent, research papers or private evaluator mounts are supplied.
The Dockerfile copies only explicit project inputs; `.dockerignore` also limits
the build context. Pinning package versions plus a moving image tag alone is not
bit-for-bit reproduction; use the image digest and keep a dependency/image record.

For tests, use the same restrictions and an ephemeral container, overriding CMD:

```sh
docker run --rm --network none --read-only --user 65532:65532 \
  --cap-drop ALL --security-opt no-new-privileges \
  --cpus 2 --memory 3g --pids-limit 128 \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=256m,mode=1777 \
  physicsguard-repair:3.1 python -m pytest -q -o cache_dir=/tmp/pytest-cache
```

The worker still accepts only four reviewed originals plus a constrained edit.
Containers, AST checks, timeouts and rootless execution individually do not
establish a secure arbitrary-code sandbox. This image contains public verifier
definitions and is **not** an investigator image or a private holdout boundary.
Before arbitrary patches, separately test filesystem/network isolation, CPU,
memory/process and hard wall limits, immutable source/verifier mounts, restricted
commands and absence of secrets. Before Meta orchestration, expose only JSON
tool messages to a separate investigator that cannot read evaluator assets.
