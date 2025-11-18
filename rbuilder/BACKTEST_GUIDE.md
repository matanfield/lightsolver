# Backtesting Guide: Greedy vs Custom Algorithm

This guide walks you through running backtests on historical Sepolia blocks to benchmark your custom optimization algorithm against the greedy algorithm.

## Prerequisites

1. **QuickNode endpoints (per network)**:
   ```bash
   # Sepolia
   export QUICK_NODE_ETH_SPOLIA_API_URL_HTTP="https://..."
   export QUICK_NODE_ETH_SPOLIA_API_URL_WSS="wss://..."

   # Mainnet (optional)
   export QUICK_NODE_ETH_MAINNET_API_URL_HTTP="https://..."
   export QUICK_NODE_ETH_MAINNET_API_URL_WSS="wss://..."
   ```

2. **Reth node for Sepolia** (for state access):
   - Option A: Run a local Reth node synced to Sepolia
   - Option B: Use IPC provider if you have a running node
   - Option C: Use the QuickNode endpoint (may be slower)

3. **Build rbuilder**:
   ```bash
   cd /Users/matanfield/Projects/lightsolver/rbuilder
   source ~/.cargo/env
   cargo build --release
   ```

## Step 1: Fetch Historical Block Data

First, you need to fetch historical mempool data and block information for the blocks you want to test.

```bash
# Set your environment variables (use .env or export manually):
# QUICK_NODE_ETH_SPOLIA_API_URL_HTTP="https://..."
# QUICK_NODE_ETH_SPOLIA_API_URL_WSS="wss://..."
# QUICK_NODE_ETH_MAINNET_API_URL_HTTP="https://..."
# QUICK_NODE_ETH_MAINNET_API_URL_WSS="wss://..."
# RETH_DATADIR="/path/to/reth/datadir"  # Optional if using local node

# Or if using IPC:
# Update config-sepolia-backtest.toml to set ipc_provider

# Fetch data for a range of blocks (e.g., blocks 5000000-5000100)
cargo run --release --bin backtest-fetch -- \
  --config config-sepolia-backtest.toml \
  fetch --range 5000000 5000100

# Or use the helper script:
./run-backtest.sh fetch 5000000 5000100
```

To run against mainnet, point the helper script (or cargo commands) to the mainnet config:

```bash
export RBUILDER_CONFIG_PATH=config-mainnet-backtest.toml
./run-backtest.sh fetch 18900000 18900100   # Example mainnet range
```

This will:
- Download mempool transactions from mempool-dumpster
- Fetch block data from your QuickNode endpoint
- Store everything in `~/.rbuilder/backtest/sepolia.sqlite`

## Step 2: Run Backtest with Greedy Algorithm (Baseline)

Run backtests with the greedy algorithm to establish a baseline:

```bash
# Test a single block
cargo run --release --bin backtest-build-block -- \
  --config config-sepolia-backtest.toml \
  --builders greedy-mp-ordering \
  5000000

# Or use the helper script:
./run-backtest.sh test-greedy 5000000

# Test a range of blocks and store results for comparison
cargo run --release --bin backtest-build-range -- \
  --config config-sepolia-backtest.toml \
  --store-backtest \
  --range \
  5000000 5000100

# Or use the helper script:
./run-backtest.sh test-range 5000000 5000100
```

The `--store-backtest` flag saves results to the database so you can compare later.

## Step 3: Implement Your Custom Algorithm

To add your custom algorithm, you have a few options:

### Option A: Custom Sorting (Easiest)

If your algorithm is just a different sorting strategy, you can:
1. Add a new `Sorting` variant in `crates/rbuilder/src/building/mod.rs`
2. Implement the sorting logic
3. Add a new builder config:

```toml
[[builders]]
name = "custom-algo"
algo = "ordering-builder"
sorting = "your-custom-sorting"  # Your new sorting variant
discard_txs = true
failed_order_retries = 1
drop_failed_orders = true
```

### Option B: Custom BlockBuildingAlgorithm (More Flexible)

If you need more control, implement the `BlockBuildingAlgorithm` trait:

1. Create a new file: `crates/rbuilder/src/building/builders/custom_builder.rs`
2. Implement `BlockBuildingAlgorithm` trait
3. Register it in `crates/rbuilder/src/building/builders/mod.rs`
4. Add config parsing in `crates/rbuilder/src/live_builder/config.rs`

See `ordering_builder.rs` and `parallel_builder.rs` for examples.

### Option C: Modify Ordering Builder

You can also extend the ordering builder with custom logic by modifying:
- `crates/rbuilder/src/building/builders/ordering_builder.rs`
- `crates/rbuilder/src/building/block_orders/order_priority.rs`

## Step 4: Run Backtest with Your Custom Algorithm

Once your algorithm is implemented:

1. Add it to `backtest_builders` in the config:
```toml
backtest_builders = ["greedy-mp-ordering", "custom-algo"]
```

2. Run the backtest:
```bash
# Test single block
cargo run --release --bin backtest-build-block -- \
  --config config-sepolia-backtest.toml \
  --builders greedy-mp-ordering \
  --builders custom-algo \
  5000000

# Test range and compare
cargo run --release --bin backtest-build-range -- \
  --config config-sepolia-backtest.toml \
  --compare-backtest \
  --range \
  5000000 5000100
```

The `--compare-backtest` flag compares against the stored baseline results.

## Step 5: Analyze Results

The output shows:
- **Win %**: Percentage of blocks where your algorithm beat the landed block
- **Total profits**: Sum of extra profit vs landed blocks
- Per-block comparison showing:
  - `bid_val`: The actual winning bid value
  - `best_bldr`: Your best builder's profit and orders included
  - Comparison between greedy and your algorithm

You can also export to CSV:
```bash
cargo run --release --bin backtest-build-range -- \
  --config config-sepolia-backtest.toml \
  --csv results.csv \
  --range \
  5000000 5000100
```

## Understanding the Output

```
block:       5000000
bid_val:     0.123456 ETH          # Actual winning bid
best_bldr:   0.125000 ETH 42 greedy-mp-ordering  # Your best result
won_by:      greedy-mp-ordering   # Which builder won
sim_ord:     150                   # Simulated orders count
  bldr:  0.125000 ETH 42 greedy-mp-ordering
  bldr:  0.120000 ETH 38 custom-algo
```

## Tips

1. **Start small**: Test on 10-20 blocks first to verify your algorithm works
2. **Use `--store-backtest`**: Saves results for easy comparison
3. **Check block ranges**: Make sure blocks have sufficient MEV activity
4. **Parallel processing**: The backtest uses all CPU cores by default
5. **Sepolia vs Mainnet**: Sepolia has less MEV, so results may differ from mainnet

## Troubleshooting

- **"No blocks found"**: Make sure you've run `backtest-fetch` first
- **"Provider error"**: Check your Reth node is synced and accessible
- **"Rate limit"**: Reduce `backtest_fetch_eth_rpc_parallel` in config
- **Build errors**: Make sure you've implemented all required traits for your custom algorithm

