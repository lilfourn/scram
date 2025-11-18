# Project Scram: Overview

## The Future of Data Acquisition for Machine Learning

Scram is a next-generation, intelligent web crawling agent designed specifically for the needs of data scientists and machine learning engineers. It addresses the critical bottleneck in modern data acquisition: acquiring clean, structured, and relevant data from the web at scale.

Traditional web scrapers often require extensive manual configuration, struggle against modern anti-bot technologies, and deliver messy data needing significant cleaning. Scram moves beyond these limitations by integrating advanced AI directly into the crawling and extraction workflow.

## How It Works

Scram operates through a sophisticated yet intuitive Terminal User Interface (TUI). The process is driven by user intent:

1.  **Define the Goal:** The user provides starting URLs and describes the desired data in natural language (e.g., "Extract product names, prices, specifications, and reviews from this site").
2.  **Intelligent Navigation:** Scram doesn't blindly crawl every link. Powered by Google Gemini, it analyzes the content of each page to determine its semantic relevance to the objective, ensuring efficient and targeted crawling.
3.  **Structured Extraction:** Scram dynamically generates a data schema based on the user's request. The AI precisely extracts only the requested information, automatically cleaning it and validating it against the schema.
4.  **Review and Refine:** Users monitor progress via a live dashboard. If the results need adjustment, the user can provide feedback in natural language, and Scram will instantly adapt its extraction strategy.
5.  **ML-Ready Export:** Once approved, the data is exported in formats ready for immediate use in ML pipelines (e.g., Parquet, CSV, JSONL).

## Key Features

*   **AI-Driven Intelligence:** Utilizing Google Gemini and the LangGraph framework, Scram understands user intent, navigates semantically, and extracts data with human-like precision.
*   **ML-Ready Data by Default:** Designed to output structured, validated data, eliminating extensive post-scrape cleaning.
*   **Extreme Performance:** Built on a high-concurrency asynchronous architecture, Scram is capable of processing over 1000 pages per minute.
*   **Advanced Anti-Bot Evasion:** Featuring state-of-the-art evasion techniques, including TLS fingerprint spoofing, residential proxy rotation, and stealth browser automation, Scram reliably accesses data protected by systems like Cloudflare.
*   **Professional TUI:** A modern, interactive terminal interface provides a seamless user experience with live dashboards, real-time logging, and interactive data previews.

Scram is not just a scraper; it's an intelligent data acquisition agent that understands what you are looking for and delivers it ready for analysis.