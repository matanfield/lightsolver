# LPU Knapsack for Ethereum Block Building

## Project Name
LightSolver × MEV – LPU Knapsack Superiority Proof-of-Concept

## Current and ONLY goal (Nov 2025)
Prove on real Ethereum data that a perfect (or near-perfect knapsack solver on ~10 000 items (bundles + mempool txs) creates enough extra builder profit to justify building a large-scale LPU.

Everything else (production builder, beating Flashbots, etc.) is postponed until this single question has a clear, positive answer.

## Why this matters
- The hardest sub-problem in block building is the repeatedly solved multi-dimensional knapsack (gas + dependencies + coinbase payments + blob constraints).
- Today everyone (Flashbots, Beaver, Titan, rsync…) uses greedy + local search on CPU/GPU → provably sub-optimal.
- If we can show that solving the knapsack exactly (or 99.9 % optimal) on 5k–10k items adds even $5k–$20k of extra profit on an average slot, the business case for a big LPU is made.

## What we actually need to do right now (step-by-step)

1. Get vanilla rbuilder running on a recent mainnet slot  
   → baseline greedy profit number  
   (we already compile, next is live or historical run)

2. Export the exact knapsack instance that rbuilder solves in that slot:
   - list of bundles + mempool txs considered
   - profit of each item
   - gas used
   - conflict graph (which items exclude which)
   - coinbase payment overrides
   → this is the input for the emulator

3. Feed the exact same instance to the LPU emulator (GPU version is fine) and let it run until ≤ 0.1 % from optimal (may take minutes instead of 50 ms – acceptable for the experiment)

4. Compare:
   - greedy profit (from step 1)
   - near-optimal profit (from step 3)
   → delta in USD per slot, extrapolated to yearly revenue

5. Using internal LPU cycle counts, estimate how long the same instance would take on real LPU hardware at n = 10k scale  
   → proves real-time feasibility

## Current Progress (Updated Nov 2025)

### ✅ Build & Infrastructure
- **rbuilder vendored and compiles on macOS arm64** ✓
- **Fixed runng-sys CMake compatibility issue** ✓
  - Added `build.rs` to `crates/bid-scraper` to set `CMAKE_POLICY_VERSION_MINIMUM=3.5`
  - Permanent fix for CMake 4.x compatibility
- **Backtest binaries working** ✓
  - `backtest-fetch`: Fetches historical block and mempool data
  - `backtest-build-block`: Tests algorithms on single blocks (requires Reth)
  - `backtest-build-block-no-sim`: Tests algorithms without Reth (⚠️ builds but has runtime limitation)
  - `backtest-build-range`: Tests algorithms on block ranges with comparison

### ✅ Data Infrastructure
- **Historical data fetching operational** ✓
  - Mainnet: 67 blocks fetched (18920000-18920200)
  - 165,665 mempool orders stored
  - Database: `~/.rbuilder/backtest/mainnet.sqlite` (390 MB)
- **Mempool data source configured** ✓
  - Using mempool-dumpster (https://mempool-dumpster.flashbots.net/)
  - Stores transactions in `~/.rbuilder/mempool-data/{network}/`
- **Relay payload handling improved** ✓
  - Made payload requirement optional (`backtest_require_payload_from_relays = false`)
  - Falls back to fake payload when relays don't have data
  - Still fetches real mempool transactions regardless

### ✅ Automation & Scripts
- **`run-backtest.sh`**: Main helper script for backtesting
  - Automatically loads `.env` file
  - Resolves `env:VAR_NAME` placeholders in config files
  - Commands: `fetch`, `test-greedy`, `test-range`, `compare`
- **`fetch-recent-blocks.sh`**: Automatically fetches recent blocks
  - Calculates block range based on hours back
  - Default: last 24 hours (~7,200 blocks)
- **Configuration files**:
  - `config-mainnet-backtest.toml`: Mainnet backtesting config
  - `config-sepolia-backtest.toml`: Sepolia backtesting config

## Data Storage & Database

### Database Locations
- **Mainnet**: `/Users/matanfield/.rbuilder/backtest/mainnet.sqlite`
  - Current: 67 blocks (18920000-18920200)
  - 165,665 orders stored
  - Size: 390 MB
- **Sepolia**: `/Users/matanfield/.rbuilder/backtest/sepolia.sqlite`
  - Size: 36 KB (minimal data)

### Database Schema
The SQLite databases contain:
- `blocks`: Block metadata (number, hash, timestamp)
- `orders`: Mempool transactions/orders (bundles, transactions)
- `blocks_data`: Full block data
- `built_block_included_orders`: Which orders were included in built blocks
- `built_block_data`: Built block results for comparison

### Mempool Data Storage
- **Location**: `~/.rbuilder/mempool-data/{network}/transactions/`
- **Source**: mempool-dumpster (Flashbots)
- **Format**: Parquet files (one per day)
- **Usage**: Provides historical mempool transactions for knapsack algorithm testing

### No-Simulation Backtesting (`backtest-build-block-no-sim`)

**Status**: ⚠️ Builds successfully but has runtime limitation

**Purpose**: Run knapsack algorithms without requiring Reth state by using historical execution data

**What Works**:
- ✅ Loads historical block and order data from SQLite database
- ✅ Extracts gas and estimates profit from block transactions
- ✅ Creates `SimulatedOrder` objects with pre-computed values
- ✅ Sets up test chain state and provider factory
- ✅ Inserts parent block header with correct hash

**Current Limitation**:
- ⚠️ Runtime error when builder accesses parent block by number
  - Error: `Missing historical block hash for block 18920192`
  - Root cause: Test provider requires sequential blocks, but builder looks for parent by number
  - Impact: Selection algorithm cannot complete execution

**Technical Approach**:
- Estimates gas used as 80% of `gas_limit` (typical for most transactions)
- Estimates profit from gas tips: `gas_tip * estimated_gas`
- Uses `MockRootHasher` to avoid needing real state
- Creates `SimulatedOrder` objects with `SimValue::new_test()`

**Next Steps to Fix**:
1. Modify builder to handle missing parent blocks gracefully when using `MockRootHasher`
2. Or create custom provider that doesn't require sequential blocks
3. Or insert parent block with correct number mapping

**See**: `RUN_NO_SIM_GUIDE.md` for detailed documentation

## Resources & Dependencies

### External Services
1. **QuickNode** (RPC Provider)
   - **Mainnet**: `QUICK_NODE_ETH_MAINNET_API_URL_HTTP` / `QUICK_NODE_ETH_MAINNET_API_URL_WSS`
   - **Sepolia**: `QUICK_NODE_ETH_SPOLIA_API_URL_HTTP` / `QUICK_NODE_ETH_SPOLIA_API_URL_WSS`
   - **Purpose**: On-chain block data, current block numbers, transaction data
   - **Rate limits**: Configurable via `backtest_fetch_eth_rpc_parallel` (default: 10)

2. **Mempool-Dumpster** (Mempool Data)
   - **URL**: https://mempool-dumpster.flashbots.net/
   - **Purpose**: Historical mempool transactions
   - **Format**: Parquet files organized by date
   - **Network support**: Mainnet, Sepolia
   - **Usage**: Automatically downloaded by `backtest-fetch`

3. **MEV Relays** (Optional Payload Data)
   - **Flashbots**: Primary relay (most reliable)
   - **Eden Network**: Fallback relay
   - **Ultrasound Money**: Additional relay
   - **Purpose**: "Payload delivered" traces for comparing against actual winning bids
   - **Note**: Not required for knapsack algorithm testing (only needed for comparison)

### Local Dependencies
- **Rust/Cargo**: Build system
- **CMake**: Required for `runng-sys` (native messaging library)
- **Python 3**: Used by scripts for environment variable resolution
- **SQLite**: Database storage (via `sqlx` crate)

## Configuration

### Environment Variables (`.env` file)
```bash
# QuickNode endpoints
QUICK_NODE_ETH_MAINNET_API_URL_HTTP=https://...
QUICK_NODE_ETH_MAINNET_API_URL_WSS=wss://...
QUICK_NODE_ETH_SPOLIA_API_URL_HTTP=https://...
QUICK_NODE_ETH_SPOLIA_API_URL_WSS=wss://...

# Optional: Local Reth node
RETH_DATADIR=/path/to/reth/datadir

# Config selection
RBUILDER_CONFIG_PATH=config-mainnet-backtest.toml  # or config-sepolia-backtest.toml
```

### Config File Structure
- **Base config**: `config-mainnet-backtest.toml` / `config-sepolia-backtest.toml`
- **Key settings**:
  - `backtest_fetch_output_file`: Database location
  - `backtest_fetch_mempool_data_dir`: Mempool data storage
  - `backtest_require_payload_from_relays`: Whether to require relay payloads (default: `false`)
  - `backtest_builders`: List of algorithms to test
  - `[[builders]]`: Algorithm configurations (greedy-mp-ordering, greedy-mgp-ordering, etc.)

## Recent Changes & Improvements

### 1. Build Fixes
- **runng-sys CMake compatibility**: Added `build.rs` to `crates/bid-scraper` to set `CMAKE_POLICY_VERSION_MINIMUM=3.5` before build
- **Environment variable resolution**: Scripts now properly resolve `env:VAR_NAME` placeholders in config files

### 2. Data Fetching Improvements
- **Optional relay payloads**: Added `backtest_require_payload_from_relays` config option
  - When `false`: Uses fake payload when relays don't respond
  - Allows fetching blocks with mempool data even without relay traces
- **Better error handling**: `--ignore-errors` flag skips blocks with errors instead of failing entire fetch
- **Recent blocks script**: `fetch-recent-blocks.sh` automatically calculates and fetches recent blocks

### 3. Automation
- **`run-backtest.sh` improvements**:
  - Auto-loads `.env` file
  - Resolves environment variables in config files
  - Supports `fetch recent [hours]` command
  - Network switching via `RBUILDER_CONFIG_PATH`
  - Added `test-no-sim` command for running algorithms without Reth

### 4. No-Simulation Backtesting (Nov 2025)
- **New binary**: `backtest-build-block-no-sim` - Runs knapsack algorithms without Reth state
- **Implementation**: 
  - Extracts gas/profit from historical block transactions
  - Estimates gas used (80% of gas_limit) and profit (from gas tips)
  - Creates `SimulatedOrder` objects with pre-computed values
  - Uses `MockRootHasher` to avoid needing real state
- **Status**: ✅ Builds successfully, ⚠️ Runtime limitation (parent block lookup issue)
- **Purpose**: Test selection algorithms without requiring Reth sync (saves days + terabytes)
- **See**: `RUN_NO_SIM_GUIDE.md` for complete documentation

## Usage Examples

### Fetch Historical Data
```bash
cd /Users/matanfield/Projects/lightsolver/rbuilder

# Set config
export RBUILDER_CONFIG_PATH=config-mainnet-backtest.toml

# Fetch recent blocks (last 24 hours)
./run-backtest.sh fetch recent

# Fetch specific range
./run-backtest.sh fetch 18920000 18920200
```

### Run Baseline (Greedy Algorithm)
```bash
# Test single block
./run-backtest.sh test-greedy 18920000

# Test range and store results
./run-backtest.sh test-range 18920000 18920100
```

### Compare Custom Algorithm
```bash
# After implementing your algorithm, add it to config and compare:
./run-backtest.sh compare 18920000 18920100
```

### Inspect Database
```bash
# List blocks in database
cargo run --release --bin backtest-fetch -- --config config-mainnet-backtest.toml list

# Query directly
sqlite3 ~/.rbuilder/backtest/mainnet.sqlite "SELECT * FROM blocks LIMIT 10;"
```

## Immediate Next Actions

### Priority 1: Fix No-Simulation Backtesting
1. **Fix parent block lookup**: Resolve runtime error in `backtest-build-block-no-sim`
   - Modify builder to handle missing parent blocks gracefully when using `MockRootHasher`
   - Or create custom provider that doesn't require sequential blocks
2. **Validate end-to-end**: Verify selection algorithm runs successfully without Reth
3. **Compare with simulation**: When Reth is available, compare no-sim vs full-sim results

### Priority 2: Knapsack Testing Workflow
1. ✅ **Fetch historical data** - DONE (67 mainnet blocks stored)
2. ✅ **Run greedy baseline** - Ready to run (`./run-backtest.sh test-range` or `test-no-sim` when fixed)
3. **Export knapsack instances** - Instrument `backtest-build-block` or `backtest-build-block-no-sim` to dump:
   - List of bundles + mempool txs considered
   - Profit of each item
   - Gas used
   - Conflict graph (which items exclude which)
   - Coinbase payment overrides
4. **Feed to LPU emulator** - Connect dump format to emulator input pipeline
5. **Compare results** - Get first "greedy $X → near-optimal $Y" number

## Key Files & Directories

```
rbuilder/
├── config-mainnet-backtest.toml      # Mainnet config
├── config-sepolia-backtest.toml       # Sepolia config
├── run-backtest.sh                    # Main helper script
├── fetch-recent-blocks.sh             # Recent blocks fetcher
├── setup-mempool-data.sh              # Mempool data setup
├── RUN_NO_SIM_GUIDE.md                # Guide for no-simulation backtesting
├── RUN_KNAPSACK_GUIDE.md              # Guide for running knapsack algorithms
├── .env                               # Environment variables (not in git)
├── crates/
│   ├── bid-scraper/
│   │   └── build.rs                   # CMake fix for runng-sys
│   └── rbuilder/
│       ├── src/
│       │   ├── bin/
│       │   │   └── backtest-build-block-no-sim.rs  # No-sim binary
│       │   ├── backtest/              # Backtest implementation
│       │   └── live_builder/
│       │       └── base_config.rs     # Config with backtest_require_payload_from_relays
│       └── build.rs                   # Build script
└── docs/
    └── project.md                     # This file

~/.rbuilder/
├── backtest/
│   ├── mainnet.sqlite                 # Mainnet database (390 MB)
│   └── sepolia.sqlite                 # Sepolia database (36 KB)
└── mempool-data/
    ├── mainnet/                       # Mainnet mempool transactions
    └── sepolia/                       # Sepolia mempool transactions
```

## Notes

- **Relay payloads are optional**: You don't need relay payload data to run your knapsack algorithm - you just need mempool transactions, which are now fetched reliably from mempool-dumpster.
- **Mainnet vs Sepolia**: Mainnet has significantly more MEV activity. Use mainnet for realistic benchmarking.
- **Database growth**: Each block adds ~5-6 MB to the database. Plan storage accordingly.
- **Rate limits**: QuickNode has rate limits. Adjust `backtest_fetch_eth_rpc_parallel` if hitting limits.

Once we have that number and it is big, the rest of the builder war becomes worth fighting. Until then, everything else is noise.