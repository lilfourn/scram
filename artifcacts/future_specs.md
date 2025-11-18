# Project Scram: Enhanced Technical Specifications (R&D Roadmap)

## 1. Overview

This document outlines the advanced specifications for evolving Scram into a world-leading, autonomous data acquisition platform for Machine Learning. It introduces five key innovations: the Visual-Semantic Engine (VSE), the Mirage Behavioral Synthesis Engine, the Rust High-Performance Core with Adaptive Model Distillation, Autonomous Knowledge Graph (KG) Construction, and Provable Data Provenance.

## 2. Architectural Evolution

The architecture will evolve into a hybrid Python/Rust system.

- **Python (Agent Core, AI Logic, TUI):** Remains the orchestrator (LangGraph), handling high-level logic, complex AI tasks (MLLMs, the "Teacher" models), user interaction (Textual), and data structuring.
- **Rust (High-Performance Core - HPC):** Introduced to handle massive concurrency (Tokio), low-level networking (TLS spoofing), browser control (CDP), behavioral synthesis (Mirage), and high-speed execution of distilled models (the "Student" models).
- **Interoperability:** Communication between Python and Rust will be managed via PyO3/Maturin, compiling the Rust core into a Python-callable library for low-latency interaction.

## 3. Innovation Specifications

### 3.1. Visual-Semantic Engine (VSE) and Self-Healing

- **Objective:** Eliminate extraction brittleness caused by reliance on DOM selectors.
- **Architecture:** A multimodal system combining Computer Vision (CV) and Multimodal LLMs (MLLMs).
- **Components:**
  - **Visual Segmentation:** Utilize LayoutLMv3 or similar models to understand page layout hierarchy and visual cues.
  - **DOM-Visual Mapper:** Correlates visual bounding boxes with DOM elements and the Accessibility Tree (AOM).
  - **Multimodal AI Core:** (e.g., Gemini Vision) Extracts data based on visual context rather than strict selectors.
- **Self-Healing (Temporal Resonance):**
  - Must automatically detect extraction failures (Pydantic validation errors).
  - Must maintain multi-modal fingerprints (Semantic Context, Visual Location, DOM Embedding) of desired data.
  - Must use these fingerprints to autonomously locate data when site structure changes and regenerate extraction logic.

### 3.2. Mirage Behavioral Synthesis Engine (Evasion)

- **Objective:** Achieve behavioral camouflage to evade advanced ML-based bot detection.
- **Technology:** Generative Adversarial Networks (GANs) trained on real human browsing data.
- **Implementation:** Must be implemented in the **Rust HPC** for microsecond precision control via the Chrome DevTools Protocol (CDP).
- **Features:**
  - **Humanized Interaction:** Synthesize realistic mouse telemetry, variable scrolling speeds, and typing cadence.
  - **Warm-up Protocol:** Autonomous navigation of unrelated sites to build realistic cookie history and behavioral baselines.
  - **Deep Environment Spoofing:** Active randomization of Canvas, WebGL, AudioContext, and hardware fingerprints.

### 3.3. Adaptive Model Distillation and Rust HPC

- **Objective:** Achieve massive scale (millions of pages) by optimizing speed and reducing reliance on expensive MLLMs.
- **Architecture:** Teacher-Student model.
  - **Teacher (VSE/MLLM):** Analyzes initial pages of a template.
  - **Student (Distilled Model):** A small, fast model (e.g., distilled BERT) trained by the Teacher for a specific template.
- **Rust Core Implementation:**
  - The Rust engine executes the Student models at high throughput.
  - Must support optimized inference runtimes (e.g., ONNX Runtime).
- **Adaptive Switching:** The system must automatically switch between the Teacher and Student. If Student confidence drops, the request must escalate back to the Teacher.

### 3.4. Autonomous Knowledge Graph (KG) Construction

- **Objective:** Deliver interconnected, standardized data rather than flat tables.
- **Zero-Shot Structural Inference:** A meta-learning model that analyzes a URL and automatically predicts the optimal ML schema (Entities and Relationships).
- **Entity Resolution:** Identify and link identical entities across different pages using vector similarity.
- **Cross-Session Ontological Alignment (CSOA):** Must map session-specific data structures to a Universal ML Ontology.

### 3.5. Provable Data Provenance

- **Objective:** Ensure enterprise-grade data integrity and traceability.
- **Chain of Custody:** Every data point must have verifiable metadata: timestamp, source URL, schema version, AI model ID (Teacher/Student), and confidence score.
- **Visual Proof:** Capture a screenshot at the time of extraction with a bounding box highlighting the exact location of the extracted data.
- **TUI Integration:** The TUI must include a "Verify" feature to instantly view the visual proof and metadata.

## 4. Enhanced Technology Stack Additions

| Domain                      | Technologies                                            |
| --------------------------- | ------------------------------------------------------- |
| **High-Performance Core**   | Rust (Language), Tokio (Async Runtime)                  |
| **Rust Networking/Evasion** | `Reqwest`, `rustls` (Native TLS spoofing)               |
| **Rust Browser Control**    | `chromiumoxide` or `headless_chrome` (CDP control)      |
| **Interoperability**        | PyO3, Maturin                                           |
| **AI/ML (Multimodal)**      | Gemini Vision, LayoutLMv3, PyTorch/TensorFlow           |
| **AI/ML (Behavioral)**      | TensorFlow/PyTorch (for GAN development)                |
| **AI/ML (Distillation)**    | DistilBERT, ONNX Runtime (Rust integration)             |
| **Data Structures**         | Graph Databases (e.g., Neo4j), Vector DBs (e.g., Faiss) |
