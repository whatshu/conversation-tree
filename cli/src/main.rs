mod client;
mod config;
mod render;

use anyhow::{anyhow, Context, Result};
use clap::{Args, Parser, Subcommand};
use client::{ApiClient, ChatRequest};
use config::{ActiveRef, CliConfig};
use render::{render_branch_lines, render_node_line, render_workspace_lines};
use std::io::{self, Write};

#[derive(Parser)]
#[command(name = "ct")]
#[command(about = "Conversation tree CLI", version)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Workspace(WorkspaceCommand),
    Config(ConfigCommand),
    Chat(ChatCommand),
    Tree(TreeCommand),
    Checkout(CheckoutCommand),
    Branch(BranchCommand),
    Show(ShowCommand),
}

#[derive(Args)]
struct ChatCommand {
    #[arg(long)]
    workspace: Option<String>,
    #[arg(long = "from")]
    from_ref: Option<String>,
}

#[derive(Args)]
struct TreeCommand {
    #[arg(long)]
    all: bool,
    #[arg(long)]
    branch: Option<String>,
    #[arg(long)]
    node: Option<String>,
}

#[derive(Args)]
struct CheckoutCommand {
    value: String,
}

#[derive(Args)]
struct ShowCommand {
    node_id: String,
    #[arg(long)]
    trace: bool,
}

#[derive(Subcommand)]
enum WorkspaceAction {
    List,
    New { name: String },
    Use { value: String },
}

#[derive(Args)]
struct WorkspaceCommand {
    #[command(subcommand)]
    action: WorkspaceAction,
}

#[derive(Subcommand)]
enum BranchAction {
    List,
    Rename { branch: String, new_name: String },
}

#[derive(Args)]
struct BranchCommand {
    #[command(subcommand)]
    action: BranchAction,
}

#[derive(Subcommand)]
enum ConfigAction {
    Show,
    SetBaseUrl { url: String },
    SetApiToken { token: String },
}

#[derive(Args)]
struct ConfigCommand {
    #[command(subcommand)]
    action: ConfigAction,
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();
    let mut config = CliConfig::load()?;
    let client = ApiClient::new(&config.resolved_server_url()?, &config.resolved_api_token()?)?;

    match cli.command {
        Commands::Workspace(command) => handle_workspace(command, &client, &mut config).await?,
        Commands::Config(command) => handle_config(command, &mut config)?,
        Commands::Chat(command) => handle_chat(command, &client, &mut config).await?,
        Commands::Tree(command) => handle_tree(command, &client, &config).await?,
        Commands::Checkout(command) => handle_checkout(command, &mut config)?,
        Commands::Branch(command) => handle_branch(command, &client, &config).await?,
        Commands::Show(command) => handle_show(command, &client, &config).await?,
    }

    Ok(())
}

fn handle_config(command: ConfigCommand, config: &mut CliConfig) -> Result<()> {
    match command.action {
        ConfigAction::Show => {
            println!(
                "base_url: {} ({})",
                config.resolved_server_url()?,
                config.server_url_source()?
            );
            println!(
                "api_token: {} ({})",
                mask_token(&config.resolved_api_token()?),
                config.api_token_source()?
            );
            if let Some(workspace_id) = &config.active_workspace_id {
                println!("active_workspace_id: {}", workspace_id);
            }
            if let Some(workspace_name) = &config.active_workspace_name {
                println!("active_workspace_name: {}", workspace_name);
            }
            if let Some(active_ref) = &config.active_ref {
                println!("active_ref: {} {}", active_ref.kind, active_ref.value);
            }
        }
        ConfigAction::SetBaseUrl { url } => {
            config.server_url = normalize_base_url(&url)?;
            config.save()?;
            println!("base_url set to {}", config.server_url);
        }
        ConfigAction::SetApiToken { token } => {
            config.api_token = normalize_api_token(&token)?;
            config.save()?;
            println!("api_token updated in config");
        }
    }
    Ok(())
}

async fn handle_workspace(command: WorkspaceCommand, client: &ApiClient, config: &mut CliConfig) -> Result<()> {
    match command.action {
        WorkspaceAction::List => {
            for workspace in client.list_workspaces().await? {
                println!("{}\t{}", workspace.id, workspace.name);
            }
        }
        WorkspaceAction::New { name } => {
            let workspace = client.create_workspace(&name).await?;
            config.active_workspace_id = Some(workspace.id.clone());
            config.active_workspace_name = Some(workspace.name.clone());
            config.save()?;
            println!("created workspace {} ({})", workspace.name, workspace.id);
        }
        WorkspaceAction::Use { value } => {
            let workspaces = client.list_workspaces().await?;
            let workspace = workspaces
                .into_iter()
                .find(|item| item.id == value || item.name == value)
                .ok_or_else(|| anyhow!("workspace not found: {}", value))?;
            config.active_workspace_id = Some(workspace.id.clone());
            config.active_workspace_name = Some(workspace.name.clone());
            config.save()?;
            println!("using workspace {} ({})", workspace.name, workspace.id);
        }
    }
    Ok(())
}

async fn handle_chat(command: ChatCommand, client: &ApiClient, config: &mut CliConfig) -> Result<()> {
    let workspace_id = resolve_workspace_id(client, command.workspace, config).await?;
    if let Some(from_ref) = command.from_ref {
        config.active_ref = Some(classify_ref(&from_ref));
        config.save()?;
    }
    println!("chatting in workspace {}", workspace_id);
    loop {
        print!("ct> ");
        io::stdout().flush().ok();
        let mut line = String::new();
        io::stdin().read_line(&mut line)?;
        let prompt = line.trim();
        if prompt.is_empty() {
            continue;
        }
        if prompt.starts_with('/') {
            if prompt == "/exit" {
                break;
            }
            handle_inline_command(prompt, client, config).await?;
            continue;
        }
        let request = build_chat_request(prompt, config);
        let mut next_ref = config.active_ref.clone();
        let mut printed_tokens = false;
        client
            .stream_chat(&workspace_id, &request, |event| {
                match event.event.as_str() {
                    "token" => {
                        if let Some(text) = event.data.get("text").and_then(|value| value.as_str()) {
                            printed_tokens = true;
                            print!("{}", text);
                            io::stdout().flush().ok();
                        }
                    }
                    "assistant_final" => {
                        if printed_tokens {
                            println!();
                        }
                    }
                    "node_saved" => {
                        next_ref = next_active_ref_from_event(event.data.clone());
                    }
                    "summary_status" => {
                        if let Some(status) = event.data.get("status").and_then(|value| value.as_str()) {
                            println!("[summary:{}]", status);
                        }
                    }
                    "tool_call" | "tool_result" => {
                        println!("{}", event.data);
                    }
                    "error" => {
                        return Err(anyhow!("server error: {}", event.data));
                    }
                    _ => {}
                }
                Ok(())
            })
            .await?;
        config.active_ref = next_ref;
        config.save()?;
    }
    Ok(())
}

async fn handle_tree(command: TreeCommand, client: &ApiClient, config: &CliConfig) -> Result<()> {
    let workspace_id = config
        .active_workspace_id
        .clone()
        .context("no active workspace configured")?;
    let tree = client.get_tree(&workspace_id).await?;
    if command.all || (command.branch.is_none() && command.node.is_none()) {
        for line in render_workspace_lines(&tree) {
            println!("{}", line);
        }
        return Ok(());
    }
    if let Some(branch_name) = command.branch {
        let branch = tree
            .branches
            .iter()
            .find(|branch| branch.name == branch_name)
            .ok_or_else(|| anyhow!("branch not found: {}", branch_name))?;
        println!(
            "branch {} head={} base={}",
            branch.name,
            branch.head_node_id.clone().unwrap_or_else(|| "-".to_string()),
            branch.base_node_id.clone().unwrap_or_else(|| "-".to_string())
        );
    }
    if let Some(node_id) = command.node {
        let node = tree
            .nodes
            .iter()
            .find(|node| node.id == node_id)
            .ok_or_else(|| anyhow!("node not found: {}", node_id))?;
        println!("{}", render_node_line(node));
        if let Some(summary) = &node.latest_summary {
            println!("summary: {}", summary);
        }
    }
    Ok(())
}

fn handle_checkout(command: CheckoutCommand, config: &mut CliConfig) -> Result<()> {
    config.active_ref = Some(classify_ref(&command.value));
    config.save()?;
    println!("checked out {}", command.value);
    Ok(())
}

async fn handle_branch(command: BranchCommand, client: &ApiClient, config: &CliConfig) -> Result<()> {
    let workspace_id = config
        .active_workspace_id
        .clone()
        .context("no active workspace configured")?;
    match command.action {
        BranchAction::List => {
            let branches = client.list_branches(&workspace_id).await?;
            for line in render_branch_lines(&branches) {
                println!("{}", line);
            }
        }
        BranchAction::Rename { branch, new_name } => {
            let branches = client.list_branches(&workspace_id).await?;
            let found = branches
                .iter()
                .find(|item| item.name == branch || item.id == branch)
                .ok_or_else(|| anyhow!("branch not found: {}", branch))?;
            let renamed = client.rename_branch(&workspace_id, &found.id, &new_name).await?;
            println!("renamed {} -> {}", branch, renamed.name);
        }
    }
    Ok(())
}

async fn handle_show(command: ShowCommand, client: &ApiClient, config: &CliConfig) -> Result<()> {
    let workspace_id = config
        .active_workspace_id
        .clone()
        .context("no active workspace configured")?;
    if command.trace {
        let trace = client.get_trace(&workspace_id, &command.node_id).await?;
        println!("run {} model {}", trace.run_id, trace.model_name);
        if let Some(summary) = trace.summary {
            println!("summary: {}", summary);
        }
        for event in trace.events {
            println!("#{} {} {}", event.sequence, event.event_type, event.payload_json);
        }
    } else {
        let node = client.get_node(&workspace_id, &command.node_id).await?;
        println!("{}", render_node_line(&node));
        if let Some(message) = node.latest_assistant_message {
            println!("assistant: {}", message);
        }
        if let Some(summary) = node.latest_summary {
            println!("summary: {}", summary);
        }
    }
    Ok(())
}

async fn handle_inline_command(prompt: &str, client: &ApiClient, config: &mut CliConfig) -> Result<()> {
    let parts: Vec<&str> = prompt.split_whitespace().collect();
    match parts.as_slice() {
        ["/tree"] => handle_tree(
            TreeCommand {
                all: true,
                branch: None,
                node: None,
            },
            client,
            config,
        )
        .await,
        ["/checkout", value] => handle_checkout(CheckoutCommand { value: value.to_string() }, config),
        ["/branch", "list"] => {
            handle_branch(BranchCommand { action: BranchAction::List }, client, config).await
        }
        ["/branch", "rename", branch, new_name] => {
            handle_branch(
                BranchCommand {
                    action: BranchAction::Rename {
                        branch: branch.to_string(),
                        new_name: new_name.to_string(),
                    },
                },
                client,
                config,
            )
            .await
        }
        ["/show", node_id] => {
            handle_show(
                ShowCommand {
                    node_id: node_id.to_string(),
                    trace: false,
                },
                client,
                config,
            )
            .await
        }
        _ => Err(anyhow!("unsupported inline command: {}", prompt)),
    }
}

async fn resolve_workspace_id(explicit_client: &ApiClient, explicit: Option<String>, config: &CliConfig) -> Result<String> {
    if let Some(value) = explicit {
        let workspaces = explicit_client.list_workspaces().await?;
        let workspace = workspaces
            .into_iter()
            .find(|item| item.id == value || item.name == value)
            .ok_or_else(|| anyhow!("workspace not found: {}", value))?;
        return Ok(workspace.id);
    }
    config
        .active_workspace_id
        .clone()
        .context("no active workspace configured")
}

fn classify_ref(value: &str) -> ActiveRef {
    if value.contains('/') || value == "main" {
        ActiveRef {
            kind: "branch".to_string(),
            value: value.to_string(),
        }
    } else {
        ActiveRef {
            kind: "node".to_string(),
            value: value.to_string(),
        }
    }
}

fn build_chat_request(prompt: &str, config: &CliConfig) -> ChatRequest {
    match &config.active_ref {
        Some(active) if active.kind == "branch" => ChatRequest {
            prompt: prompt.to_string(),
            parent_node_id: None,
            branch_name: Some(active.value.clone()),
        },
        Some(active) => ChatRequest {
            prompt: prompt.to_string(),
            parent_node_id: Some(active.value.clone()),
            branch_name: None,
        },
        None => ChatRequest {
            prompt: prompt.to_string(),
            parent_node_id: None,
            branch_name: Some("main".to_string()),
        },
    }
}

fn next_active_ref_from_event(data: serde_json::Value) -> Option<ActiveRef> {
    if let Some(branch_name) = data.get("branch_name").and_then(|value| value.as_str()) {
        return Some(ActiveRef {
            kind: "branch".to_string(),
            value: branch_name.to_string(),
        });
    }
    data.get("node_id")
        .and_then(|value| value.as_str())
        .map(|node_id| ActiveRef {
            kind: "node".to_string(),
            value: node_id.to_string(),
        })
}

fn normalize_base_url(url: &str) -> Result<String> {
    let trimmed = url.trim().trim_end_matches('/');
    if trimmed.is_empty() {
        return Err(anyhow!("base url cannot be empty"));
    }
    if !(trimmed.starts_with("http://") || trimmed.starts_with("https://")) {
        return Err(anyhow!("base url must start with http:// or https://"));
    }
    Ok(trimmed.to_string())
}

fn normalize_api_token(token: &str) -> Result<String> {
    let trimmed = token.trim();
    if trimmed.is_empty() {
        return Err(anyhow!("api token cannot be empty"));
    }
    Ok(trimmed.to_string())
}

fn mask_token(token: &str) -> String {
    if token.len() <= 8 {
        return "********".to_string();
    }
    format!("{}***{}", &token[..4], &token[token.len() - 2..])
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn build_chat_request_defaults_to_main_branch() {
        let config = CliConfig::default();
        let request = build_chat_request("hello", &config);
        assert_eq!(request.branch_name.as_deref(), Some("main"));
        assert!(request.parent_node_id.is_none());
    }

    #[test]
    fn node_saved_event_prefers_branch_reference() {
        let data = serde_json::json!({
            "node_id": "n-1",
            "branch_name": "main"
        });
        let active = next_active_ref_from_event(data).expect("ref should exist");
        assert_eq!(active.kind, "branch");
        assert_eq!(active.value, "main");
    }

    #[test]
    fn normalize_base_url_trims_trailing_slash() {
        let url = normalize_base_url("http://127.0.0.1:8000/").expect("url should normalize");
        assert_eq!(url, "http://127.0.0.1:8000");
    }

    #[test]
    fn normalize_base_url_requires_http_scheme() {
        let error = normalize_base_url("127.0.0.1:8000").expect_err("url should fail");
        assert!(error.to_string().contains("http:// or https://"));
    }

    #[test]
    fn normalize_api_token_rejects_empty_value() {
        let error = normalize_api_token("   ").expect_err("token should fail");
        assert!(error.to_string().contains("cannot be empty"));
    }
}
