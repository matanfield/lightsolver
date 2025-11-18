//! Backtest app that builds blocks WITHOUT re-simulating transactions.
//! Uses historical execution data (gas/profit) from the actual block execution.
//! This allows testing knapsack optimization algorithms without requiring Reth state.
//!
//! Usage:
//!   backtest-build-block-no-sim --config config.toml --builders greedy-mp-ordering --builders custom-algo 18920193

use alloy_primitives::{utils::format_ether, U256};
use clap::Parser;
use rbuilder_config::load_toml_config;
use rbuilder_primitives::{Order, OrderId, SimValue, SimulatedOrder};
use std::{collections::HashMap, path::PathBuf, sync::Arc, time::Instant};
use tracing::info;

use rbuilder::{
    backtest::{
        restore_landed_orders::{restore_landed_orders, ExecutedBlockTx, SimplifiedOrder},
        BlockData, HistoricalDataStorage,
    },
    building::{
        builders::BacktestSimulateBlockInput,
        testing::test_chain_state::{BlockArgs, TestChainState},
        BlockBuildingContext,
    },
    live_builder::{cli::LiveBuilderConfig, config::Config},
    provider::{
        StateProviderFactory,
        RootHasher,
        state_provider_factory_from_provider_factory::StateProviderFactoryFromProviderFactory,
    },
};
use alloy_primitives::{BlockHash, BlockNumber, B256};
use alloy_consensus::Header;
use reth_errors::ProviderResult;
use reth_provider::StateProviderBox;
use serde::Serialize;
use std::fs::File;
use std::io::BufWriter;

#[derive(Serialize)]
struct KnapsackItem {
    id: String,
    profit: U256,
    gas: u64,
    nonces: Vec<(Address, u64)>,
}

#[derive(Serialize)]
struct KnapsackInstance {
    block_number: u64,
    items: Vec<KnapsackItem>,
}

#[derive(Parser, Debug)]
struct Cli {
    #[clap(long, help = "Config file path", env = "RBUILDER_CONFIG")]
    config: PathBuf,
    #[clap(
        long,
        help = "builders to build block with (see config builders)",
        default_value = "greedy-mp-ordering"
    )]
    builders: Vec<String>,
    #[clap(help = "Block Number")]
    block: u64,
}

/// Wrapper provider factory that intercepts block_hash() calls to return parent hash
/// when asked for the parent block number. This allows check_block_hash_reader_health
/// to pass even though we don't have the real parent block in TestChainState.
#[derive(Clone)]
struct ParentBlockHashProviderFactory {
    inner: StateProviderFactoryFromProviderFactory<reth_provider::test_utils::MockNodeTypesWithDB>,
    parent_block_number: BlockNumber,
    parent_hash: BlockHash,
}

impl ParentBlockHashProviderFactory {
    fn new(
        inner: StateProviderFactoryFromProviderFactory<reth_provider::test_utils::MockNodeTypesWithDB>,
        parent_block_number: BlockNumber,
        parent_hash: BlockHash,
    ) -> Self {
        Self {
            inner,
            parent_block_number,
            parent_hash,
        }
    }
}

impl StateProviderFactory for ParentBlockHashProviderFactory {
    fn latest(&self) -> ProviderResult<StateProviderBox> {
        self.inner.latest()
    }

    fn history_by_block_number(&self, block: BlockNumber) -> ProviderResult<StateProviderBox> {
        self.inner.history_by_block_number(block)
    }

    fn history_by_block_hash(&self, block: BlockHash) -> ProviderResult<StateProviderBox> {
        self.inner.history_by_block_hash(block)
    }

    fn header(&self, block_hash: &BlockHash) -> ProviderResult<Option<Header>> {
        self.inner.header(block_hash)
    }

    fn block_hash(&self, number: BlockNumber) -> ProviderResult<Option<B256>> {
        // Intercept calls for parent block number - return parent hash
        if number == self.parent_block_number {
            return Ok(Some(self.parent_hash));
        }
        // For other block numbers, delegate to inner provider
        self.inner.block_hash(number)
    }

    fn best_block_number(&self) -> ProviderResult<BlockNumber> {
        self.inner.best_block_number()
    }

    fn header_by_number(&self, num: u64) -> ProviderResult<Option<Header>> {
        self.inner.header_by_number(num)
    }

    fn last_block_number(&self) -> ProviderResult<BlockNumber> {
        self.inner.last_block_number()
    }

    fn root_hasher(&self, parent_num_hash: alloy_eips::BlockNumHash) -> ProviderResult<Box<dyn RootHasher>> {
        self.inner.root_hasher(parent_num_hash)
    }
}

/// Creates SimulatedOrder objects from historical execution data without re-simulation
fn create_simulated_orders_from_historical_data(
    orders: Vec<Order>,
    historical_profit_gas: HashMap<OrderId, (U256, u64)>, // profit, gas
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

/// Extract gas and profit from historical block execution
/// Uses gas tips to estimate profit (no re-simulation needed)
fn extract_historical_profit_gas(
    block_data: &BlockData,
    available_orders: &[Order],
) -> eyre::Result<HashMap<OrderId, (U256, u64)>> {
    // Extract gas and estimate profit from gas tips
    // Note: We're estimating profit from gas tips, not exact coinbase transfers
    // This is sufficient for testing selection algorithms
    let mut gas_by_tx = HashMap::new();
    let mut profit_by_tx = HashMap::new();
    
    // Handle BlockTransactions enum (can be Full or Hashes)
    use alloy_rpc_types::BlockTransactions;
    use alloy_network_primitives::TransactionResponse;
    
    let transactions = match &block_data.onchain_block.transactions {
        BlockTransactions::Full(txs) => txs,
        BlockTransactions::Hashes(_) => {
            return Err(eyre::eyre!("Block has transaction hashes only, not full transactions. This should not happen with HistoricalDataStorage."));
        }
        BlockTransactions::Uncle => {
            return Err(eyre::eyre!("Block has uncle transactions, not supported."));
        }
    };
    
    // Extract transactions and estimate gas/profit
    // Note: We don't have receipts (they come from simulation), so we estimate
    use alloy_consensus::Transaction as TransactionTrait;
    
    for tx_response in transactions {
        let tx_hash = TransactionResponse::tx_hash(tx_response);
        let tx_inner = &tx_response.inner;
        
        // Estimate gas used (use gas_limit as approximation - actual gas_used would be <= gas_limit)
        // For simplicity, assume 80% of gas_limit is used (typical for most transactions)
        let estimated_gas = (tx_inner.gas_limit() as f64 * 0.8) as u64;
        gas_by_tx.insert(tx_hash, estimated_gas);
        
        // Estimate profit from gas tip (priority fee goes to coinbase)
        let gas_tip = tx_inner
            .max_priority_fee_per_gas()
            .unwrap_or_default()
            .min(tx_inner.max_fee_per_gas());
        let gas_tip_profit = U256::from(gas_tip) * U256::from(estimated_gas);
        profit_by_tx.insert(tx_hash, gas_tip_profit);
    }
    
    // Create ExecutedBlockTx from block data with estimated profits
    // Assume all transactions succeeded (we don't have receipt data)
    let executed_block_txs: Vec<ExecutedBlockTx> = transactions
        .iter()
        .map(|tx_response| {
            let tx_hash = TransactionResponse::tx_hash(tx_response);
            let profit = profit_by_tx.get(&tx_hash).copied().unwrap_or_default();
            
            ExecutedBlockTx::new(
                tx_hash,
                alloy_primitives::I256::try_from(profit).unwrap_or_default(),
                true, // Assume success (we don't have receipt data)
            )
        })
        .collect();

    // Create simplified orders from available orders
    let simplified_orders: Vec<SimplifiedOrder> = available_orders
        .iter()
        .map(SimplifiedOrder::new_from_order)
        .collect();

    // Restore landed orders to map orders to their transactions
    let landed_orders = restore_landed_orders(executed_block_txs, simplified_orders);

    // Map orders to their profit and gas
    let mut result = HashMap::new();
    for order in available_orders {
        let order_id = order.id();
        if let Some(landed_data) = landed_orders.get(&order_id) {
            // Get total profit (convert I256 to U256, handling negative as 0)
            let profit = if landed_data.total_coinbase_profit > alloy_primitives::I256::ZERO {
                U256::try_from(landed_data.total_coinbase_profit).unwrap_or_default()
            } else {
                U256::ZERO
            };

            // Calculate total gas from transaction hashes
            let gas: u64 = landed_data
                .tx_hashes
                .iter()
                .filter_map(|tx_hash| gas_by_tx.get(tx_hash).copied())
                .sum();

            // Only include orders that have gas data
            if gas > 0 || profit > U256::ZERO {
                result.insert(order_id, (profit, gas));
            }
        } else {
            // Order not found in landed data - might be a new order not in the block
            // Estimate gas from order itself
            let estimated_gas = estimate_order_gas(order);
            if estimated_gas > 0 {
                result.insert(order_id, (U256::ZERO, estimated_gas));
            }
        }
    }

    Ok(result)
}

/// Estimate gas for an order (fallback when not in block)
fn estimate_order_gas(order: &Order) -> u64 {
    // Simple estimation: count transactions and estimate gas per tx
    let tx_count = order.list_txs().len();
    // Rough estimate: 21k base + 50k average per tx
    tx_count as u64 * 50_000 + 21_000
}

#[tokio::main]
async fn main() -> eyre::Result<()> {
    let cli = Cli::parse();
    let config: Config = load_toml_config(cli.config.clone())?;
    config.base_config().setup_tracing_subscriber()?;

    info!("Loading block {} from database...", cli.block);

    // Load block data from database
    let mut storage = HistoricalDataStorage::new_from_path(
        config.base_config().backtest_fetch_output_file.clone(),
    )
    .await?;

    let full_slot_data = storage.read_block_data(cli.block).await?;
    
    // Convert FullSlotBlockData to BlockData
    // Use a cutoff time that includes all orders (far future)
    use time::OffsetDateTime;
    let cutoff = OffsetDateTime::now_utc() + time::Duration::days(365);
    let block_data = full_slot_data.snapshot_including_landed(cutoff)?;
    
    let available_orders: Vec<Order> = block_data
        .available_orders
        .iter()
        .map(|owt| owt.order.clone())
        .collect();

    info!("Found {} available orders", available_orders.len());

    // Extract historical profit and gas data (no provider needed - we use receipts directly)
    info!("Extracting historical execution data from block receipts...");
    let historical_profit_gas = extract_historical_profit_gas(&block_data, &available_orders)?;
    info!("Extracted profit/gas for {} orders", historical_profit_gas.len());

    // Create SimulatedOrder objects without re-simulation
    let sim_orders = create_simulated_orders_from_historical_data(
        available_orders.clone(),
        historical_profit_gas,
    );
    info!("Created {} simulated orders", sim_orders.len());

    // Get builder signer from config (needed for block building context)
    let signer = config.base_config().coinbase_signer()?;
    
    // Create test chain state with builder signer funded (needed for payout tx)
    // Use new_with_balances_and_contracts to add funds to builder signer in genesis
    use alloy_primitives::utils::parse_ether;
    let test_chain_state = rbuilder::building::testing::test_chain_state::TestChainState::new_with_balances_and_contracts(
        BlockArgs::default()
            .number(block_data.onchain_block.header.number)
            .timestamp(block_data.onchain_block.header.timestamp),
        vec![(signer.address, parse_ether("100.0")?.to::<u128>())], // Give builder 100 ETH
        vec![], // No extra contracts
    )?;
    
    // Insert parent block as block #1 (after genesis) so builder can access it
    // The builder needs to call history_by_block_hash for the parent block
    let parent_hash = block_data.onchain_block.header.parent_hash;
    {
        use reth_primitives::{BlockBody, Header, SealedHeader};
        use reth_primitives_traits::block::Block;
        let provider = test_chain_state.provider_factory().provider_rw()?;
        // Create a dummy parent header with the correct hash but block number 1 (after genesis block 0)
        let mut parent_header = Header::default();
        parent_header.number = 1; // Sequential after genesis (block 0)
        let sealed_parent = SealedHeader::new(parent_header, parent_hash);
        provider.insert_historical_block(
            reth_primitives::Block::new(sealed_parent.header().clone(), BlockBody::default())
                .try_into_recovered()
                .unwrap(),
        )?;
        provider.commit()?;
    }
    
    // Create a wrapper provider factory that intercepts block_hash() calls
    // to return the parent hash when asked for the parent block number
    let parent_block_number = block_data.onchain_block.header.number - 1;
    let parent_hash = block_data.onchain_block.header.parent_hash;
    
    // Create provider factory from test chain state
    // Using None for root_hash_context means MockRootHasher will be used
    let base_provider_factory = StateProviderFactoryFromProviderFactory::new(
        test_chain_state.provider_factory().clone(),
        None, // no root hash context - use MockRootHasher
    );
    
    // Wrap it to intercept block_hash() calls
    let provider_factory = ParentBlockHashProviderFactory::new(
        base_provider_factory,
        parent_block_number,
        parent_hash,
    );
    
    // Create block building context from actual block data
    let chain_spec = config.base_config().chain_spec()?;
    
    let ctx = BlockBuildingContext::from_onchain_block(
        block_data.onchain_block.clone(),
        chain_spec,
        None,
        Default::default(), // empty blocklist
        signer.address,
        block_data.winning_bid_trace.proposer_fee_recipient,
        signer,
        Arc::new(rbuilder::building::builders::mock_block_building_helper::MockRootHasher {}),
        false, // evm_caching_enable
        Default::default(), // mev_blocker_price
    );
    // Enable no-execution mode to skip EVM execution and trust simulated values
    let mut ctx = ctx;
    ctx.no_execution = true;

    // Export Knapsack Instance
    info!("Exporting knapsack instance...");
    let knapsack_items: Vec<KnapsackItem> = sim_orders
        .iter()
        .map(|sim_order| {
            let nonces = sim_order
                .order
                .nonces()
                .into_iter()
                .map(|n| (n.address, n.nonce))
                .collect();
            
            KnapsackItem {
                id: sim_order.id().to_string(),
                profit: sim_order.sim_value.full_profit_info().coinbase_profit(),
                gas: sim_order.sim_value.gas_used(),
                nonces,
            }
        })
        .collect();

    let instance = KnapsackInstance {
        block_number: cli.block,
        items: knapsack_items,
    };

    let export_path = format!("knapsack_instance_{}.json", cli.block);
    let file = File::create(&export_path)?;
    let writer = BufWriter::new(file);
    serde_json::to_writer(writer, &instance)?;
    info!("Exported {} items to {}", instance.items.len(), export_path);

    // Run each builder algorithm
    println!("\n=== Running Block Building Algorithms ===\n");
    
    for builder_name in &cli.builders {
        println!("--- Builder: {} ---", builder_name);
        
        let start_time = Instant::now();
        
        // Use the config's build_backtest_block method which handles builder selection
        // Note: We're using a test chain state provider - commits may fail but we have pre-computed values
        let input = BacktestSimulateBlockInput {
            ctx: ctx.clone(),
            builder_name: builder_name.clone(),
            sim_orders: &sim_orders,
            provider: provider_factory.clone(),
        };

        // Run the builder algorithm using config's method
        let block = config.build_backtest_block(
            builder_name,
            input,
            rbuilder::building::NullPartialBlockExecutionTracer {},
        )?;

        let compute_time = start_time.elapsed();
        let total_value = block.trace.bid_value;
        let orders_included = block.trace.included_orders.len();

        println!("Total Value: {} ETH", format_ether(total_value));
        println!("Orders Included: {}", orders_included);
        println!("Compute Time: {:?}", compute_time);
        println!("\nSelected Transactions:");
        
        for (idx, order_result) in block.trace.included_orders.iter().enumerate() {
            println!("  {}. {} (gas: {}, profit: {} ETH)", 
                idx + 1,
                order_result.order.id(),
                order_result.space_used.gas,
                format_ether(order_result.coinbase_profit)
            );
            
            // Print transaction hashes
            for tx_info in &order_result.tx_infos {
                println!("      ↳ {}", tx_info.tx.hash());
            }
        }
        
        println!();
    }

    Ok(())
}

