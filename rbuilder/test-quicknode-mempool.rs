//! Simple test script to connect to QuickNode WebSocket and stream live mempool transactions
use alloy_provider::{Provider, ProviderBuilder};
use alloy_primitives::FixedBytes;
use futures::StreamExt;
use std::pin::pin;
use std::time::Instant;

#[tokio::main]
async fn main() -> eyre::Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    // Get QuickNode WebSocket URL from environment
    let ws_url = std::env::var("QUICK_NODE_ETH_MAINNET_API_URL_WSS")
        .expect("QUICK_NODE_ETH_MAINNET_API_URL_WSS environment variable not set");

    println!("🔌 Connecting to QuickNode WebSocket: {}", ws_url);
    println!("📡 Subscribing to pending transactions...\n");

    // Connect to WebSocket
    let ws_conn = alloy_provider::WsConnect::new(ws_url);
    let provider = ProviderBuilder::new()
        .connect_ws(ws_conn)
        .await
        .map_err(|e| eyre::eyre!("Failed to connect to WebSocket: {}", e))?;

    println!("✅ Connected successfully!\n");
    println!("⏳ Waiting for pending transactions...\n");
    println!("Press Ctrl+C to stop\n");
    println!("{}", "─".repeat(80));

    // Subscribe to pending transactions
    let stream = provider
        .subscribe_pending_transactions()
        .await
        .map_err(|e| eyre::eyre!("Failed to subscribe to pending transactions: {}", e))?;

    let mut stream = pin!(stream.into_stream());
    let mut count = 0u64;
    let start_time = Instant::now();

    // Stream transactions
    while let Some(tx_hash) = stream.next().await {
        count += 1;
        let elapsed = start_time.elapsed();
        let rate = count as f64 / elapsed.as_secs_f64();

        // Get transaction details
        let tx_details = provider.get_transaction_by_hash(tx_hash).await;
        
        match tx_details {
            Ok(Some(tx)) => {
                let from = tx.from;
                let to = tx.to.map(|a| a.to_string()).unwrap_or_else(|| "Contract Creation".to_string());
                let value = tx.value;
                let gas_price = tx.gas_price.unwrap_or_default();
                let gas_limit = tx.gas_limit;
                
                println!(
                    "[#{:6}] Hash: {:#?}",
                    count,
                    tx_hash
                );
                println!("         From: {}", from);
                println!("         To:   {}", to);
                println!("         Value: {} ETH", alloy_primitives::U256::from(value) / alloy_primitives::U256::from(1_000_000_000_000_000_000u64));
                println!("         Gas Price: {} Gwei", gas_price / 1_000_000_000u64);
                println!("         Gas Limit: {}", gas_limit);
                println!("         Rate: {:.2} tx/s", rate);
                println!("{}", "─".repeat(80));
            }
            Ok(None) => {
                println!(
                    "[#{:6}] Hash: {:#?} (tx not found in mempool)",
                    count,
                    tx_hash
                );
            }
            Err(e) => {
                eprintln!("[#{:6}] Error fetching tx details: {}", count, e);
            }
        }
    }

    println!("\n📊 Total transactions received: {}", count);
    Ok(())
}


