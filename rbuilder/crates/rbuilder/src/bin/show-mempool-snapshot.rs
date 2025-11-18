//! Simple tool to show mempool snapshot and SimulatedOrder data
//! Shows what would be fed to the greedy algorithm

use alloy_primitives::utils::format_ether;
use clap::Parser;
use rbuilder_config::load_toml_config;
use rbuilder_primitives::{Order, OrderId, SimValue, SimulatedOrder};
use std::{collections::HashMap, path::PathBuf, sync::Arc};
use tracing::info;

use rbuilder::{
    backtest::{
        restore_landed_orders::{restore_landed_orders, ExecutedBlockTx, SimplifiedOrder},
        BlockData, HistoricalDataStorage,
    },
    live_builder::{cli::LiveBuilderConfig, config::Config},
};

#[derive(Parser, Debug)]
struct Cli {
    #[clap(long, help = "Config file path", env = "RBUILDER_CONFIG")]
    config: PathBuf,
    #[clap(help = "Block Number")]
    block: u64,
    #[clap(long, help = "Show top N orders by profit")]
    top: Option<usize>,
}

// Copy of extract_historical_profit_gas from backtest-build-block-no-sim.rs
fn extract_historical_profit_gas(
    block_data: &BlockData,
    available_orders: &[Order],
) -> eyre::Result<HashMap<OrderId, (alloy_primitives::U256, u64)>> {
    use alloy_network_primitives::TransactionResponse;
    use alloy_rpc_types::BlockTransactions;
    
    let mut gas_by_tx = HashMap::new();
    let mut profit_by_tx = HashMap::new();
    
    let transactions = match &block_data.onchain_block.transactions {
        BlockTransactions::Full(txs) => txs,
        BlockTransactions::Hashes(_) => {
            return Err(eyre::eyre!("Block has transaction hashes only, not full transactions."));
        }
        BlockTransactions::Uncle => {
            return Err(eyre::eyre!("Block has uncle transactions, not supported."));
        }
    };
    
    use alloy_consensus::Transaction as TransactionTrait;
    
    for tx_response in transactions {
        let tx_hash = TransactionResponse::tx_hash(tx_response);
        let tx_inner = &tx_response.inner;
        
        let estimated_gas = (tx_inner.gas_limit() as f64 * 0.8) as u64;
        gas_by_tx.insert(tx_hash, estimated_gas);
        
        let gas_tip = tx_inner
            .max_priority_fee_per_gas()
            .unwrap_or_default()
            .min(tx_inner.max_fee_per_gas());
        let gas_tip_profit = alloy_primitives::U256::from(gas_tip) * alloy_primitives::U256::from(estimated_gas);
        profit_by_tx.insert(tx_hash, gas_tip_profit);
    }
    
    let executed_block_txs: Vec<ExecutedBlockTx> = transactions
        .iter()
        .map(|tx_response| {
            let tx_hash = TransactionResponse::tx_hash(tx_response);
            let profit = profit_by_tx.get(&tx_hash).copied().unwrap_or_default();
            
            ExecutedBlockTx::new(
                tx_hash,
                alloy_primitives::I256::try_from(profit).unwrap_or_default(),
                true,
            )
        })
        .collect();

    let simplified_orders: Vec<SimplifiedOrder> = available_orders
        .iter()
        .map(SimplifiedOrder::new_from_order)
        .collect();

    let landed_orders = restore_landed_orders(executed_block_txs, simplified_orders);

    let mut result = HashMap::new();
    for (order_id, landed_data) in landed_orders {
        // Extract profit from LandedOrderData (convert I256 to U256)
        let profit = if landed_data.total_coinbase_profit > alloy_primitives::I256::ZERO {
            alloy_primitives::U256::try_from(landed_data.total_coinbase_profit).unwrap_or_default()
        } else {
            alloy_primitives::U256::ZERO
        };
        
        // Calculate total gas from transaction hashes
        let gas: u64 = landed_data
            .tx_hashes
            .iter()
            .filter_map(|tx_hash| gas_by_tx.get(tx_hash).copied())
            .sum();
        
        // Only include orders that have gas data
        if gas > 0 || profit > alloy_primitives::U256::ZERO {
            result.insert(order_id, (profit, gas));
        }
    }

    Ok(result)
}

fn create_simulated_orders_from_historical_data(
    orders: Vec<Order>,
    historical_profit_gas: HashMap<OrderId, (alloy_primitives::U256, u64)>,
) -> Vec<Arc<SimulatedOrder>> {
    orders
        .into_iter()
        .filter_map(|order| {
            let order_id = order.id();
            let (profit, gas) = historical_profit_gas.get(&order_id)?;
            
            Some(Arc::new(SimulatedOrder {
                order,
                sim_value: SimValue::new_test(*profit, *profit, *gas),
                used_state_trace: None,
            }))
        })
        .collect()
}

#[tokio::main]
async fn main() -> eyre::Result<()> {
    let cli = Cli::parse();
    
    let config: Config = load_toml_config(cli.config.clone())?;
    config.base_config().setup_tracing_subscriber()?;

    let mut storage = HistoricalDataStorage::new_from_path(
        config.base_config().backtest_fetch_output_file.clone(),
    )
    .await?;

    let full_slot_data = storage.read_block_data(cli.block).await?;
    
    use time::OffsetDateTime;
    let cutoff = OffsetDateTime::now_utc() + time::Duration::days(365);
    let block_data = full_slot_data.snapshot_including_landed(cutoff)?;
    
    let available_orders: Vec<Order> = block_data
        .available_orders
        .iter()
        .map(|owt| owt.order.clone())
        .collect();

    println!("\n=== Mempool Snapshot for Block {} ===\n", cli.block);
    println!("Total Orders: {}", available_orders.len());
    println!("Block Hash: {:?}", block_data.onchain_block.header.hash);
    println!("Parent Hash: {:?}", block_data.onchain_block.header.parent_hash);
    println!("Block Number: {}", block_data.onchain_block.header.number);
    println!("Timestamp: {}\n", block_data.onchain_block.header.timestamp);

    let historical_profit_gas = extract_historical_profit_gas(&block_data, &available_orders)?;
    println!("Orders with profit/gas data: {}\n", historical_profit_gas.len());

    let sim_orders = create_simulated_orders_from_historical_data(
        available_orders.clone(),
        historical_profit_gas,
    );

    println!("=== SimulatedOrder Data (What would be fed to Greedy) ===\n");
    
    // Sort by profit (descending) for display
    let mut sorted_orders: Vec<_> = sim_orders.iter().collect();
    sorted_orders.sort_by(|a, b| {
        b.sim_value.full_profit_info().coinbase_profit().cmp(&a.sim_value.full_profit_info().coinbase_profit())
    });

    let display_count = cli.top.unwrap_or(sorted_orders.len());
    let top_orders = &sorted_orders[..display_count.min(sorted_orders.len())];

    println!("Showing {} orders (sorted by profit):\n", top_orders.len());
    println!("{:<60} {:>15} {:>15} {:>20}", "Order ID", "Gas", "Profit (ETH)", "Profit/Gas");
    println!("{}", "-".repeat(110));

    let mut total_profit = alloy_primitives::U256::ZERO;
    let mut total_gas = 0u64;

    for sim_order in top_orders {
        let profit = sim_order.sim_value.full_profit_info().coinbase_profit();
        let gas = sim_order.sim_value.gas_used();
        let profit_per_gas = if gas > 0 {
            format_ether(profit / alloy_primitives::U256::from(gas))
        } else {
            "N/A".to_string()
        };

        total_profit += profit;
        total_gas += gas;

        println!(
            "{:<60} {:>15} {:>15} {:>20}",
            format!("{:?}", sim_order.order.id()),
            gas,
            format_ether(profit),
            profit_per_gas
        );

        // Show transaction hashes
        for (tx, _) in sim_order.order.list_txs() {
            println!("  ↳ TX: {:?}", tx.hash());
        }
    }

    println!("{}", "-".repeat(110));
    println!(
        "{:<60} {:>15} {:>15}",
        "TOTAL (shown)",
        total_gas,
        format_ether(total_profit)
    );

    if display_count < sorted_orders.len() {
        let remaining_profit: alloy_primitives::U256 = sorted_orders[display_count..]
            .iter()
            .map(|o| o.sim_value.full_profit_info().coinbase_profit())
            .sum();
        let remaining_gas: u64 = sorted_orders[display_count..]
            .iter()
            .map(|o| o.sim_value.gas_used())
            .sum();
        
        println!(
            "{:<60} {:>15} {:>15}",
            format!("... and {} more orders", sorted_orders.len() - display_count),
            remaining_gas,
            format_ether(remaining_profit)
        );
    }

    println!("\n=== Summary ===");
    println!("Total orders: {}", sim_orders.len());
    println!("Total estimated profit: {} ETH", format_ether(
        sim_orders.iter().map(|o| o.sim_value.full_profit_info().coinbase_profit()).sum::<alloy_primitives::U256>()
    ));
    println!("Total estimated gas: {}", 
        sim_orders.iter().map(|o| o.sim_value.gas_used()).sum::<u64>()
    );
    println!("\nNote: These are ESTIMATED values (gas tips * 80% of gas_limit)");
    println!("For exact values, you'd need full transaction simulation (requires Reth)");

    Ok(())
}

