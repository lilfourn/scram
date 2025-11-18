# Task 01: High-Performance Fetching Engine & Evasion

## Goal
Implement the `FetchingEngine` capable of 1000+ pages/min with robust anti-bot evasion.

## Requirements

### 1. Concurrency Model
- Implement an `asyncio` worker pool (Producer-Consumer pattern).
- Workers should pull URLs from an `asyncio.Queue`.
- Implement **Rate Limiting**:
  - Global throttle.
  - Per-domain throttle.
  - Exponential backoff for 429/503 errors.

### 2. Hybrid Fetching Strategy
Implement a two-tier fetching logic:
- **Tier 1 (Speed)**: Use `httpx` or `curl_cffi`.
  - Analyze response for blocks (403, Cloudflare challenges).
- **Tier 2 (Evasion)**: If blocked, escalate to `Playwright`.

### 3. Anti-Bot Evasion
- **Proxy Rotation**: Integrate support for residential proxies.
- **TLS Spoofing**: Use `curl_cffi` to mimic real browser JA3 fingerprints.
- **Header Management**: Rotate User-Agents and maintain consistent headers.
- **Browser Stealth**:
  - Use `playwright-stealth`.
  - Maintain a pool of "warm" browser contexts.
  - Randomize viewports and timezones.

## Definition of Done
- `FetchingEngine` class is implemented and tested.
- Can fetch URLs using both HTTP and Browser methods.
- Rate limiting and backoff logic are verified with tests.
- Proxy and User-Agent rotation are functional.
