use pyo3::prelude::*;
pub mod backends; 
pub mod instances;
pub mod sessions;

#[pymodule]
fn rust_api(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(backends::list_backends, m)?)?;
    m.add_function(wrap_pyfunction!(backends::get_backend_status, m)?)?;
    m.add_function(wrap_pyfunction!(backends::get_backend_configuration, m)?)?;
    m.add_function(wrap_pyfunction!(backends::get_backend_properties, m)?)?;
    m.add_function(wrap_pyfunction!(instances::get_usage, m)?)?;
    m.add_function(wrap_pyfunction!(sessions::create_session, m)?)?;
    m.add_function(wrap_pyfunction!(sessions::delete_session, m)?)?;
    Ok(())
}