# harbor image

Harbor agent-evaluation framework CLI 的运行镜像。

- **基础镜像**：`python:3.14.8`（harbor 要求 `>=3.12`；但上游 `litellm` 声明 `requires_python <3.15`，故 3.14 是目前最新可用版本，不用 3.15）
- **harbor**：通过 `uv tool install harbor==<版本>` 安装，二进制在 `/usr/local/bin/harbor`（同时提供 `hb`、`hr`）
- **docker**：仅安装 Docker **客户端**与 **Compose 插件**（静态二进制）；运行时通过挂载宿主 `/var/run/docker.sock` 复用宿主 Docker 引擎
- **镜像 tag**：与 harbor 版本号一致，例如 `harbor:0.24.0`

## 构建

`docker/` 目录即构建上下文（`.dockerignore` 与其同级）。

本地单架构构建（仅本机架构）：

```bash
docker build -t harbor:0.24.0 docker/
```

多架构构建并推送（Linux amd64 + arm64）：

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --provenance=false \
  -t <用户名>/harbor:0.24.0 \
  --push docker/
```

仅构建 Linux amd64（默认不使用 buildx 会只出本机架构，导致 amd64 拉取时报 `no image found ... amd64`）：

```bash
docker buildx build \
  --platform linux/amd64 \
  --provenance=false \
  -t <用户名>/harbor:0.24.0 \
  --push docker/
```

### 指定版本

harbor、docker 客户端与 compose 版本均可通过 build arg 覆盖：

```bash
docker build \
  --build-arg HARBOR_VERSION=0.24.0 \
  --build-arg DOCKER_VERSION=29.9.0 \
  --build-arg COMPOSE_VERSION=5.6.0 \
  -t harbor:0.24.0 docker/
```

`HARBOR_VERSION` 需与镜像 tag 保持一致。

## 运行

必须挂载宿主 Docker socket，容器内的 `harbor` 才能驱动 Docker 本地沙箱：

```bash
docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  harbor:0.24.0 --help
```

运行任务（示例，参数以 harbor 官方文档为准）：

```bash
docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$PWD/tasks:/work/tasks" \
  -w /work \
  harbor:0.24.0 run -p tasks/ -a <agent> -m <model> --n-concurrent <N>
```

## 验证

```bash
docker run --rm harbor:0.24.0 --version 2>/dev/null || docker run --rm harbor:0.24.0 --help
docker run --rm --entrypoint docker \
  -v /var/run/docker.sock:/var/run/docker.sock \
  harbor:0.24.0 version
docker run --rm --entrypoint docker \
  -v /var/run/docker.sock:/var/run/docker.sock \
  harbor:0.24.0 compose version
```

## 说明

- 镜像内**不含** `dockerd`；不适用于需要容器内独立 Docker 环境的场景（如需要请改用 Docker-in-Docker 方案）。
- 若宿主 Docker socket 的属组 GID 与容器内不一致，可用 `--group-add <gid>` 补充。
- `DOCKER_VERSION` 取自 <https://download.docker.com/linux/static/stable/>；`HARBOR_VERSION` 取自 <https://pypi.org/project/harbor/>；`COMPOSE_VERSION` 取自 <https://github.com/docker/compose/releases>。
