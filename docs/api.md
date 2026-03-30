# HTTP API

## 鉴权

所有业务接口都需要：

```http
Authorization: Bearer <CT_API_TOKEN>
```

## 主要端点

- `POST /v1/workspaces`
- `GET /v1/workspaces`
- `GET /v1/workspaces/{id}`
- `GET /v1/workspaces/{id}/tree`
- `GET /v1/workspaces/{id}/branches`
- `PATCH /v1/workspaces/{id}/branches/{branch_id}`
- `GET /v1/workspaces/{id}/nodes/{node_id}`
- `GET /v1/workspaces/{id}/nodes/{node_id}/trace`
- `POST /v1/workspaces/{id}/messages/stream`

## SSE 事件

- `token`
- `tool_call`
- `tool_result`
- `assistant_final`
- `node_saved`
- `summary_status`
- `error`
