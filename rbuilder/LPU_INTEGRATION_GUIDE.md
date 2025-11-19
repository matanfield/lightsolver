# LPU Integration Quick Reference

## File Locations

```
/Users/matanfield/Projects/lightsolver/rbuilder/

├── knapsack_instance_*.json          ← YOUR INPUT DATA (6 files, ~2k items each)
├── BACKTEST_RESULTS.md               ← Performance summary
├── BACKTEST_FAQ.md                   ← Detailed Q&A (read this!)
└── crates/rbuilder/src/
    └── building/builders/
        └── ordering_builder.rs       ← GREEDY ALGORITHM (line 396-476)
                                         Replace fill_orders() to integrate LPU
```

## Greedy Algorithm Flow

```
INPUT: ~2,000 SimulatedOrder objects
    ↓
SORT by priority (max-profit or mev-gas-price)
    ↓
LOOP:
    Pop next order from sorted list
        ↓
    Try commit_order() to block
        ↓
    If success: keep in block
    If fail: discard, try next
        ↓
    Repeat until time limit or gas full
    ↓
OUTPUT: Built block with greedy selection
```

**Location**: `ordering_builder.rs:396-476`
```rust
fn fill_orders(...) {
    while let Some(sim_order) = block_orders.pop_order() {
        block_building_helper.commit_order(&mut self.local_ctx, &sim_order, ...)?;
    }
}
```

## Your LPU Integration Options

### Option A: Offline (CURRENT - RECOMMENDED FOR NOW)

```bash
# Step 1: Already done - you have the files!
ls knapsack_instance_*.json

# Step 2: Feed to your LPU emulator
./your_lpu_emulator \
  --input knapsack_instance_21200001.json \
  --output lpu_solution.json \
  --timeout 10s \
  --optimize-for profit

# Step 3: Compare results
# Greedy: 0.002606 ETH (from BACKTEST_RESULTS.md)
# LPU:    ??? ETH (your output)
# Delta:  ??? ETH (this is your KEY NUMBER!)
```

**Expected LPU Output Format**:
```json
{
  "block_number": 21200001,
  "selected_orders": [
    "tx:0x8ee1683d8d6fa20bed576a6b7d6c652dd67dbc71500e4cddc245183be581352f",
    "tx:0xf6f10d95c2644cc7b17c7368f91e768c0008374b9e93197087283661b38e4557",
    ...
  ],
  "total_profit": "0x...",      // hex wei
  "total_gas": 29500000,
  "compute_time_ms": 8234,
  "solution_quality": 0.999     // % of optimal (if known)
}
```

### Option B: API Integration (FUTURE)

When ready to integrate:

**1. LPU Emulator as HTTP Server**
```bash
# Start LPU emulator in server mode
./your_lpu_emulator --serve --port 8080
```

**2. Modify rbuilder**
Create `crates/rbuilder/src/building/builders/lpu_builder.rs`:
```rust
pub fn run_lpu_builder<P>(
    input: LiveBuilderInput<P>,
    config: &LpuBuilderConfig,
) where P: StateProviderFactory + Clone + 'static {
    // Convert orders to knapsack format
    let instance = to_knapsack_instance(&orders);
    
    // Call LPU API
    let response = reqwest::blocking::Client::new()
        .post(&format!("{}/solve", config.api_endpoint))
        .json(&instance)
        .timeout(config.timeout)
        .send()?
        .json::<LpuSolution>()?;
    
    // Commit orders in optimal order
    for order_id in response.selected_orders {
        commit_order(order_id)?;
    }
}
```

**3. Configure**
```toml
# config-mainnet-backtest.toml
backtest_builders = ["greedy-mp-ordering", "lpu-knapsack"]

[[builders]]
name = "lpu-knapsack"
algo = "lpu-builder"
api_endpoint = "http://localhost:8080"
timeout_ms = 10000
```

**4. Run comparison**
```bash
cargo run --release -p rbuilder --bin backtest-build-block-no-sim -- \
  --config config-mainnet-backtest.toml \
  --builders greedy-mp-ordering \
  --builders lpu-knapsack \
  21200001
```

## Key Code Locations

### 1. Greedy Algorithm
**File**: `crates/rbuilder/src/building/builders/ordering_builder.rs`
- **Line 86-233**: Main `run_ordering_builder()` function
- **Line 396-476**: `fill_orders()` - THE GREEDY LOOP
- **Line 405**: `while let Some(sim_order) = block_orders.pop_order()` ← This pops next sorted order

### 2. Order Sorting
**File**: `crates/rbuilder/src/building/mod.rs`
- **Sorting enum**: Defines `MaxProfit`, `MevGasPrice`, etc.
- **PrioritizedOrderStore**: Maintains sorted order queue

### 3. Knapsack Export
**File**: `crates/rbuilder/src/bin/backtest-build-block-no-sim.rs`
- **Line 355-391**: Exports knapsack instance to JSON
- **Line 40-56**: KnapsackInstance struct definition

### 4. Data Filtering
**File**: `crates/rbuilder/src/backtest/fetch/mempool.rs`
- **Line 25-59**: Fetches mempool data from dumpster
- **Line 111-117**: 3-minute time window filter

**File**: `crates/rbuilder/src/backtest/mod.rs`
- **Line 96-113**: Timestamp filtering
- **Line 132-165**: Replacement filtering
- **Line 167-192**: Bundle deduplication

## Quick Commands

### Export more knapsack instances
```bash
cd /Users/matanfield/Projects/lightsolver/rbuilder
source ~/.cargo/env

# Export single block
cargo run --release -p rbuilder --bin backtest-build-block-no-sim -- \
  --config config-mainnet-backtest.toml \
  --builders greedy-mp-ordering \
  21200006

# Export range (blocks 6-10)
for block in {21200006..21200010}; do
  cargo run --release -p rbuilder --bin backtest-build-block-no-sim -- \
    --config config-mainnet-backtest.toml \
    --builders greedy-mp-ordering \
    $block 2>&1 | grep -E "(Total Value|Orders Included|Exported)"
done
```

### Fetch more blocks
```bash
# Fetch next 100 blocks
export RBUILDER_CONFIG_PATH=config-mainnet-backtest.toml
./run-backtest.sh fetch 21200011 21200110
```

### Inspect knapsack instance
```bash
# Show summary
cat knapsack_instance_21200001.json | jq '{
  block_number,
  total_items: (.items | length),
  total_gas: (.items | map(.gas) | add),
  profitable_items: (.items | map(select(.profit != "0x0")) | length)
}'

# Show top 10 most profitable items
cat knapsack_instance_21200001.json | jq '.items | 
  map({id, profit: .profit, gas}) | 
  sort_by(.profit) | 
  reverse | 
  .[0:10]'
```

## ROI Calculator

```python
# roi_calculator.py
greedy_profit_eth = 0.002606
lpu_profit_eth = ???  # Your result

improvement_eth = lpu_profit_eth - greedy_profit_eth
improvement_pct = (improvement_eth / greedy_profit_eth) * 100

blocks_per_day = 7200
blocks_per_year = 7200 * 365

daily_improvement = improvement_eth * blocks_per_day
yearly_improvement = improvement_eth * blocks_per_year

eth_price = 2500
yearly_usd = yearly_improvement * eth_price

print(f"Improvement: {improvement_eth:.6f} ETH ({improvement_pct:.2f}%)")
print(f"Daily extra: {daily_improvement:.4f} ETH (${daily_improvement * eth_price:,.2f})")
print(f"Yearly extra: {yearly_improvement:.2f} ETH (${yearly_usd:,.0f})")
```

## Success Metrics

### Minimum Viable Improvement
- **5% improvement** → Worth investigating further
- **10% improvement** → Strong business case
- **20%+ improvement** → Clear competitive advantage

### Time Budget
- **Greedy**: 2-4ms per block
- **Available**: ~12 seconds per slot
- **LPU budget**: Up to 10 seconds per block
- **Overhead allowance**: 2 seconds

If LPU can solve in < 10 seconds with > 5% improvement → **VIABLE!**

## Next Actions

1. ✅ **DONE**: Export knapsack instances
2. **YOUR TURN**: Feed `knapsack_instance_21200001.json` to LPU emulator
3. **YOUR TURN**: Measure LPU profit vs greedy (0.002606 ETH baseline)
4. **YOUR TURN**: Calculate ROI using formula above
5. **TOGETHER**: If ROI positive, plan API integration (Option B/C)

---

**Quick Reference**:
- Knapsack files: `knapsack_instance_*.json` (6 files, ~2k items each)
- Greedy baseline: 0.002606 ETH (block 21200001, best example)
- Greedy code: `ordering_builder.rs:fill_orders()` (line 396)
- Integration point: Replace `fill_orders()` with LPU API call
