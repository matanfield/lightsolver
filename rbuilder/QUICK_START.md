# Quick Start - Running Backtests

## Basic Usage

Make sure you're in the rbuilder directory:

```bash
cd /Users/matanfield/Projects/lightsolver/rbuilder
```

Then run commands with `./` prefix:

```bash
# Fetch historical data
./run-backtest.sh fetch <from_block> <to_block>

# Test greedy algorithm on a single block
./run-backtest.sh test-greedy <block_number>

# Test greedy algorithm on a range (stores results)
./run-backtest.sh test-range <from_block> <to_block>

# Compare your custom algorithm vs stored greedy results
./run-backtest.sh compare <from_block> <to_block>
```

## Examples

**Note:** Use recent blocks that have MEV activity. For Sepolia, current block is ~9.6M, so try blocks from the last few thousand:
- Sepolia: Try blocks like 9650000-9650100 (recent blocks)
- Mainnet: Blocks with MEV activity (check mempool-dumpster for active blocks)

```bash
# Fetch recent Sepolia blocks (adjust to current block - few thousand)
./run-backtest.sh fetch 9650000 9650100  # Internally uses --ignore-errors

# Test greedy on a recent block
./run-backtest.sh test-greedy 9650000

# Test greedy on range and store results
./run-backtest.sh test-range 9650000 9650100
```

**Finding blocks with MEV:**
- Check mempool-dumpster for blocks with high order counts
- Try blocks from the last few days/weeks
- Mainnet typically has more MEV activity than Sepolia

## Environment Variables

The script automatically loads from `.env` file. Make sure your `.env` has:
- `QUICK_NODE_ETH_SPOLIA_API_URL_HTTP=...`
- `QUICK_NODE_ETH_SPOLIA_API_URL_WSS=...`
- (optional) `QUICK_NODE_ETH_MAINNET_API_URL_HTTP=...`
- (optional) `QUICK_NODE_ETH_MAINNET_API_URL_WSS=...`
- `RETH_DATADIR=...` (optional, if using local Reth node)

## Choosing the Network

- Sepolia is the default: the script uses `config-sepolia-backtest.toml`.
- To switch to mainnet, set the config override before running:
  ```bash
  export RBUILDER_CONFIG_PATH=config-mainnet-backtest.toml
  ./run-backtest.sh fetch 18900000 18900100
  ```

