use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;

use ibm_quantum_platform_api::{apis, apis::configuration};

fn make_config(base_url: &str, token: &str) -> configuration::Configuration {
    configuration::Configuration {
        base_path: base_url.to_string(),
        user_agent: Some("qiskit-ibm-runtime-rust-client".into()),
        client: reqwest::Client::new(),
        basic_auth: None,
        oauth_access_token: None,
        bearer_access_token: Some(token.to_string()),
        api_key: None,
        
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

    Ok(resp.devices.unwrap_or_default().into_iter().map(|b| b.name).collect())
}

// #[pyfunction]
// fn get_backend_status_py(base_url: String, token: String, backend_id: String) -> PyResult<String> {
//     let config = make_config(&base_url, &token);
//     let rt = tokio::runtime::Runtime::new().unwrap(); // TODO don't use unwrap
//     // let rt = tokio::runtime::Runtime::new()
//     // .map_err(|e| PyRuntimeError::new_err(format!("Tokio runtime error: {e}")))?;

//     let resp = rt
//         .block_on(apis::backends_api::get_backend_status(&config, &backend_id, Some("2025-01-01")))
//         .map_err(|e| PyRuntimeError::new_err(format!("API error: {e}")))?;

//     serde_json::to_string(&resp)
//         .map_err(|e| PyRuntimeError::new_err(format!("Serialization failed: {e}")))
// }

// #[pyfunction]
// fn get_backend_configuration_py(base_url: String, token: String, crn: String, backend_id: String) -> PyResult<String> {
//     let config = make_config(&base_url, &token);
//     let rt = tokio::runtime::Runtime::new().unwrap();

//     let resp = rt
//         .block_on(apis::backends_api::get_backend_configuration(
//             &config,
//             &backend_id,
//             &crn,
//             Some("2025-01-01"),
//         ))
//         .map_err(|e| PyRuntimeError::new_err(format!("API error: {e}")))?;

//     serde_json::to_string(&resp)
//         .map_err(|e| PyRuntimeError::new_err(format!("Serialization failed: {e}")))
// }

// #[pyfunction]
// fn get_backend_properties_py(base_url: String, token: String, crn: String, backend_id: String) -> PyResult<String> {
//     let config = make_config(&base_url, &token);
//     let rt = tokio::runtime::Runtime::new().unwrap();

//     let resp = rt
//         .block_on(apis::backends_api::get_backend_properties(
//             &config,
//             &backend_id,
//             &crn,
//             Some("2025-01-01"),
//             None, 
//         ))
//         .map_err(|e| PyRuntimeError::new_err(format!("API error: {e}")))?;

//     serde_json::to_string(&resp)
//         .map_err(|e| PyRuntimeError::new_err(format!("Serialization failed: {e}")))
// }

// pub fn register(_py: Python, m: &PyModule) -> PyResult<()> {
//     m.add_function(wrap_pyfunction!(list_backends_py, m)?)?;
//     m.add_function(wrap_pyfunction!(get_backend_status_py, m)?)?;
//     m.add_function(wrap_pyfunction!(get_backend_configuration_py, m)?)?;
//     m.add_function(wrap_pyfunction!(get_backend_properties_py, m)?)?;
//     Ok(())
// }