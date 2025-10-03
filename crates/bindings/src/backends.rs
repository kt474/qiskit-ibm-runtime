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
        crn: Some(crn.to_string()),
    }
}

#[pyfunction]
pub fn list_backends(base_url: String, token: String, crn: String) -> PyResult<Vec<String>> {
    let config = make_config(&base_url, &token, &crn);
    let rt = tokio::runtime::Runtime::new()
        .map_err(|e| PyRuntimeError::new_err(format!("Failed to start Tokio runtime: {e}")))?;

    let resp = rt
        .block_on(apis::backends_api::list_backends(&config, Some("2025-05-01"), &crn))
        .map_err(|e| PyRuntimeError::new_err(format!("API call failed: {e}")))?;

    Ok(resp.devices.unwrap_or_default().into_iter().map(|b| b.name).collect())
}

#[pyfunction]
pub fn get_backend_status(base_url: String, token: String, backend: String, crn:String) -> PyResult<String> {
    let config = make_config(&base_url, &token, &crn);
    let rt = tokio::runtime::Runtime::new()
    .map_err(|e| PyRuntimeError::new_err(format!("Tokio runtime error: {e}")))?;

    let resp = rt
        .block_on(apis::backends_api::get_backend_status(&config, &backend, &crn, Some("2025-05-01")))
        .map_err(|e| PyRuntimeError::new_err(format!("API error: {e}")))?;

    serde_json::to_string(&resp)
        .map_err(|e| PyRuntimeError::new_err(format!("Serialization failed: {e}")))
}

#[pyfunction]
pub fn get_backend_configuration(base_url: String, token: String, crn: String, backend: String) -> PyResult<String> {
    let config = make_config(&base_url, &token, &crn);
    let rt = tokio::runtime::Runtime::new()
    .map_err(|e| PyRuntimeError::new_err(format!("Tokio runtime error: {e}")))?;

    let resp = rt
        .block_on(apis::backends_api::get_backend_configuration(
            &config,
            &backend,
            &crn,
            Some("2025-05-01"),
        ))
        .map_err(|e| PyRuntimeError::new_err(format!("API error: {e}")))?;

    serde_json::to_string(&resp)
        .map_err(|e| PyRuntimeError::new_err(format!("Serialization failed: {e}")))
}

#[pyfunction]
pub fn get_backend_properties(base_url: String, token: String, crn: String, backend: String) -> PyResult<String> {
    let config = make_config(&base_url, &token, &crn);
    let rt = tokio::runtime::Runtime::new()
    .map_err(|e| PyRuntimeError::new_err(format!("Tokio runtime error: {e}")))?;

    let resp = rt
        .block_on(apis::backends_api::get_backend_properties(
            &config,
            &backend,
            &crn,
            Some("2025-01-01"),
            None, 
        ))
        .map_err(|e| PyRuntimeError::new_err(format!("API error: {e}")))?;

    serde_json::to_string(&resp)
        .map_err(|e| PyRuntimeError::new_err(format!("Serialization failed: {e}")))
}

