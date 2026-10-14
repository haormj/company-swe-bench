# Python 3.14 (not 3.15): harbor -> litellm declares `requires_python <3.15`
# and fastuuid only ships wheels up to cp314, so 3.14 is the newest supported.
FROM python:3.14.8

ARG HARBOR_VERSION=0.24.0
ARG DOCKER_VERSION=29.9.0

LABEL org.opencontainers.image.title="harbor" \
      org.opencontainers.image.description="Harbor agent-evaluation framework CLI with Docker client support" \
      org.opencontainers.image.source="https://harborframework.com/docs" \
      org.opencontainers.image.version="${HARBOR_VERSION}"

# uv: Python tool manager, used to install the harbor CLI in an isolated env.
RUN pip install --no-cache-dir uv

# Install the harbor CLI and expose the `harbor` binary on PATH.
ENV UV_TOOL_BIN_DIR=/usr/local/bin
RUN uv tool install "harbor==${HARBOR_VERSION}"

# Install only the Docker CLI (static binary). The daemon is provided at runtime
# by mounting the host socket, so no dockerd is shipped in the image.
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) docker_arch=x86_64 ;; \
      arm64) docker_arch=aarch64 ;; \
      *) echo "unsupported architecture: $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://download.docker.com/linux/static/stable/${docker_arch}/docker-${DOCKER_VERSION}.tgz" \
      | tar -xz --strip-components=1 -C /usr/local/bin docker/docker; \
    docker --version

# Runtime usage (mount the host Docker socket so the CLI can reach a daemon):
#   docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock harbor:0.24.0 --help
ENTRYPOINT ["harbor"]
CMD ["--help"]
