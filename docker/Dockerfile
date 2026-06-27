# syntax=docker/dockerfile:1.6

# PFC headless dev container.
#
# Goal: run the Itasca PFC Linux engine in console (no-GUI) mode plus the
# itasca-mcp-bridge WebSocket server, so MCP clients on the host can drive PFC
# without a Windows machine. Demo mode (no license) caps models at 1000
# balls/clumps -- enough for bridge dev and smoke tests.
#
# The Itasca .deb (~2.5 GB) is downloaded once on the host and bind-mounted
# into the build, so the slow download is decoupled from build iteration and
# the .deb itself never lands in a Docker layer.
#
# Setup (one time):
#   curl -C - -L -o ~/Downloads/itascasoftware.latest.deb \
#     https://itasca-software.s3.amazonaws.com/itasca-software/9.subscription/itascasoftware.latest.deb
#
# Build (Apple Silicon -> emulate x86_64 via Rosetta):
#   docker build --platform=linux/amd64 \
#       --build-context itasca-deb=$HOME/Downloads \
#       -t itasca-mcp:dev -f docker/Dockerfile .
#
# Run, exposing the bridge WS port to the host:
#   docker run --rm -it --platform=linux/amd64 -p 9001:9001 itasca-mcp:dev

# ---------- Stage 1: install PFC engine ----------
# Ubuntu 22.04 is required because the Itasca binaries link against glibc 2.32+
# (the 9.6 build crashes with `GLIBC_2.34 not found` on 20.04's glibc 2.31).
# The .deb's Depends list still mentions libffi7 -- a 20.04-era package -- so
# we sideload it from the 20.04 archive before installing the .deb. Itasca's
# own packaging is inconsistent on this point; this workaround lets a single
# image work despite it.
FROM --platform=linux/amd64 ubuntu:22.04 AS pfc-engine

ARG DEB_NAME=itascasoftware.latest.deb
# 20.04-era libs the Itasca binaries link against (.deb declares libffi7, the
# embedded Python's _ssl.so links against OpenSSL 1.1). 22.04 ships libffi8 +
# OpenSSL 3.0, so we sideload these from the 20.04 security archive.
ARG LIBFFI7_URL=http://archive.ubuntu.com/ubuntu/pool/main/libf/libffi/libffi7_3.3-4_amd64.deb
ARG LIBSSL1_URL=http://security.ubuntu.com/ubuntu/pool/main/o/openssl/libssl1.1_1.1.1f-1ubuntu2.24_amd64.deb
ARG DEBIAN_FRONTEND=noninteractive

# Pre-accept the EULA for ttf-mscorefonts-installer (a transitive dep of the
# Itasca .deb that would otherwise stall the build on an interactive prompt),
# and sideload libffi7 + libssl1.1 from the 20.04 archive.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        debconf-utils \
        wget \
        && echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" \
            | debconf-set-selections \
        && wget -q -O /tmp/libffi7.deb "${LIBFFI7_URL}" \
        && wget -q -O /tmp/libssl1.deb "${LIBSSL1_URL}" \
        && apt-get install -y --no-install-recommends /tmp/libffi7.deb /tmp/libssl1.deb \
        && rm -f /tmp/libffi7.deb /tmp/libssl1.deb \
        && rm -rf /var/lib/apt/lists/*

# Install the Itasca .deb. The file is bind-mounted from the host build
# context (--build-context itasca-deb=...) so the 2.5 GB binary never lives
# in a Docker layer; only the post-install state under /usr stays. Letting
# `apt install ./file.deb` resolve transitive deps is more reliable than
# pre-listing them -- the package's Depends already enumerates ~30 libs.
RUN --mount=type=bind,from=itasca-deb,target=/itasca-deb \
    apt-get update && \
    apt-get install -y --no-install-recommends "/itasca-deb/${DEB_NAME}" && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/*

# ---------- Stage 2: GUI stack + bridge ----------
FROM pfc-engine AS itasca-mcp

ARG DEBIAN_FRONTEND=noninteractive

# In-container X stack (Xvfb + fluxbox + x11vnc + noVNC) plus the runtime libs
# the PFC binaries dlopen() at startup. Putting these in stage 2 keeps the
# heavy engine layer cached when iterating on the GUI/entrypoint setup.
#
# - libfontconfig1 is required by pfc3d9_gui but missing from the .deb's
#   Depends list (Itasca packaging gap; surfaces as `libfontconfig.so.1: cannot
#   open shared object file` on first launch).
# - mesa-utils + libgl1-mesa-dri provide llvmpipe software GL (Docker-on-Mac
#   has no GPU passthrough).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libfontconfig1 \
        xvfb \
        fluxbox \
        x11vnc \
        novnc \
        websockify \
        x11-utils \
        mesa-utils \
        libgl1-mesa-dri \
    && rm -rf /var/lib/apt/lists/*

# PFC bundles its own Python 3.10 (used by pfc3d_console etc.). That is the
# only interpreter where `import itasca` works, so we install the bridge into
# its site-packages directly. Direct invocation needs LD_LIBRARY_PATH to find
# libpython3.10 and libstdc++ shipped by Itasca.
ENV ITASCA_HOME=/opt/itascasoftware/subscription
ENV ITASCA_PYBIN=${ITASCA_HOME}/python310/bin/python3
ENV ITASCA_LD_PATHS=${ITASCA_HOME}/python310/bin:${ITASCA_HOME}

WORKDIR /opt/itasca-mcp-bridge
COPY itasca-mcp-bridge/ ./

# Editable install so a future bind-mount of the host's source can iterate
# without rebuilding the image. Using the embedded Python guarantees the
# bridge runs in the same interpreter as the `itasca` module.
RUN LD_LIBRARY_PATH=${ITASCA_LD_PATHS} ${ITASCA_PYBIN} -m pip install --no-cache-dir -e .

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# pfc3d9_gui resolves project/data paths against CWD; sit in /workspace so
# they go to the host-mounted user workspace, not the bridge install dir.
WORKDIR /workspace

EXPOSE 9001 6080

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
