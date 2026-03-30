# CLI 使用说明

## 命令

- `ct workspace list`
- `ct workspace new <name>`
- `ct workspace use <name-or-id>`
- `ct config show`
- `ct config set-base-url <http://host:port>`
- `ct chat [--workspace <name-or-id>] [--from <node-or-branch>]`
- `ct tree [--all|--branch <name>|--node <id>]`
- `ct checkout <node-id|branch-name>`
- `ct branch list`
- `ct branch rename <branch> <new-name>`
- `ct show <node-id> [--trace]`

## 配置

- `ct config show`：查看当前 CLI 保存的 `base_url`、活跃 workspace 和活跃 ref
- `ct config set-base-url <url>`：修改 CLI 连接的后端地址，要求以 `http://` 或 `https://` 开头

## 聊天内命令

- `/tree`
- `/checkout <node-id|branch>`
- `/branch list`
- `/branch rename <branch> <new-name>`
- `/show <node-id>`
- `/exit`
