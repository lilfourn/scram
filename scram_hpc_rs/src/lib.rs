use pyo3::prelude::*;
use pyo3::types::PyBytes;
use reqwest::Client;
use std::collections::HashMap;

mod browser;
mod inference;

#[pyfunction]
fn fetch_url(py: Python, url: String, headers: Option<HashMap<String, String>>) -> PyResult<&PyAny> {
    pyo3_asyncio::tokio::future_into_py(py, async move {
        let client = Client::builder()
            .use_rustls_tls()
            .build()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        let mut request_builder = client.get(&url);

        if let Some(h) = headers {
            for (k, v) in h {
                request_builder = request_builder.header(k, v);
            }
        }

        let response = request_builder
            .send()
            .await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        let status = response.status().as_u16();
        let text = response
            .text()
            .await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        Ok((text, status))
    })
}

#[pyfunction]
fn fetch_browser(py: Python, url: String, headless: bool) -> PyResult<&PyAny> {
    pyo3_asyncio::tokio::future_into_py(py, async move {
        let browser = browser::MirageBrowser::new(headless)
            .await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        
        let (content, status, screenshot) = browser
            .fetch_page(&url)
            .await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        Ok((content, status, screenshot))
    })
}

#[pyfunction]
fn run_inference(_py: Python, model_path: String, dom_features: Vec<f32>) -> PyResult<Vec<f32>> {
    let engine = inference::InferenceEngine::new(&model_path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
    
    let result = engine.extract(dom_features)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        
    Ok(result)
}

#[pymodule]
fn scram_hpc_rs(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(fetch_url, m)?)?;
    m.add_function(wrap_pyfunction!(fetch_browser, m)?)?;
    m.add_function(wrap_pyfunction!(run_inference, m)?)?;
    Ok(())
}
