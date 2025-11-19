# Backtest FAQ - Understanding the Data & Integration Points

## 1. Why only ~2,000 txs instead of ~150k?

The ~2,000 transactions are **NOT the full mempool**. They are the **available orders at block building time** after multiple filters:

### Temporal Filtering
- **Time window**: 3 minutes before block timestamp to 5 seconds after
- **Source**: `fetch/mempool.rs:114-117`
```rust
let block_time = OffsetDateTime::from_unix_timestamp(block.block_timestamp as i64)?;
(
    block_time - Duration::minutes(3),  // 3 min before
    block_time + Duration::seconds(5),   // 5 sec after
)
```

### Applied Filters (source: `backtest/mod.rs`)
1. **Timestamp filter** - Orders received after building started
2. **Replaced orders** - Transaction replacements (same nonce, higher gas)
3. **Bundles from mempool** - Bundles composed entirely of public mempool txs (redundant)
4. **Custom filters** - Builder-specific order filtering

### Why this makes sense
- A block builder doesn't process the ENTIRE mempool
- They process what's **available and relevant** at the moment they start building
- ~2,000 is actually realistic for a block building time window

## 2. Is this the full list or pre-filtered?

**This is the PRE-FILTERED list** ready for the knapsack algorithm.

The full processing pipeline:
```
mempool-dumpster (full mempool) 
    → temporal filter (3min window) 
    → validation filter (parse errors, etc)
    → timestamp filter (late arrivals)
    → replacement filter (keep newest)
    → bundle deduplication (remove redundant bundles)
    → custom filters (builder-specific)
    → AVAILABLE ORDERS (~2,000)
         ↓
    [YOUR KNAPSACK INPUT]
```

The ~2,000 orders are:
- ✅ Valid transactions
- ✅ Arrived on time
- ✅ No duplicates/replacements  
- ✅ Non-redundant bundles
- ✅ Ready for block inclusion

This is exactly what you want for knapsack - clean, validated orders.

## 3. Is this what we run the knapsack on?

**YES!** This is the exact input to the selection algorithm.

The exported `knapsack_instance_*.json` files contain:
- All ~2,000 available orders
- Gas usage for each
- Profit estimation for each
- Nonce dependencies (conflict graph)

This is the complete knapsack problem instance.

## 4. Where's the Greedy? How to Replace with LPU?

### Greedy Algorithm Location

**File**: `crates/rbuilder/src/building/builders/ordering_builder.rs`

**Main Loop** (line 396-476):
```rust
fn fill_orders<OrderPriorityType: OrderPriority, OrderFilter>(
    &mut self,
    block_building_helper: &mut dyn BlockBuildingHelper,
    block_orders: &mut PrioritizedOrderStore<OrderPriorityType>,  // ← SORTED INPUT
    order_filter: OrderFilter,
    build_start: Instant,
    deadline: Option<Duration>,
) -> eyre::Result<()> {
    // GREEDY LOOP: Pop orders one by one from sorted list
    while let Some(sim_order) = block_orders.pop_order() {  // ← POP NEXT
        if sim_order.sim_value.gas_used() == 0 || !order_filter(&sim_order) {
            continue;
        }
        
        // Try to commit order to block
        let commit_result = block_building_helper.commit_order(
            &mut self.local_ctx,
            &sim_order,
            &|sim_result| {
                simulation_too_low::<OrderPriorityType>(&sim_order.sim_value, sim_result)
            },
        )?;
        
        // If successful, keep it; if failed, try next
        // This is the GREEDY part: take first that fits
    }
    Ok(())
}
```

**Sorting Methods** (configured in `config.toml`):
- `max-profit`: Sort by coinbase profit (highest first)
- `mev-gas-price`: Sort by MEV gas price (highest first)
- Others: `base-fee-profit`, `max-profit-per-gas`, etc.

### Integration Points for LPU

You have **3 main options**:

#### Option A: Export → LPU Emulator → Import (CURRENT APPROACH)
**Best for initial testing**

```
rbuilder
    ↓ export JSON
knapsack_instance.json
    ↓ feed to LPU
LPU Emulator (GPU/CPU)
    ↓ output JSON
optimal_solution.json
    ↓ import & compare
rbuilder (comparison)
```

**Pros**:
- Clean separation
- Easy to iterate on LPU
- Can test offline
- Simple to compare results

**Cons**:
- Requires serialization
- Two-step process

#### Option B: Replace `fill_orders()` with LPU API Call
**Best for live integration**

Modify `ordering_builder.rs:fill_orders()`:
```rust
fn fill_orders_with_lpu<OrderPriorityType: OrderPriority>(
    &mut self,
    block_building_helper: &mut dyn BlockBuildingHelper,
    block_orders: &mut PrioritizedOrderStore<OrderPriorityType>,
    build_start: Instant,
    deadline: Option<Duration>,
) -> eyre::Result<()> {
    // 1. Convert block_orders to LPU format
    let knapsack_instance = convert_to_knapsack(block_orders);
    
    // 2. Call LPU emulator API
    let optimal_solution = call_lpu_api(
        knapsack_instance, 
        deadline.unwrap_or(Duration::from_secs(12))
    )?;
    
    // 3. Commit orders in optimal order
    for order_id in optimal_solution.selected_orders {
        let sim_order = block_orders.get(order_id)?;
        block_building_helper.commit_order(&mut self.local_ctx, &sim_order, ...)?;
    }
    
    Ok(())
}
```

**Pros**:
- Live integration
- Real-time comparison
- Production-ready path

**Cons**:
- More complex
- Tighter coupling
- Need robust API

#### Option C: New Builder Algorithm Type
**Best for side-by-side testing**

Create `crates/rbuilder/src/building/builders/lpu_builder.rs`:
```rust
pub fn run_lpu_builder<P>(
    input: LiveBuilderInput<P>,
    config: &LpuBuilderConfig,
) where P: StateProviderFactory + Clone + 'static {
    // Similar to ordering_builder but calls LPU instead
    let optimal_solution = lpu_emulator.solve(knapsack_instance, timeout)?;
    // Commit optimal solution...
}
```

Register in `config.toml`:
```toml
backtest_builders = ["greedy-mp-ordering", "lpu-knapsack"]

[[builders]]
name = "lpu-knapsack"
algo = "lpu-builder"
api_endpoint = "http://localhost:8080/solve"
timeout_ms = 10000
```

**Pros**:
- Clean comparison
- No modifications to existing code
- Easy A/B testing

**Cons**:
- More boilerplate
- Need to implement full builder interface

### Recommended Approach

**Phase 1 (Current)**: Use **Option A** (Export/Import)
- ✅ You already have knapsack exports
- Develop LPU emulator independently
- Get baseline comparison numbers

**Phase 2 (Next)**: Use **Option C** (New Builder Type)
- Once LPU emulator is stable
- Add it as a new builder algorithm
- Run side-by-side with greedy
- Use `backtest-build-block-no-sim` for fast iteration

**Phase 3 (Production)**: Use **Option B** (Replace fill_orders)
- Once LPU proves superior
- Integrate directly into ordering_builder
- Deploy to production

## 5. Is $3 per block realistic?

**YES, absolutely realistic!** Here's why:

### Block Profit Components
1. **Base fees** - Burned, not profit
2. **Priority fees** - Small tips (usually < 0.1 ETH)
3. **MEV** - Varies wildly (0 to 10+ ETH)

### Your Results
| Block | Profit (ETH) | USD @ $2,500 | Type |
|-------|--------------|--------------|------|
| 21200000 | 0.001208 | $3.02 | Low MEV |
| 21200001 | 0.002606 | $6.52 | Moderate MEV |
| 21200002 | 0.000365 | $0.91 | Very low |
| 21200003 | 0.000856 | $2.14 | Low |
| 21200004 | 0.000000 | $0.00 | No MEV |
| 21200005 | 0.000567 | $1.42 | Low |

### Reality Check
- **Most blocks**: $1-10 in profit
- **MEV-heavy blocks**: $100-1,000+ (rare)
- **Average**: ~$20-50 per block
- **High MEV days**: $100+ average (like during NFT mints, liquidations)

### Why This Matters for Your LPU
Even if you improve $3 → $4 (33% improvement):
```
Daily improvement: $1 * 7,200 blocks = $7,200/day
Yearly improvement: $7,200 * 365 = $2.6M/year
```

But the real value is in HIGH MEV blocks:
```
Improve $1,000 → $1,100 (10% improvement):
If this happens 100x/day = $10,000/day extra
Yearly: $3.65M/year
```

**The $3 blocks are normal. Focus on improving the high-value ones!**

## 6. Where are the Knapsack Instances?

**Location**: `/Users/matanfield/Projects/lightsolver/rbuilder/`

```bash
ls -lh /Users/matanfield/Projects/lightsolver/rbuilder/knapsack_instance_*.json
```

**Files**:
```
knapsack_instance_21200000.json  (331 KB, 2,005 items)
knapsack_instance_21200001.json  (340 KB, 2,057 items)
knapsack_instance_21200002.json  (333 KB, 2,017 items)
knapsack_instance_21200003.json  (330 KB, 1,999 items)
knapsack_instance_21200004.json  (330 KB, 1,995 items)
knapsack_instance_21200005.json  (339 KB, 2,050 items)
```

**Format**:
```json
{
  "block_number": 21200001,
  "items": [
    {
      "id": "tx:0x...",
      "profit": "0x...",      // hex wei
      "gas": 71000,
      "nonces": [
        ["0xaddress", nonce]  // conflict/dependency info
      ]
    },
    // ... 2000+ more
  ]
}
```

## 7. Export vs API Integration?

Both approaches are valid! Here's a decision framework:

### Use Export Approach When:
- ✅ **Developing/testing LPU emulator** (decoupled development)
- ✅ **Running experiments offline** (no need for running builder)
- ✅ **Comparing multiple algorithms** (save instances, test many solvers)
- ✅ **Benchmarking performance** (controlled, repeatable tests)
- ✅ **Academic research** (reproducible results)

**Workflow**:
```bash
# 1. Export instances
cargo run --release -p rbuilder --bin backtest-build-block-no-sim -- \
  --config config-mainnet-backtest.toml \
  --builders greedy-mp-ordering \
  21200001

# 2. Run LPU (separately)
./lpu_emulator knapsack_instance_21200001.json --output solution.json

# 3. Compare results
python compare_results.py solution.json greedy_results.json
```

### Use API Integration When:
- ✅ **LPU emulator is stable** (no longer changing rapidly)
- ✅ **Want live comparison** (side-by-side with greedy in same run)
- ✅ **Testing production readiness** (real-time performance)
- ✅ **Need realistic timing** (actual latency, network delays)
- ✅ **Building towards deployment** (production path)

**Workflow**:
```bash
# Start LPU API server
./lpu_emulator --serve --port 8080

# Run builder with LPU integration
cargo run --release -p rbuilder --bin backtest-build-block -- \
  --config config-with-lpu.toml \
  --builders greedy-mp-ordering \
  --builders lpu-knapsack \
  21200001
```

### Recommended Hybrid Approach

**Now (Phase 1)**: Export
- ✅ You already have exports
- Develop LPU independently
- Get baseline numbers

**Soon (Phase 2)**: API Integration
- Once LPU works well on exports
- Add API server to LPU
- Create new builder type in rbuilder
- Compare live

**Future (Phase 3)**: Native Integration
- If LPU proves superior
- Compile LPU as Rust library
- Direct integration (no network overhead)

## Summary Table

| Question | Short Answer |
|----------|-------------|
| Why ~2k txs? | Filtered available orders at block time, not full mempool |
| Pre-filtered? | YES - ready for knapsack, validated and deduplicated |
| Run knapsack on this? | YES - exact input for your optimization |
| Where's greedy? | `ordering_builder.rs:fill_orders()` - simple loop |
| How to replace? | Option A (export), B (API), or C (new builder type) |
| $3 realistic? | YES - most blocks are low MEV, focus on high-value ones |
| Where's JSON? | `rbuilder/knapsack_instance_*.json` (6 files) |
| Export vs API? | Export for dev, API for production testing |

## Next Steps

1. ✅ **DONE**: Export knapsack instances
2. **TODO**: Feed `knapsack_instance_21200001.json` to LPU emulator
3. **TODO**: Compare LPU solution profit vs greedy (0.002606 ETH)
4. **TODO**: If improvement > 5%, calculate ROI
5. **TODO**: If ROI positive, plan API integration
