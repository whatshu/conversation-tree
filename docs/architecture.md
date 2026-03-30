# 架构说明

## 总览

系统由三个部分组成：

- Rust CLI：保存本地活跃 workspace/ref，并通过 HTTP/SSE 与后端通信
- Python API：负责工作区、tree 查询、节点创建和流式响应
- Python worker：异步消费摘要任务并回写 `run_summaries`

## 数据模型

- `Workspace`：一个独立 conversation tree
- `Node`：一个用户 prompt 节点，只记录用户输入和父节点关系
- `Run`：某个节点对应的一次 agent 执行
- `RunEvent`：token、tool call、tool result、assistant final 等有序事件
- `RunSummary`：总结该节点执行过程的摘要
- `Branch`：轻量命名引用，保存 `base_node_id` 和 `head_node_id`

## 分支规则

- 首次消息创建默认分支 `main`
- 从当前 head 继续：沿原 branch 前进
- 从历史节点继续：在成功生成新节点后自动创建新 branch

## 安全边界

- v1 为本机单用户，后端只开放到 localhost
- 使用 Bearer token 保护所有业务接口
- 不提供任意 shell 工具，工具注册表默认只加载白名单只读工具
