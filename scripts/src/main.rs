use std::fs::File;
use std::io::BufReader;
use std::num::NonZeroU32;
use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Duration;

use anyhow::{Context, Result};
use clap::Parser;
use futures::stream::{self, StreamExt};
use governor::{Quota, RateLimiter};
use indicatif::{ProgressBar, ProgressStyle};
use tokio::sync::Semaphore;

#[derive(Debug, serde::Deserialize)]
struct DownloadRecord {
    #[serde(rename = "objectid")]
    id: i32,
    #[serde(rename = "thumburl")]
    url: url::Url,
}

#[derive(Parser, Debug)]
#[command(name = "download")]
#[command(about = "Download images from a CSV file in parallel")]
struct Args {
    /// Path to the csv file
    #[arg(short, long, default_value = "art.csv")]
    input: PathBuf,

    /// Output directory for downloaded images
    #[arg(short, long, default_value = "images")]
    output: PathBuf,

    /// Maximum concurrent downloads
    #[arg(short, long, default_value = "50")]
    concurrency: usize,

    /// Maximum requests per second
    #[arg(short, long, default_value = "500")]
    rate_limit: u32,

    /// Number of retry attempts on failure
    #[arg(long, default_value = "3")]
    retries: u32,
}

fn read_csv(path: &PathBuf) -> Result<Vec<DownloadRecord>> {
    let mut reader = File::open(path)
        .map(BufReader::new)
        .map(csv::Reader::from_reader)?;

    let mut records = Vec::new();
    for result in reader.deserialize() {
        records.push(result?);
    }

    Ok(records)
}

async fn download_with_retry(
    client: &reqwest::Client,
    url: &url::Url,
    output_path: &PathBuf,
    retries: u32,
) -> Result<()> {
    let mut last_error = None;

    for attempt in 0..=retries {
        if attempt > 0 {
            // Exponential backoff: 1s, 2s, 4s, ...
            let delay = Duration::from_secs(1 << (attempt - 1));
            tokio::time::sleep(delay).await;
        }

        match client.get(url.clone()).send().await {
            Ok(response) => {
                if response.status().is_success() {
                    match response.bytes().await {
                        Ok(bytes) => {
                            tokio::fs::write(output_path, &bytes).await?;
                            return Ok(());
                        }
                        Err(e) => {
                            last_error =
                                Some(anyhow::anyhow!("Failed to read response body: {}", e));
                        }
                    }
                } else {
                    last_error = Some(anyhow::anyhow!("HTTP {}: {}", response.status(), url));
                }
            }
            Err(e) => {
                last_error = Some(anyhow::anyhow!("Request failed: {}", e));
            }
        }
    }

    Err(last_error.unwrap_or_else(|| anyhow::anyhow!("Unknown error")))
}

struct DownloadState {
    success: AtomicUsize,
    failed: AtomicUsize,
    skipped: AtomicUsize,
}

impl DownloadState {
    fn new() -> Self {
        Self {
            success: AtomicUsize::new(0),
            failed: AtomicUsize::new(0),
            skipped: AtomicUsize::new(0),
        }
    }

    fn increment_success(&self) {
        self.success.fetch_add(1, Ordering::Relaxed);
    }

    fn increment_failed(&self) {
        self.failed.fetch_add(1, Ordering::Relaxed);
    }

    fn increment_skipped(&self) {
        self.skipped.fetch_add(1, Ordering::Relaxed);
    }

    fn success(&self) -> usize {
        self.success.load(Ordering::Relaxed)
    }

    fn failed(&self) -> usize {
        self.failed.load(Ordering::Relaxed)
    }

    fn skipped(&self) -> usize {
        self.skipped.load(Ordering::Relaxed)
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();

    // Create output directory
    tokio::fs::create_dir_all(&args.output)
        .await
        .context("Failed to create output directory")?;

    // Read CSV file
    println!("Reading CSV file: {:?}", args.input);
    let records = read_csv(&args.input)?;
    println!("Found {} records with valid URLs", records.len());

    // Set up rate limiter
    let rate_limiter = Arc::new(RateLimiter::direct(Quota::per_second(
        NonZeroU32::new(args.rate_limit).context("Rate limit must be > 0")?,
    )));

    // Set up concurrency limiter
    let semaphore = Arc::new(Semaphore::new(args.concurrency));

    // Set up HTTP client
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(30))
        .build()?;

    // Progress tracking
    let progress = ProgressBar::new(records.len() as u64);
    progress.set_style(
        ProgressStyle::default_bar()
            .template("{spinner:.green} [{elapsed_precise}] [{bar:40.cyan/blue}] {pos}/{len} ({eta}) {msg}")?
            .progress_chars("#>-"),
    );

    let state = Arc::new(DownloadState::new());

    // Process downloads in parallel
    stream::iter(records)
        .for_each_concurrent(args.concurrency, |record| {
            let client = client.clone();
            let state = Arc::clone(&state);
            let rate_limiter = Arc::clone(&rate_limiter);
            let semaphore = Arc::clone(&semaphore);
            let progress = progress.clone();
            let output_dir = args.output.clone();
            let retries = args.retries;

            async move {
                let output_path = output_dir.join(format!("{}.jpg", record.id));

                // Skip if file already exists (resume support)
                if output_path.exists() {
                    state.increment_skipped();
                    progress.inc(1);
                    return;
                }

                // Acquire semaphore permit
                let _permit = semaphore.acquire().await.unwrap();

                // Wait for rate limiter
                rate_limiter.until_ready().await;

                // Download with retry
                match download_with_retry(&client, &record.url, &output_path, retries).await {
                    Ok(_) => state.increment_success(),
                    Err(e) => {
                        state.increment_failed();
                        progress.println(format!("Failed {}: {}", record.url, e));
                    }
                }

                progress.inc(1);
            }
        })
        .await;

    progress.finish_with_message("Done!");

    println!("\nSummary:");
    println!("  Downloaded: {}", state.success());
    println!("  Skipped (already exists): {}", state.skipped());
    println!("  Failed: {}", state.failed());

    if state.failed() > 0 {
        println!("\nNote: {} downloads failed. Run again to retry.", state.failed());
    }

    Ok(())
}
