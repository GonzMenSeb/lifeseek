# lifeseek reproducible build image (Task 0.2).
# Pins the base by digest and clones every external engine at the exact SHA
# recorded in tools/versions.lock, so `lifeseek reproduce <id>` replays bitwise.
#
# NOTE: engines are documented but NOT built in v1 scaffolding (the adapters ship
# as interfaces/stubs first — Phase 6). Uncomment the build stages once the SHAs
# in tools/versions.lock are confirmed. The deterministic core needs none of them.
#
# Build:   podman build -t lifeseek:repro -f Containerfile .
# The digest below MUST be filled before any release/reproduce run.

# TODO-CONFIRM: replace with the resolved digest from tools/versions.lock.
FROM python:3.12-slim-bookworm
# FROM python:3.12-slim-bookworm@sha256:<digest-from-versions.lock>

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

# Toolchain for: lifelib JIT C++ compile, qfind (C), rlifesrc (Rust), LLS (SAT),
# and bubblewrap sandboxing (Phase 6 / SPEC §10).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential clang git ca-certificates curl pkg-config \
        bubblewrap libseccomp-dev \
    && rm -rf /var/lib/apt/lists/*

# uv for reproducible Python env from uv.lock.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /opt/lifeseek
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --extra lifelib --extra sat --extra mcp --no-install-project
COPY . .
RUN uv sync --frozen --extra lifelib --extra sat --extra mcp

# --- External engines (cloned at pinned SHAs; build stages disabled until SHAs confirmed) ---
# ARG QFIND_SHA      # from tools/versions.lock
# RUN git clone https://github.com/Matthias-Merzenich/qfind /opt/engines/qfind \
#     && git -C /opt/engines/qfind checkout "$QFIND_SHA" \
#     && cc -O3 -march=native -o /usr/local/bin/qfind /opt/engines/qfind/qfind.c
#
# ARG RLIFESRC_SHA
# RUN git clone https://github.com/AlephAlpha/rlifesrc /opt/engines/rlifesrc \
#     && git -C /opt/engines/rlifesrc checkout "$RLIFESRC_SHA" \
#     && cargo build --release --manifest-path /opt/engines/rlifesrc/Cargo.toml -p rlifesrc
#
# ARG LLS_SHA
# RUN git clone https://github.com/OscarCunningham/logic-life-search /opt/engines/lls \
#     && git -C /opt/engines/lls checkout "$LLS_SHA"

ENTRYPOINT ["uv", "run", "lifeseek"]
CMD ["--help"]
