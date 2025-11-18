# Running Greedy Knapsack Algorithm on Real Mempool Blocks

This guide shows you how to run rbuilder's greedy knapsack algorithm on a real mempool block (current or historic) and get the output result with the suggested transactions.

## Prerequisites

1. **Database with blocks**: You should have blocks fetched in your database
2. **Config set**: Make sure `RBUILDER_CONFIG_PATH` is set or use default config
3. **Environment variables**: `.env` file should be loaded (handled automatically by scripts)
4. **Reth database** (REQUIRED for `backtest-build-block`): `backtest-build-block` needs a local Reth node database for state access to simulate transactions. You have two options:
   - **Option A**: Run a local Reth node synced to mainnet/sepolia
   - **Option B**: Use QuickNode RPC (may work but requires code changes - see troubleshooting)

**Important**: 
- `backtest-fetch` works without Reth (uses QuickNode RPC) ✅
- `backtest-build-block` **requires** a local Reth node for state simulation ❌
  - You need either a Reth database (`reth_datadir`) or IPC connection (`ipc_provider`)
  - HTTP RPC is not supported for state provider in block building
- `backtest-build-block-no-sim` **does NOT require Reth** ⚠️
  - Uses historical execution data instead of re-simulation
  - ⚠️ **Currently has runtime limitation** (see `RUN_NO_SIM_GUIDE.md` for details)
  - Builds successfully but fails when builder accesses parent block by number

## Step 1: Check Available Blocks

First, see what blocks you have in your database:

```bash
cd /Users/matanfield/Projects/lightsolver/rbuilder

# List blocks in database
export RBUILDER_CONFIG_PATH=config-mainnet-backtest.toml
./run-backtest.sh list  # If this command exists, or:
cargo run --release --bin backtest-fetch -- --config config-mainnet-backtest.toml list
```

This shows: `block_number,block_hash,order_count,profit`

## Step 2: Run Greedy Algorithm on a Block

### Option A: With Reth (Full Simulation) - Recommended

```bash
# Test greedy algorithm on a single block
export RBUILDER_CONFIG_PATH=config-mainnet-backtest.toml
./run-backtest.sh test-greedy 18920000
```

### Option B: Without Reth (No Simulation) - ⚠️ Currently Limited

```bash
# Test greedy algorithm without Reth (uses historical data)
export RBUILDER_CONFIG_PATH=config-mainnet-backtest.toml
./run-backtest.sh test-no-sim 18920000 greedy-mp-ordering
```

**Note**: `backtest-build-block-no-sim` builds successfully but currently has a runtime limitation. See `RUN_NO_SIM_GUIDE.md` for details and status.

### Basic Run (Summary Output)

This gives you:
- Builder profit
- Number of orders included
- Order IDs included

### Detailed Run (With Transaction Hashes)

To get the **full transaction list** with all transaction hashes:

```bash
export RBUILDER_CONFIG_PATH=config-mainnet-backtest.toml

cargo run --release --bin backtest-build-block -- \
  --config config-mainnet-backtest.toml \
  --builders greedy-mp-ordering \
  --trace-block-building \
  18920000
```

**Key flags:**
- `--builders greedy-mp-ordering`: Uses the greedy max-profit algorithm
- `--trace-block-building`: Shows detailed execution trace with all transactions
- `18920000`: Block number to test

### Even More Detail

For maximum detail including all available orders and simulation results:

```bash
cargo run --release --bin backtest-build-block -- \
  --config config-mainnet-backtest.toml \
  --builders greedy-mp-ordering \
  --trace-block-building \
  --show-orders \
  --show-sim \
  18920000
```

**Additional flags:**
- `--show-orders`: Shows all available orders with timestamps
- `--show-sim`: Shows simulation results for all orders

## Step 3: Understanding the Output

### Summary Output Format

```
Built block 18920000 with builder: "greedy-mp-ordering"
Builder profit: 0.123456 ETH
Number of used orders: 42
OrderID123... gas: 21000 profit: 0.001 ETH
  ↳ 0xabc123... (transaction hash)
OrderID456... gas: 50000 profit: 0.002 ETH
  ↳ 0xdef456... (transaction hash)
  ↳ 0x789abc... (transaction hash)
...
Winning builder: greedy-mp-ordering with profit: 0.123456 ETH
```

### Transaction Output Format

Each included order shows:
- **Order ID**: Unique identifier for the order/bundle
- **Gas used**: Gas consumed by this order
- **Profit**: Coinbase profit from this order
- **Transaction hashes** (indented): All transaction hashes included in this order
  - For bundles: Multiple transactions
  - For single transactions: One transaction hash

### Order Types

- **Single Transaction**: One transaction hash
- **Bundle**: Multiple transaction hashes (shown indented)
- **ShareBundle**: MEV-share bundle with multiple transactions

## Step 4: Export Transaction List

To extract just the transaction hashes, you can pipe the output:

```bash
cargo run --release --bin backtest-build-block -- \
  --config config-mainnet-backtest.toml \
  --builders greedy-mp-ordering \
  --trace-block-building \
  18920000 2>&1 | grep "↳" | awk '{print $2}'
```

This extracts all transaction hashes from the output.

## Step 5: Run on Current/Recent Blocks

### Option A: Use Already Fetched Recent Blocks

If you've already fetched recent blocks:

```bash
# Get current block number
CURRENT=$(curl -s -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  "$(grep QUICK_NODE_ETH_MAINNET_API_URL_HTTP .env | cut -d'=' -f2-)" | \
  python3 -c "import sys, json; print(int(json.load(sys.stdin)['result'], 16))")

# Run on most recent block in database (or fetch it first)
./run-backtest.sh test-greedy $CURRENT
```

### Option B: Fetch Recent Block First

```bash
# Fetch last hour of blocks (~300 blocks)
export RBUILDER_CONFIG_PATH=config-mainnet-backtest.toml
./run-backtest.sh fetch recent 1

# Then run on the latest block
# (Check what blocks were fetched with 'list' command)
```

## Example: Complete Workflow

```bash
cd /Users/matanfield/Projects/lightsolver/rbuilder

# 1. Set config
export RBUILDER_CONFIG_PATH=config-mainnet-backtest.toml

# 2. Check available blocks
cargo run --release --bin backtest-fetch -- --config config-mainnet-backtest.toml list | tail -5

# 3. Run greedy algorithm with full transaction details
cargo run --release --bin backtest-build-block -- \
  --config config-mainnet-backtest.toml \
  --builders greedy-mp-ordering \
  --trace-block-building \
  18920000

# 4. Extract transaction hashes to a file
cargo run --release --bin backtest-build-block -- \
  --config config-mainnet-backtest.toml \
  --builders greedy-mp-ordering \
  --trace-block-building \
  18920000 2>&1 | grep "↳" | awk '{print $2}' > transactions.txt
```

## Output Files

The transaction list will be in the format:
```
0xabc123def456789...
0xdef456abc123789...
0x789abc123def456...
```

Each line is a transaction hash that the greedy algorithm selected to include in the block.

## Next Steps

After getting the transaction list:

1. **Compare with your algorithm**: Run your custom algorithm and compare transaction selection
2. **Export knapsack instance**: The next step is to export the full knapsack problem (items, profits, conflicts) for LPU emulator
3. **Analyze results**: Compare profit, gas usage, and transaction selection patterns

## Troubleshooting

### "DB open error" / "Could not open database"

**Problem**: `backtest-build-block` requires a Reth database for state access.

**Solutions**:

1. **Set up Reth database** (Recommended):
   ```bash
   # Install Reth and sync to mainnet/sepolia
   # Then set in config:
   reth_datadir = "/path/to/reth/datadir"
   # Or set environment variable:
   export RETH_DATADIR=/path/to/reth/datadir
   ```

2. **Use IPC provider** (if Reth is running):
   ```toml
   ipc_provider = "/tmp/reth-mainnet.ipc"
   ```

3. **Alternative**: The codebase may support RPC providers, but this requires checking if `create_reth_provider_factory` can use RPC instead of local DB.

### Other Issues

- **"Block not found"**: Make sure you've fetched the block first with `backtest-fetch`
- **"No orders"**: The block might not have mempool data. Try a different block or fetch recent blocks
- **"Builder not found"**: Make sure `greedy-mp-ordering` is defined in your config file

## Available Builders

Check your config file (`config-mainnet-backtest.toml`) for available builders:
- `greedy-mp-ordering`: Greedy max-profit ordering
- `greedy-mgp-ordering`: Greedy MEV gas price ordering

You can test multiple builders:
```bash
cargo run --release --bin backtest-build-block -- \
  --config config-mainnet-backtest.toml \
  --builders greedy-mp-ordering \
  --builders greedy-mgp-ordering \
  --trace-block-building \
  18920000
```

This will show which builder performs better!

