use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use ibm_quantum_platform_api::{apis, apis::configuration};

fn make_config(base_url: &str, token: &str, crn: &str) -> configuration::Configuration {
    configuration::Configuration {
        base_path: base_url.to_string(),
        user_agent: Some(String::from("qiskit-ibm-runtime-rust-client")),
        client: reqwest::Client::new(),
        basic_auth: None,
        oauth_access_token: None,
        bearer_access_token: None,
        api_key: Some(configuration::ApiKey {
            prefix: Some(String::from("apikey")),           
            key: token.to_string(), 
        }),
        crn: Some(crn.to_string())
    }
}
#[pyfunction]
pub fn get_usage(base_url: String, token: String, crn: String) -> PyResult<String> {
    let config = make_config(&base_url, &token, &crn);
    let rt = tokio::runtime::Runtime::new()
        .map_err(|e| PyRuntimeError::new_err(format!("Tokio runtime error: {e}")))?;

    let resp = rt
        .block_on(apis::instances_api::get_usage(
            &config,
            Some("2025-05-01")
        ))
        .map_err(|e| {
            PyRuntimeError::new_err(format!("API call failed: {e:?}"))
        })?;

    serde_json::to_string_pretty(&resp)
        .map_err(|e| PyRuntimeError::new_err(format!("JSON serialization failed: {e}")))
}