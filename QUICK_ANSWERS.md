# Quick Answers to Your Questions

## 1. Why ~2,000 txs instead of ~150k?
**Short**: Time window filter (3 min before block)  
**Long**: See `BACKTEST_FAQ.md` section 1

The ~2,000 is NOT the full mempool. It's transactions available in a 3-minute window before the block, filtered for:
- Valid format
- On-time arrival
- No duplicates
- Non-redundant bundles

This is **realistic** - builders don't process 150k txs, they process what's available when they start building.

## 2. Is this pre-filtered?
**YES** - This is the clean, validated list ready for knapsack.

## 3. Is this what we run knapsack on?
**YES** - The exported JSON files are the exact knapsack inputs.

## 4. Where's the greedy code?
**File**: `rbuilder/crates/rbuilder/src/building/builders/ordering_builder.rs`  
**Function**: `fill_orders()` (line 396-476)

**The loop**:
```rust
while let Some(sim_order) = block_orders.pop_order() {
    block_building_helper.commit_order(&mut self.local_ctx, &sim_order, ...)?;
}
```

**How to replace**:
- **Now**: Use exported JSON → LPU → compare results (Option A)
- **Later**: API integration (Option B) or new builder type (Option C)
- **See**: `LPU_INTEGRATION_GUIDE.md` for detailed options

## 5. Is $3 per block realistic?
**YES!** Most blocks have low MEV:
- Your blocks: $0 to $6.52
- Average blocks: $1-10  
- MEV-heavy blocks: $100-1,000+ (rare, but this is where LPU wins!)

Even 33% improvement on low blocks ($3→$4) = **$2.6M/year**

## 6. Where are the knapsack instances?
**Location**: `/Users/matanfield/Projects/lightsolver/rbuilder/`

```bash
ls -lh rbuilder/knapsack_instance_*.json
```

**6 files**, each ~330KB with ~2,000 items:
- `knapsack_instance_21200000.json`
- `knapsack_instance_21200001.json` ← BEST (0.002606 ETH profit)
- `knapsack_instance_21200002.json`
- `knapsack_instance_21200003.json`
- `knapsack_instance_21200004.json`
- `knapsack_instance_21200005.json`

## 7. Export vs API integration?
**Both valid!**

**Export (NOW)**: 
- ✅ Already done
- ✅ Easy to test LPU independently
- ✅ No rbuilder changes needed
- Use this to get first results

**API (LATER)**:
- ✅ Live comparison
- ✅ Production-ready
- ✅ Real-time performance
- Use this once LPU is proven

**Recommendation**: Start with exports, move to API once you have positive ROI numbers.

---

## Your Next Steps

1. **Feed to LPU**: `knapsack_instance_21200001.json` → your emulator
2. **Compare**: Greedy 0.002606 ETH vs LPU ??? ETH
3. **Calculate ROI**: Use formula in `LPU_INTEGRATION_GUIDE.md`
4. **If > 5% improvement**: Plan API integration

## Key Files to Read

1. **BACKTEST_FAQ.md** - Detailed answers to all your questions
2. **LPU_INTEGRATION_GUIDE.md** - How to integrate LPU
3. **BACKTEST_RESULTS.md** - Performance summary of 6 blocks
4. **knapsack_instance_*.json** - Your input data (6 files)

## Test Command

```bash
# Verify your LPU can read the format
cat rbuilder/knapsack_instance_21200001.json | jq '{
  block: .block_number,
  items: (.items | length),
  sample: .items[0]
}'
```

Expected output:
```json
{
  "block": 21200001,
  "items": 2057,
  "sample": {
    "id": "tx:0x...",
    "profit": "0x0",
    "gas": 71000,
    "nonces": [["0x...", 84]]
  }
}
```

---

**TL;DR**: You have 6 real knapsack instances (~2k items each) exported. Feed them to your LPU emulator, compare profit vs greedy baseline (0.002606 ETH for best block), calculate ROI. If > 5% improvement, we integrate via API.
