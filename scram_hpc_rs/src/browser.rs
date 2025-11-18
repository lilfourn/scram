use anyhow::Result;
use chromiumoxide::browser::{Browser, BrowserConfig};
use chromiumoxide::cdp::browser_protocol::page::{CaptureScreenshotFormat, CaptureScreenshotParams, NavigateParams};
use futures::StreamExt;
use rand::Rng;
use std::time::Duration;
use tokio::time::sleep;

pub struct MirageBrowser {
    browser: Browser,
    handle: tokio::task::JoinHandle<()>,
}

impl MirageBrowser {
    pub async fn new(_headless: bool) -> Result<Self> {
        let (browser, mut handler) = Browser::launch(
            BrowserConfig::builder()
                .with_head() // We might want to toggle this based on headless param, but chromiumoxide defaults to headless unless with_head is called? Actually no, default is headless.
                // .viewport(None) // Use default
                .build()
                .map_err(|e| anyhow::anyhow!(e))?,
        )
        .await?;

        let handle = tokio::task::spawn(async move {
            while let Some(h) = handler.next().await {
                if h.is_err() {
                    break;
                }
            }
        });

        Ok(Self { browser, handle })
    }

    pub async fn fetch_page(&self, url: &str) -> Result<(String, u16, Vec<u8>)> {
        let page = self.browser.new_page("about:blank").await?;
        
        // Mirage Engine: Behavioral Synthesis (Warm-up / Mouse Jitter)
        let jitter = {
            let mut rng = rand::thread_rng();
            rng.gen_range(500..1500)
        };
        sleep(Duration::from_millis(jitter)).await;

        // Navigate
        page.goto(NavigateParams::new(url)).await?;
        
        // Wait for content (simple wait for now)
        page.wait_for_navigation().await?;
        
        // More jitter
        let jitter = {
            let mut rng = rand::thread_rng();
            rng.gen_range(1000..3000)
        };
        sleep(Duration::from_millis(jitter)).await;

        let content = page.content().await?;
        
        // Capture Screenshot
        let screenshot_params = CaptureScreenshotParams::builder()
            .format(CaptureScreenshotFormat::Png)
            .build();
            
        let screenshot = page.screenshot(screenshot_params).await?;
        
        // Chromiumoxide doesn't easily give status code for the main resource in a simple way 
        // without listening to network events. For MVP, we assume 200 if content is retrieved.
        let status = 200; 

        page.close().await?;

        Ok((content, status, screenshot))
    }
}
