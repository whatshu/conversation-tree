use anyhow::{Context, Result};
use dirs::config_dir;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ActiveRef {
    pub kind: String,
    pub value: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CliConfig {
    pub server_url: String,
    pub api_token: String,
    pub active_workspace_id: Option<String>,
    pub active_workspace_name: Option<String>,
    pub active_ref: Option<ActiveRef>,
}

impl Default for CliConfig {
    fn default() -> Self {
        Self {
            server_url: "http://127.0.0.1:8000".to_string(),
            api_token: "change-me-local-token".to_string(),
            active_workspace_id: None,
            active_workspace_name: None,
            active_ref: None,
        }
    }
}

impl CliConfig {
    pub fn path() -> Result<PathBuf> {
        let root = config_dir().context("unable to resolve config directory")?;
        Ok(root.join("conversation-tree").join("config.toml"))
    }

    pub fn load() -> Result<Self> {
        let path = Self::path()?;
        if !path.exists() {
            return Ok(Self::default());
        }
        let raw = fs::read_to_string(&path)
            .with_context(|| format!("failed to read config file at {}", path.display()))?;
        Ok(toml::from_str(&raw).context("failed to parse config file")?)
    }

    pub fn save(&self) -> Result<()> {
        let path = Self::path()?;
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)
                .with_context(|| format!("failed to create config directory {}", parent.display()))?;
        }
        let raw = toml::to_string_pretty(self).context("failed to serialize config")?;
        fs::write(&path, raw).with_context(|| format!("failed to write config file {}", path.display()))?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_config_is_local_first() {
        let config = CliConfig::default();
        assert_eq!(config.server_url, "http://127.0.0.1:8000");
        assert_eq!(config.api_token, "change-me-local-token");
    }
}
