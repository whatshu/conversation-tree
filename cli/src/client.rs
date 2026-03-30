use anyhow::{anyhow, Context, Result};
use futures_util::StreamExt;
use reqwest::header::{HeaderMap, HeaderValue, AUTHORIZATION, CONTENT_TYPE};
use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, Deserialize)]
pub struct WorkspaceDto {
    pub id: String,
    pub name: String,
    pub description: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct BranchDto {
    pub id: String,
    pub workspace_id: String,
    pub name: String,
    pub base_node_id: Option<String>,
    pub head_node_id: Option<String>,
    pub auto_named: bool,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct NodeDto {
    pub id: String,
    pub workspace_id: String,
    pub parent_node_id: Option<String>,
    pub user_prompt: String,
    pub created_at: String,
    pub latest_run_id: Option<String>,
    pub latest_assistant_message: Option<String>,
    pub latest_summary: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct TreeDto {
    pub workspace: WorkspaceDto,
    pub branches: Vec<BranchDto>,
    pub nodes: Vec<NodeDto>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct RunEventDto {
    pub id: String,
    pub run_id: String,
    pub sequence: i64,
    pub event_type: String,
    pub payload_json: String,
    pub created_at: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct TraceDto {
    pub run_id: String,
    pub node_id: String,
    pub branch_id: Option<String>,
    pub provider_name: String,
    pub model_name: String,
    pub assistant_message: Option<String>,
    pub summary: Option<String>,
    pub events: Vec<RunEventDto>,
}

#[derive(Debug, Clone, Serialize)]
pub struct WorkspaceCreateRequest {
    pub name: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct BranchRenameRequest {
    pub name: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct ChatRequest {
    pub prompt: String,
    pub parent_node_id: Option<String>,
    pub branch_name: Option<String>,
}

#[derive(Debug, Clone)]
pub struct SseEvent {
    pub event: String,
    pub data: Value,
}

#[derive(Clone)]
pub struct ApiClient {
    client: reqwest::Client,
    base_url: String,
}

impl ApiClient {
    pub fn new(base_url: &str, token: &str) -> Result<Self> {
        let mut headers = HeaderMap::new();
        let auth = format!("Bearer {}", token);
        headers.insert(AUTHORIZATION, HeaderValue::from_str(&auth)?);
        headers.insert(CONTENT_TYPE, HeaderValue::from_static("application/json"));
        let client = reqwest::Client::builder()
            .default_headers(headers)
            .build()
            .context("failed to build reqwest client")?;
        Ok(Self {
            client,
            base_url: base_url.trim_end_matches('/').to_string(),
        })
    }

    pub async fn create_workspace(&self, name: &str) -> Result<WorkspaceDto> {
        self.client
            .post(format!("{}/v1/workspaces", self.base_url))
            .json(&WorkspaceCreateRequest {
                name: name.to_string(),
            })
            .send()
            .await?
            .error_for_status()?
            .json()
            .await
            .context("failed to decode workspace response")
    }

    pub async fn list_workspaces(&self) -> Result<Vec<WorkspaceDto>> {
        self.client
            .get(format!("{}/v1/workspaces", self.base_url))
            .send()
            .await?
            .error_for_status()?
            .json()
            .await
            .context("failed to decode workspaces")
    }

    pub async fn get_tree(&self, workspace_id: &str) -> Result<TreeDto> {
        self.client
            .get(format!("{}/v1/workspaces/{}/tree", self.base_url, workspace_id))
            .send()
            .await?
            .error_for_status()?
            .json()
            .await
            .context("failed to decode tree")
    }

    pub async fn list_branches(&self, workspace_id: &str) -> Result<Vec<BranchDto>> {
        self.client
            .get(format!("{}/v1/workspaces/{}/branches", self.base_url, workspace_id))
            .send()
            .await?
            .error_for_status()?
            .json()
            .await
            .context("failed to decode branches")
    }

    pub async fn rename_branch(&self, workspace_id: &str, branch_id: &str, new_name: &str) -> Result<BranchDto> {
        self.client
            .patch(format!(
                "{}/v1/workspaces/{}/branches/{}",
                self.base_url, workspace_id, branch_id
            ))
            .json(&BranchRenameRequest {
                name: new_name.to_string(),
            })
            .send()
            .await?
            .error_for_status()?
            .json()
            .await
            .context("failed to decode renamed branch")
    }

    pub async fn get_node(&self, workspace_id: &str, node_id: &str) -> Result<NodeDto> {
        self.client
            .get(format!(
                "{}/v1/workspaces/{}/nodes/{}",
                self.base_url, workspace_id, node_id
            ))
            .send()
            .await?
            .error_for_status()?
            .json()
            .await
            .context("failed to decode node")
    }

    pub async fn get_trace(&self, workspace_id: &str, node_id: &str) -> Result<TraceDto> {
        self.client
            .get(format!(
                "{}/v1/workspaces/{}/nodes/{}/trace",
                self.base_url, workspace_id, node_id
            ))
            .send()
            .await?
            .error_for_status()?
            .json()
            .await
            .context("failed to decode trace")
    }

    pub async fn stream_chat(&self, workspace_id: &str, payload: &ChatRequest) -> Result<Vec<SseEvent>> {
        let response = self
            .client
            .post(format!(
                "{}/v1/workspaces/{}/messages/stream",
                self.base_url, workspace_id
            ))
            .json(payload)
            .send()
            .await?
            .error_for_status()?;
        let mut stream = response.bytes_stream();
        let mut buffer = String::new();
        let mut events = Vec::new();
        while let Some(chunk) = stream.next().await {
            let chunk = chunk?;
            buffer.push_str(&String::from_utf8_lossy(&chunk));
            while let Some(index) = buffer.find("\n\n") {
                let frame = buffer[..index].to_string();
                buffer = buffer[index + 2..].to_string();
                if let Some(event) = parse_sse_frame(&frame)? {
                    events.push(event);
                }
            }
        }
        Ok(events)
    }
}

fn parse_sse_frame(frame: &str) -> Result<Option<SseEvent>> {
    let mut event_name = None;
    let mut data = None;
    for line in frame.lines() {
        if let Some(value) = line.strip_prefix("event: ") {
            event_name = Some(value.to_string());
        } else if let Some(value) = line.strip_prefix("data: ") {
            data = Some(serde_json::from_str::<Value>(value).context("failed to parse event data")?);
        }
    }
    match (event_name, data) {
        (Some(event), Some(data)) => Ok(Some(SseEvent { event, data })),
        (None, None) => Ok(None),
        _ => Err(anyhow!("incomplete SSE frame: {frame}")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_simple_sse_frame() {
        let frame = "event: token\ndata: {\"text\":\"hello\"}";
        let event = parse_sse_frame(frame).expect("frame should parse").expect("event should exist");
        assert_eq!(event.event, "token");
        assert_eq!(event.data["text"], "hello");
    }
}
