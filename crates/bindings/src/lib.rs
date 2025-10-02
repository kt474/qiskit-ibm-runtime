use pyo3::prelude::*;
pub mod backends; 

#[pymodule]
fn rust_api(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(backends::list_backends, m)?)?;
    m.add_function(wrap_pyfunction!(backends::get_backend_status, m)?)?;
    Ok(())
}