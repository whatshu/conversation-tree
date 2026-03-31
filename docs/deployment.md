# 部署与排障

## 本地部署

1. 创建 `.env`
2. 执行 `docker compose up --build`
3. 确认 `http://127.0.0.1:8000/health` 返回正常

## Docker 暴露方式

- API 容器内部绑定 `0.0.0.0`
- 宿主机仍只通过 `127.0.0.1:8000` 暴露，保持本机可访问、局域网默认不可访问

## 数据库初始化

- 服务启动时会优先执行 Alembic `upgrade head`
- 如果本地开发环境缺少 migration 配置，则退回到 SQLAlchemy metadata 初始化

## 常见问题

### API token 不匹配

- 检查 CLI 配置中的 token 是否与 `.env` 一致

### PostgreSQL 启动失败

- 删除本地卷后重新启动
- 检查 5432 端口占用

### CLI 无法编译

- 安装 Rust toolchain
- 执行 `cargo test` 与 `cargo run`

### 后端测试

- 执行 `docker compose run --build --rm api python -m pytest tests`
