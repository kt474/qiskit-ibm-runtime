use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use ibm_quantum_platform_api::{apis, apis::configuration, models};

fn make_config(base_url: &str, token: &str, crn: &str) -> configuration::Configuration {
    configuration::Configuration {
        base_path: base_url.to_string(),
        user_agent: Some("qiskit-ibm-runtime-rust-client".into()),
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
pub fn create_session(
    base_url: String,
    token: String,
    backend: Option<String>,
    mode: Option<String>, 
    max_ttl: Option<i32>,
    crn: String
) -> PyResult<String> {
    let config = make_config(&base_url, &token, &crn);

    let mode_enum = match mode.as_deref() {
        Some("dedicated") => models::create_session_request_one_of::Mode::Dedicated,
        _ => models::create_session_request_one_of::Mode::Batch, // Default
    };

    let request_one_of = models::CreateSessionRequestOneOf {
        max_ttl,
        mode: mode_enum,
        backend: backend.clone(),
        backend_name: backend, 
    };

    let request = models::CreateSessionRequest::CreateSessionRequestOneOf(
        Box::new(request_one_of)
    );

    dbg!(&request);

    let rt = tokio::runtime::Runtime::new()
        .map_err(|e| PyRuntimeError::new_err(format!("Tokio runtime error: {e}")))?;

    let resp = rt
        .block_on(apis::sessions_api::create_session(
            &config,
            Some("2025-05-01"),
            Some(request),
        ))
        .map_err(|e| PyRuntimeError::new_err(format!("API call failed: {e:?}")))?;
    
    dbg!(&resp);
    serde_json::to_string_pretty(&resp)
        .map_err(|e| PyRuntimeError::new_err(format!("JSON serialization failed: {e}")))
}
