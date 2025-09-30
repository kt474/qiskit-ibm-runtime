use pyo3::prelude::*;

pub mod backends;  
pub mod jobs;      

#[pymodule]
fn rust_api(py: Python, m: &PyModule) -> PyResult<()> {
    backends::register(py, m)?;
    Ok(())
}