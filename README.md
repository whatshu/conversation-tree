# Conversation Tree

一个本地优先的 conversation tree 应用，包含：

- Rust CLI：聊天优先、少量 git 风格命令管理 tree
- Python backend：FastAPI + LangGraph + PostgreSQL
- Docker Compose：本地安全运行 `api + worker + postgres`

## 项目结构

- `cli/`：Rust 命令行前端
- `server/`：Python HTTP 后端和 worker
- `docs/`：架构、API、CLI 和部署文档

## 快速开始

1. 复制环境变量：

```bash
cp .env.example .env
```

2. 启动后端：

```bash
docker compose up --build
```

3. 安装并运行 CLI：

```bash
cd cli
cargo run -- workspace new default
cargo run -- workspace use default
cargo run -- config set-base-url http://127.0.0.1:8000
cargo run -- config set-api-token change-me-local-token
cargo run -- chat
```

CLI 的 `base_url` 和 `api_token` 都支持两种配置方式：

- 在 `.env` 中配置 `CT_SERVER_URL` 和 `CT_API_TOKEN`
- 用 `ct config set-base-url ...` / `ct config set-api-token ...` 写入本地 config

## 当前实现说明

- 后端默认只绑定 `127.0.0.1:8000`
- 所有 API 需要 `Authorization: Bearer <token>`
- 分支从历史节点继续时自动创建，可后续重命名
- 自动分支名默认形如 `branch/<timestamp>-<slug>`
- agent/tool 明细保存在 trace 中，tree 视图默认只展示摘要
- worker 会异步生成 AI summary，CLI 默认展示摘要，必要时可查看 trace

更多细节见：

- [docs/architecture.md](docs/architecture.md)
- [docs/api.md](docs/api.md)
- [docs/cli.md](docs/cli.md)
- [docs/deployment.md](docs/deployment.md)
