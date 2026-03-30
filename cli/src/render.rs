use crate::client::{BranchDto, NodeDto, TreeDto};

pub fn render_workspace_lines(tree: &TreeDto) -> Vec<String> {
    let mut lines = vec![format!("workspace: {} ({})", tree.workspace.name, tree.workspace.id)];
    for branch in &tree.branches {
        lines.push(format!(
            "branch {} -> head={} base={}",
            branch.name,
            branch.head_node_id.clone().unwrap_or_else(|| "-".to_string()),
            branch.base_node_id.clone().unwrap_or_else(|| "-".to_string())
        ));
    }
    for node in &tree.nodes {
        lines.push(render_node_line(node));
        if let Some(summary) = &node.latest_summary {
            lines.push(format!("  summary: {}", summary));
        }
    }
    lines
}

pub fn render_node_line(node: &NodeDto) -> String {
    format!(
        "node {} parent={} prompt={}",
        node.id,
        node.parent_node_id.clone().unwrap_or_else(|| "-".to_string()),
        node.user_prompt
    )
}

pub fn render_branch_lines(branches: &[BranchDto]) -> Vec<String> {
    branches
        .iter()
        .map(|branch| {
            format!(
                "{} head={}{}",
                branch.name,
                branch.head_node_id.clone().unwrap_or_else(|| "-".to_string()),
                if branch.auto_named { " [auto]" } else { "" }
            )
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::client::{WorkspaceDto};

    #[test]
    fn render_tree_contains_summary() {
        let tree = TreeDto {
            workspace: WorkspaceDto {
                id: "ws-1".into(),
                name: "default".into(),
                description: None,
                created_at: "now".into(),
                updated_at: "now".into(),
            },
            branches: vec![BranchDto {
                id: "b-1".into(),
                workspace_id: "ws-1".into(),
                name: "main".into(),
                base_node_id: Some("n-1".into()),
                head_node_id: Some("n-2".into()),
                auto_named: false,
                created_at: "now".into(),
                updated_at: "now".into(),
            }],
            nodes: vec![NodeDto {
                id: "n-1".into(),
                workspace_id: "ws-1".into(),
                parent_node_id: None,
                user_prompt: "hello".into(),
                created_at: "now".into(),
                latest_run_id: Some("r-1".into()),
                latest_assistant_message: Some("hi".into()),
                latest_summary: Some("assistant did work".into()),
            }],
        };
        let rendered = render_workspace_lines(&tree).join("\n");
        assert!(rendered.contains("assistant did work"));
        assert!(rendered.contains("branch main"));
    }
}
