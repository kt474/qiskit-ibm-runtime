use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;

use ibm_quantum_platform_api::{apis, apis::configuration};

fn make_config(base_url: &str, token: &str) -> configuration::Configuration {
    configuration::Configuration {
        base_path: base_url.to_string(),
        bearer_access_token: Some(token.to_string()),
        user_agent: Some("qiskit-ibm-runtime-rust-client".into()),
        api_key: None,
        client: reqwest::Client::new(),
    }
}

#[pyfunction]
fn list_backends_py(base_url: String, token: String, crn: String) -> PyResult<Vec<String>> {
    let config = make_config(&base_url, &token);

    let rt = tokio::runtime::Runtime::new()
        .map_err(|e| PyRuntimeError::new_err(format!("Failed to start Tokio runtime: {e}")))?;

    let resp = rt
        .block_on(apis::backends_api::list_backends(&config, Some("2025-01-01"), &crn))
        .map_err(|e| PyRuntimeError::new_err(format!("API call failed: {e}")))?;

    Ok(resp.backends.into_iter().map(|b| b.name).collect())
}

pub fn register(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(list_backends_py, m)?)?;
    Ok(())
}