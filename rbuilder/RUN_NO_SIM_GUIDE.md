# Running Knapsack Algorithms Without Re-Simulation

This guide shows how to run greedy and custom knapsack algorithms **without requiring Reth state** by using historical execution data.

## Current Status (Nov 2025)

### ✅ What Works
- **Build**: Binary compiles successfully ✓
- **Data Loading**: Loads historical block and order data from SQLite database ✓
- **Profit/Gas Extraction**: Extracts gas and estimates profit from block transactions ✓
- **SimulatedOrder Creation**: Creates `SimulatedOrder` objects with pre-computed values ✓
- **Test Provider Setup**: Sets up test chain state and provider factory ✓
- **Parent Block Insertion**: Inserts parent block header with correct hash ✓

### ⚠️ Known Limitations
- **Runtime Error**: Currently fails at runtime when builder accesses parent block by number
  - Error: `Missing historical block hash for block 18920192, latest block: 18920192`
  - Root cause: Test provider requires sequential block insertion, but we insert parent as block #1 while builder looks for block #18920192
  - Impact: Selection algorithm cannot complete execution
  - Workaround: None currently - requires code changes to handle missing parent blocks gracefully

### 🔧 Technical Details

**What the binary does:**
1. Loads `FullSlotBlockData` from `HistoricalDataStorage`
2. Converts to `BlockData` using `snapshot_including_landed()`
3. Extracts transactions from `BlockTransactions::Full`
4. Estimates gas used (80% of gas_limit) and profit (from gas tips)
5. Creates `ExecutedBlockTx` objects with estimated values
6. Uses `restore_landed_orders()` to map orders to transactions
7. Creates `SimulatedOrder` objects with `SimValue::new_test()`
8. Sets up `TestChainState` and inserts parent block as block #1
9. Creates `BlockBuildingContext` with `MockRootHasher`
10. Runs builder algorithm via `config.build_backtest_block()`

**Where it fails:**
- Builder calls `provider.history_by_block_hash(parent_hash)` ✓ (works)
- Builder calls `provider.block_hash(18920192)` ✗ (fails - we inserted as block #1)
- Builder needs parent block accessible by both hash AND number

## Prerequisites

- Blocks fetched in database (use `backtest-fetch`)
- Config file with builder definitions
- **NO Reth node required!** 🎉 (but see limitations above)

## Usage

### Basic Run (Greedy Algorithm)

```bash
cd /Users/matanfield/Projects/lightsolver/rbuilder

export RBUILDER_CONFIG_PATH=config-mainnet-backtest.toml

# Using the helper script
./run-backtest.sh test-no-sim 18920193 greedy-mp-ordering

# Or directly
cargo run --release -p rbuilder --bin backtest-build-block-no-sim -- \
  --config config-mainnet-backtest.toml \
  --builders greedy-mp-ordering \
  18920193
```

### Run Multiple Algorithms (Greedy + Custom)

```bash
./run-backtest.sh test-no-sim 18920193 greedy-mp-ordering custom-algo

# Or directly
cargo run --release -p rbuilder --bin backtest-build-block-no-sim -- \
  --config config-mainnet-backtest.toml \
  --builders greedy-mp-ordering \
  --builders custom-algo \
  18920193
```

## Expected Output Format

When working, for each algorithm you'll see:

```
=== Running Block Building Algorithms ===

--- Builder: greedy-mp-ordering ---
Total Value: 0.123456 ETH
Orders Included: 42
Compute Time: 15.234ms

Selected Transactions:
  1. tx:0xabc123... (gas: 21000, profit: 0.001 ETH)
      ↳ 0xabc123...
  2. bundle:uuid-... (gas: 50000, profit: 0.002 ETH)
      ↳ 0xdef456...
      ↳ 0x789abc...
  ...
```

## Current Output (With Error)

```
=== Running Block Building Algorithms ===

--- Builder: greedy-mp-ordering ---
Error: Provider historical block hashes error: Missing historical block hash for block 18920192, latest block: 18920192

Caused by:
    Missing historical block hash for block 18920192, latest block: 18920192

Location:
    /Users/matanfield/Projects/lightsolver/rbuilder/crates/rbuilder/src/building/builders/ordering_builder.rs:285:41
```

## How It Works (When Fixed)

1. **Loads historical data**: Reads orders and block execution data from SQLite database
2. **Extracts profit/gas**: 
   - Extracts transactions from `BlockTransactions::Full`
   - Estimates gas used as 80% of `gas_limit` (typical for most transactions)
   - Estimates profit from gas tips: `gas_tip * estimated_gas`
   - Creates `ExecutedBlockTx` objects with these estimates
3. **Maps orders to transactions**: Uses `restore_landed_orders()` to match orders with their transactions
4. **Creates SimulatedOrder**: Uses `SimValue::new_test()` to create orders with pre-computed values
5. **Sets up test provider**: Creates `TestChainState` and inserts parent block header
6. **Runs algorithm**: Executes the selection algorithm (no re-simulation needed)
7. **Outputs results**: Shows selected transactions, total value, and timing

## Advantages Over `backtest-build-block`

- ✅ **No Reth sync** (saves days + terabytes)
- ✅ **Fast** (no transaction simulation)
- ✅ **Real data** (uses historical execution results)
- ✅ **Focus on optimization** (tests selection algorithm, not execution)

## Limitations

### Current Limitations
- ⚠️ **Runtime error**: Builder cannot access parent block by number (see "Known Limitations" above)
- ⚠️ **Profit estimation**: Values are estimated from gas tips (not exact coinbase transfers)
- ⚠️ **Gas estimation**: Uses 80% of gas_limit as approximation (not exact gas_used)
- ⚠️ **Success assumption**: Assumes all transactions succeeded (no receipt data available)

### Design Limitations
- For exact profit, you'd need execution traces (which require Reth)
- For exact gas, you'd need transaction receipts (which come from simulation)
- But for testing selection algorithms, estimates are sufficient!

## Next Steps to Fix

1. **Modify builder to handle missing parent blocks gracefully**
   - When using `MockRootHasher`, parent block lookup by number should be optional
   - Or catch the error and continue with a dummy parent state

2. **Alternative: Use different provider**
   - Create a custom provider that doesn't require sequential blocks
   - Or use a provider that can map block numbers to hashes flexibly

3. **Alternative: Insert sequential blocks**
   - Insert blocks from genesis to parent (not practical for high block numbers)
   - Or insert parent block with correct number mapping somehow

## Troubleshooting

- **"Block not found"**: Make sure you've fetched the block first with `backtest-fetch`
- **"Builder not found"**: Check your config file has the builder defined
- **"Missing historical block hash"**: This is the current limitation - see "Next Steps to Fix" above
- **Low profit values**: This is expected - we're using gas tip estimates, not full MEV extraction

## Comparison with `backtest-build-block`

| Feature | `backtest-build-block` | `backtest-build-block-no-sim` |
|---------|----------------------|------------------------------|
| Requires Reth | ✅ Yes (local DB or IPC) | ❌ No |
| Transaction Simulation | ✅ Full EVM execution | ❌ Uses pre-computed values |
| Profit Accuracy | ✅ Exact (from execution) | ⚠️ Estimated (from gas tips) |
| Gas Accuracy | ✅ Exact (from receipts) | ⚠️ Estimated (80% of limit) |
| Speed | ⚠️ Slow (simulation) | ✅ Fast (no simulation) |
| Status | ✅ Working | ⚠️ Builds but runtime error |

## Code Location

- **Binary**: `crates/rbuilder/src/bin/backtest-build-block-no-sim.rs`
- **Helper script**: `run-backtest.sh` (command: `test-no-sim`)
- **Key functions**:
  - `extract_historical_profit_gas()`: Extracts gas/profit from block transactions
  - `create_simulated_orders_from_historical_data()`: Creates SimulatedOrder objects
  - `main()`: Orchestrates the process

## Future Improvements

1. Fix parent block lookup issue
2. Improve profit estimation (use base fee + tips, not just tips)
3. Add option to use actual gas_used from receipts if available
4. Add option to use actual coinbase profit from execution traces
5. Support multiple blocks in one run
6. Export knapsack instances for LPU emulator
