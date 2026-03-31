use anyhow::{Context, Result};
use dirs::config_dir;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::PathBuf;

const DEFAULT_SERVER_URL: &str = "http://127.0.0.1:8000";
const DEFAULT_API_TOKEN: &str = "change-me-local-token";
const ENV_SERVER_URL: &str = "CT_SERVER_URL";
const ENV_API_TOKEN: &str = "CT_API_TOKEN";

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
            server_url: DEFAULT_SERVER_URL.to_string(),
            api_token: DEFAULT_API_TOKEN.to_string(),
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

    pub fn resolved_server_url(&self) -> Result<String> {
        Ok(self.resolve_value(ENV_SERVER_URL, &self.server_url)?.0)
    }

    pub fn resolved_api_token(&self) -> Result<String> {
        Ok(self.resolve_value(ENV_API_TOKEN, &self.api_token)?.0)
    }

    pub fn server_url_source(&self) -> Result<&'static str> {
        Ok(self.resolve_value(ENV_SERVER_URL, &self.server_url)?.1)
    }

    pub fn api_token_source(&self) -> Result<&'static str> {
        Ok(self.resolve_value(ENV_API_TOKEN, &self.api_token)?.1)
    }

    fn resolve_value(&self, env_key: &str, config_value: &str) -> Result<(String, &'static str)> {
        if let Ok(value) = env::var(env_key) {
            if !value.trim().is_empty() {
                return Ok((value.trim().to_string(), "env"));
            }
        }

        if let Some(value) = load_dotenv()?.get(env_key) {
            if !value.trim().is_empty() {
                return Ok((value.trim().to_string(), ".env"));
            }
        }

        if !config_value.trim().is_empty()
            && !is_default_placeholder(env_key, config_value)
        {
            return Ok((config_value.trim().to_string(), "config"));
        }

        Ok((config_value.trim().to_string(), "default"))
    }
}

fn is_default_placeholder(env_key: &str, value: &str) -> bool {
    match env_key {
        ENV_SERVER_URL => value == DEFAULT_SERVER_URL,
        ENV_API_TOKEN => value == DEFAULT_API_TOKEN,
        _ => false,
    }
}

fn load_dotenv() -> Result<HashMap<String, String>> {
    for candidate in dotenv_candidates()? {
        if candidate.exists() {
            return parse_dotenv(&candidate);
        }
    }
    Ok(HashMap::new())
}

fn dotenv_candidates() -> Result<Vec<PathBuf>> {
    let mut candidates = Vec::new();
    let current = env::current_dir().context("unable to resolve current directory")?;
    for ancestor in current.ancestors() {
        candidates.push(ancestor.join(".env"));
    }
    Ok(candidates)
}

fn parse_dotenv(path: &PathBuf) -> Result<HashMap<String, String>> {
    let raw = fs::read_to_string(path)
        .with_context(|| format!("failed to read env file at {}", path.display()))?;
    let mut values = HashMap::new();
    for line in raw.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }
        if let Some((key, value)) = trimmed.split_once('=') {
            let clean_key = key.trim().to_string();
            let clean_value = value.trim().trim_matches('"').trim_matches('\'').to_string();
            values.insert(clean_key, clean_value);
        }
    }
    Ok(values)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_config_is_local_first() {
        let config = CliConfig::default();
        assert_eq!(config.server_url, DEFAULT_SERVER_URL);
        assert_eq!(config.api_token, DEFAULT_API_TOKEN);
    }

    #[test]
    fn explicit_config_values_can_be_selected_as_source() {
        let config = CliConfig {
            server_url: "http://localhost:9999".to_string(),
            api_token: "token-from-config".to_string(),
            active_workspace_id: None,
            active_workspace_name: None,
            active_ref: None,
        };
        let (server_url, server_source) = config
            .resolve_value("CT_UNUSED_SERVER_URL", &config.server_url)
            .expect("server url should resolve");
        let (api_token, api_source) = config
            .resolve_value("CT_UNUSED_API_TOKEN", &config.api_token)
            .expect("api token should resolve");
        assert_eq!(server_url, "http://localhost:9999");
        assert_eq!(server_source, "config");
        assert_eq!(api_token, "token-from-config");
        assert_eq!(api_source, "config");
    }

    #[test]
    fn parse_dotenv_supports_simple_key_value_lines() {
        let temp_dir = env::temp_dir().join("ct-config-test.env");
        fs::write(
            &temp_dir,
            "CT_SERVER_URL=http://localhost:9000\nCT_API_TOKEN=test-token\n",
        )
        .expect("should write temp env");
        let parsed = parse_dotenv(&temp_dir).expect("dotenv should parse");
        assert_eq!(parsed.get(ENV_SERVER_URL).map(String::as_str), Some("http://localhost:9000"));
        assert_eq!(parsed.get(ENV_API_TOKEN).map(String::as_str), Some("test-token"));
        fs::remove_file(&temp_dir).ok();
    }
}
