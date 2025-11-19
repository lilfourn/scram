import logging
import asyncio
from typing import Dict, Any, List

from src.agent.state import AgentState
from src.fetching.engine import FetchingEngine
from src.ai.gemini import GeminiClient
from src.ai.compression import ContextCompressor
from src.core.events import event_bus
from src.data.export import exporter
from src.data.collector import collector

logger = logging.getLogger(__name__)

# Global instances (to be initialized in main or graph setup)
fetching_engine = FetchingEngine()
gemini_client = GeminiClient()
context_compressor = ContextCompressor(gemini_client)


async def initialization_node(state: AgentState) -> Dict[str, Any]:
    """Initialize the session and generate schema if needed."""
    logger.info(f"Initializing session: {state['session_title']}")
    event_bus.publish("agent_activity", status="Initializing Session")

    # Initialize raw data collector
    collector.set_session(state["session_title"])

    updates = {
        "compressed_history": "Session started.",
        "recent_activity": [],
    }

    if not state.get("data_schema"):
        logger.info("Generating schema from objective...")
        event_bus.publish("agent_activity", status="Generating Schema (AI)")
        try:
            schema = await gemini_client.generate_schema(state["objective"])
            updates["data_schema"] = schema
        except Exception as e:
            logger.error(f"Failed to generate schema: {e}")
            # Fallback schema to prevent crash
            updates["data_schema"] = {
                "type": "object",
                "properties": {"content": {"type": "string"}},
            }

    # Save initial config
    exporter.save_config(
        state["session_title"],
        {
            "objective": state["objective"],
            "schema": updates.get("data_schema", state.get("data_schema")),
            "seed_urls": state.get("url_queue", [])
            + list(state.get("visited_urls", [])),
        },
    )

    return updates


async def crawl_manager_node(state: AgentState) -> Dict[str, Any]:
    """Select the next batch of URLs to crawl."""
    try:
        event_bus.publish("agent_activity", status="Managing Queue")

        queue = state.get("url_queue", [])
        visited = state.get("visited_urls", set())

        # Update Queue Size Stat
        event_bus.publish("stats_update", metric="queue_size", value=len(queue))

        if not queue:
            logger.info("Queue is empty.")
            return {"current_urls": []}

        # Batch size
        from src.core.config import config

        BATCH_SIZE = config.BATCH_SIZE
        batch_urls = []

        # Pop up to BATCH_SIZE unique unvisited URLs

        while queue and len(batch_urls) < BATCH_SIZE:
            next_url = queue.pop(0)
            if next_url not in visited and next_url not in batch_urls:
                batch_urls.append(next_url)

        if not batch_urls:
            # If we drained the queue but found only visited links
            if queue:
                return await crawl_manager_node(state)
            return {"current_urls": []}

        # Template Detection Logic
        # Group URLs by domain/path structure
        # For MVP, we just use the domain as the template ID
        from urllib.parse import urlparse

        template_groups = state.get("template_groups", {})

        for url in batch_urls:
            try:
                domain = urlparse(url).netloc
                if domain not in template_groups:
                    template_groups[domain] = []
                template_groups[domain].append(url)
            except Exception:
                pass

        # Check for optimization triggers (e.g. > 10 successful extractions for a template)
        # This would set optimized_templates in state

        logger.info(f"Selected batch of {len(batch_urls)} URLs")

        # Update recent activity
        recent_activity = state.get("recent_activity", [])
        recent_activity.append(
            f"Crawling batch of {len(batch_urls)} URLs: {batch_urls}"
        )

        return {
            "current_urls": batch_urls,
            "url_queue": queue,
            "template_groups": template_groups,
            "recent_activity": recent_activity,
        }
    except Exception as e:
        logger.error(f"Error in crawl_manager_node: {e}")
        # Return empty current_urls to stop or proceed to finalization safely
        return {"current_urls": []}


async def fetcher_node(state: AgentState) -> Dict[str, Any]:
    """Fetch the content of the current batch of URLs concurrently."""
    urls = state.get("current_urls", [])
    if not urls:
        return {"current_contents": []}

    logger.info(f"Fetching batch: {urls}")
    event_bus.publish("agent_activity", status=f"Fetching {len(urls)} pages")

    async def fetch_single(url: str, worker_id: int) -> tuple[str | None, bytes, bool]:
        event_bus.publish(
            "worker_status", worker_id=worker_id, status=f"Fetching {url}", progress=30
        )

        try:
            # Use the refactored fetching engine which handles rate limiting and escalation
            content, status, screenshot = await fetching_engine.fetch(url)

            if status != 200:
                logger.warning(f"Failed to fetch {url}, status: {status}")
                event_bus.publish(
                    "worker_status", worker_id=worker_id, status="Failed", progress=0
                )
                return None, b"", True

            event_bus.publish(
                "worker_status", worker_id=worker_id, status="Fetched", progress=100
            )
            # Stats update is now handled inside fetching_engine.fetch
            return content, screenshot, False

        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            event_bus.publish(
                "worker_status", worker_id=worker_id, status="Error", progress=0
            )
            return None, b"", True

    # Run fetches concurrently
    tasks = [fetch_single(url, i) for i, url in enumerate(urls)]
    results = await asyncio.gather(*tasks)

    # Unzip results
    contents = [r[0] for r in results]
    screenshots = [r[1] for r in results]
    failed_flags = [r[2] for r in results]

    # Update visited URLs
    new_visited = set(urls)

    # Identify failed URLs
    new_failed = {url for url, failed in zip(urls, failed_flags) if failed}

    return {
        "current_contents": contents,
        "current_screenshots": screenshots,
        "visited_urls": state["visited_urls"] | new_visited,
        "failed_urls": state["failed_urls"] | new_failed,
    }


async def relevance_analyzer_node(state: AgentState) -> Dict[str, Any]:
    """Analyze content relevance and extract links for the batch."""
    urls = state.get("current_urls", [])
    contents = state.get("current_contents", [])

    if not urls or not contents:
        return {"relevant_flags": [], "batch_next_urls": []}

    event_bus.publish("agent_activity", status="Analyzing Relevance (AI)")

    async def analyze_single(
        url: str, content: str | None, worker_id: int
    ) -> Dict[str, Any]:
        if not content:
            event_bus.publish(
                "worker_status", worker_id=worker_id, status="Idle", progress=0
            )
            return {"is_relevant": False, "next_urls": []}

        event_bus.publish(
            "worker_status",
            worker_id=worker_id,
            status="Analyzing Relevance",
            progress=60,
        )

        try:
            # Observation Compression
            # If content is large, compress it for relevance analysis
            analysis_content = content
            if len(content) > 20000:
                analysis_content = await context_compressor.compress_observation(
                    content, state["objective"]
                )
                logger.info(
                    f"Compressed content for {url}: {len(content)} -> {len(analysis_content)}"
                )

            analysis = await gemini_client.analyze_relevance(
                state["objective"], analysis_content, url
            )

            # Determine relevance based on score > 60
            score = analysis.get("relevance_score", 0)
            analysis["is_relevant"] = score > 60
            if analysis["is_relevant"]:
                logger.info(f"Page {url} is relevant (Score: {score})")

            # API Endpoint Discovery (use full content or truncated, but not summary)
            # We use the original content for this as it looks for specific patterns
            api_endpoints = await gemini_client.analyze_api_endpoints(content, url)
            if api_endpoints:
                logger.info(f"Discovered {len(api_endpoints)} API endpoints on {url}")
                # Add API endpoints to next_urls
                current_next_urls = analysis.get("next_urls", [])
                analysis["next_urls"] = list(set(current_next_urls + api_endpoints))

            return analysis
        except Exception as e:
            logger.error(f"Error analyzing {url}: {e}")
            return {"is_relevant": False, "next_urls": []}

    tasks = [analyze_single(u, c, i) for i, (u, c) in enumerate(zip(urls, contents))]
    results = await asyncio.gather(*tasks)

    relevant_flags = [r.get("is_relevant", False) for r in results]
    batch_next_urls = [r.get("next_urls", []) for r in results]

    # Handle Title Generation (use first relevant)
    if state.get("session_title") == "Generating Title...":
        for i, is_rel in enumerate(relevant_flags):
            if is_rel and contents[i]:
                try:
                    event_bus.publish("agent_activity", status="Generating Title (AI)")
                    # Ensure content is string for type checker
                    content_str = str(contents[i])
                    new_title = await gemini_client.generate_title(
                        state["objective"], content_str
                    )
                    return {
                        "relevant_flags": relevant_flags,
                        "batch_next_urls": batch_next_urls,
                        "session_title": new_title,
                    }
                except Exception as e:
                    logger.error(f"Failed to generate title: {e}")
                break

    return {
        "relevant_flags": relevant_flags,
        "batch_next_urls": batch_next_urls,
    }


async def extractor_node(state: AgentState) -> Dict[str, Any]:
    """Extract data from relevant content in the batch."""
    contents = state.get("current_contents", [])
    relevant_flags = state.get("relevant_flags", [])

    if not any(relevant_flags):
        # Reset workers
        for i in range(len(contents)):
            event_bus.publish("worker_status", worker_id=i, status="Idle", progress=0)
        return {}

    event_bus.publish("agent_activity", status="Extracting Data (AI)")

    async def extract_single(
        content: str | None,
        is_relevant: bool,
        worker_id: int,
        screenshot: bytes = b"",
        url: str = "",
    ) -> List[Dict[str, Any]]:
        if not is_relevant or not content:
            event_bus.publish(
                "worker_status", worker_id=worker_id, status="Idle", progress=0
            )
            return []

        event_bus.publish(
            "worker_status", worker_id=worker_id, status="Fast Extracting", progress=80
        )

        try:
            # Use FAST extraction
            data = await gemini_client.fast_extract(content, state["objective"])

            # Inject metadata
            from datetime import datetime, timezone

            timestamp = datetime.now(timezone.utc).isoformat()

            for item in data:
                item["_metadata"] = {
                    "source_url": url,
                    "timestamp": timestamp,
                    "screenshot_path": "pending",  # Screenshots handled in batch save if needed
                }

            event_bus.publish(
                "worker_status", worker_id=worker_id, status="Idle", progress=0
            )
            return data
        except Exception as e:
            logger.error(f"Error extracting: {e}")
            event_bus.publish(
                "worker_status", worker_id=worker_id, status="Error", progress=0
            )
            return []

    # We need to get screenshots from the fetcher node if available
    # Currently fetcher_node returns "current_contents" which is a list of strings (HTML)
    # We need to update fetcher_node to return screenshots as well.
    # But wait, fetcher_node returns a dict with "current_contents".
    # We should update AgentState to hold screenshots.

    screenshots = state.get("current_screenshots", [b""] * len(contents))
    urls = state.get("current_urls", [""] * len(contents))

    tasks = [
        extract_single(c, r, i, s, u)
        for i, (c, r, s, u) in enumerate(
            zip(contents, relevant_flags, screenshots, urls)
        )
    ]
    results = await asyncio.gather(*tasks)

    # Flatten results
    all_data = []

    for res in results:
        if res:
            all_data.extend(res)

    if all_data:
        logger.info(f"Fast extracted {len(all_data)} items. Saving to raw collector.")
        event_bus.publish(
            "stats_update", metric="items_extracted", increment=len(all_data)
        )

        # Save raw data immediately
        await collector.save(all_data)

        # We don't update "extracted_data" in state anymore to keep state light
        # The final data will be assembled at the end.
        return {}

    return {}


async def healing_node(state: AgentState) -> Dict[str, Any]:
    """Attempt to recover data using fingerprints before failing."""
    event_bus.publish("agent_activity", status="Self-Healing (AI)")
    logger.warning("Entering self-healing mode...")

    # For MVP, we just retry extraction with a more lenient prompt or different model
    # In a full implementation, we would use stored fingerprints.

    # Let's try to re-extract using the same logic but maybe log it
    # Or we could just return empty to skip this batch if healing fails.

    # Simulating healing success for now by just returning empty updates
    # which means we skip this batch but don't crash.
    return {}


async def rust_execution_node(state: AgentState) -> Dict[str, Any]:
    """Execute extraction using the optimized Rust/ONNX pipeline."""
    event_bus.publish("agent_activity", status="Fast Extraction (Rust/ONNX)")
    logger.info("Executing optimized extraction...")

    # Placeholder for actual Rust execution
    # In a real implementation, we would call scram_hpc_rs.run_inference

    # For MVP, we just simulate success
    return {}


async def finalization_node(state: AgentState) -> Dict[str, Any]:
    """Finalize the session: refine raw data, deduplicate, and export."""
    event_bus.publish("agent_activity", status="Finalizing Session")
    logger.info("Finalizing session...")

    # Load raw data
    raw_data = await collector.load_all()
    if not raw_data:
        logger.info("No raw data to refine.")
        event_bus.publish("agent_activity", status="Session Complete (No Data)")
        return {}

    logger.info(f"Refining {len(raw_data)} raw items...")
    event_bus.publish("agent_activity", status=f"Refining {len(raw_data)} Items (AI)")

    # Refine in batches
    BATCH_SIZE = 20
    refined_data = []

    for i in range(0, len(raw_data), BATCH_SIZE):
        batch = raw_data[i : i + BATCH_SIZE]
        try:
            cleaned_batch = await gemini_client.refine_data(batch, state["data_schema"])
            refined_data.extend(cleaned_batch)
            event_bus.publish(
                "stats_update", metric="items_extracted", value=len(refined_data)
            )
        except Exception as e:
            logger.error(f"Error refining batch {i}: {e}")

    # Save final refined data
    # We pass empty screenshots list as we didn't persist them in raw collector for speed
    # In a full implementation, we'd link screenshots via metadata paths
    await exporter.save_batch(state["session_title"], refined_data, [])

    # Run export (deduplication happens here)
    await exporter.finalize_session(state["session_title"])

    # Cleanup raw data
    collector.cleanup()

    event_bus.publish("agent_activity", status="Session Complete")
    return {}


async def compression_node(state: AgentState) -> Dict[str, Any]:
    """Compress history if recent activity is too long."""
    recent_activity = state.get("recent_activity", [])
    compressed_history = state.get("compressed_history", "")

    if len(recent_activity) >= 5:
        logger.info("Compressing history...")
        event_bus.publish("agent_activity", status="Compressing Context (AI)")

        new_summary = await context_compressor.compress_history(
            recent_activity, compressed_history
        )

        return {
            "compressed_history": new_summary,
            "recent_activity": [],
        }

    return {}


async def refinement_node(state: AgentState) -> Dict[str, Any]:
    """Add new URLs to the queue from the batch."""
    try:
        batch_next_urls = state.get("batch_next_urls", [])
        current_queue = state.get("url_queue", [])
        visited = state.get("visited_urls", set())

        # Flatten the list of lists
        all_new_urls = []
        for url_list in batch_next_urls:
            all_new_urls.extend(url_list)

        # Filter duplicates and visited
        unique_new_urls = []
        for url in all_new_urls:
            if (
                url not in visited
                and url not in current_queue
                and url not in unique_new_urls
            ):
                unique_new_urls.append(url)

        if unique_new_urls:
            logger.info(f"Adding {len(unique_new_urls)} new URLs to queue.")

        return {"url_queue": current_queue + unique_new_urls}
    except Exception as e:
        logger.error(f"Error in refinement_node: {e}")
        # Return existing queue to continue
        return {"url_queue": state.get("url_queue", [])}
