# High-Value Blocks Analysis - 23092808-23092812

**Date**: November 19, 2025  
**Network**: Ethereum Mainnet  
**Block Range**: 23092808-23092812 (August 8, 2025)

## Summary

Successfully fetched and exported 5 blocks with **~5,300 orders each** - 2.5x larger than previous dataset! These blocks are from a busier period, providing excellent test data for LPU scalability.

## Block Results

| Block # | Orders | File Size | Greedy Profit (ETH) | USD @ $2,500 | Compute Time | Profitable Items |
|---------|--------|-----------|---------------------|--------------|--------------|------------------|
| 23092808 | 5,290 | 875 KB | 0.000603 | $1.51 | 6.8ms | 128 |
| 23092809 | 5,306 | 878 KB | 0.000416 | $1.04 | 6.0ms | ~130 |
| 23092810 | 5,302 | 877 KB | 0.000007 | $0.02 | 32ms | ~5 |
| 23092811 | 5,272 | 871 KB | 0.000000 | $0.00 | 5.0ms | 0 |
| 23092812 | 5,366 | 889 KB | 0.000079 | $0.20 | 8.9ms | ~15 |
| **Total** | **26,536** | **4.3 MB** | **0.001105 ETH** | **$2.76** | | **~278** |

## Key Insights

### 1. Much Larger Dataset
- **2.5x more orders** per block (5,300 vs 2,000)
- **2.6x larger files** (875 KB vs 330 KB)
- **Total items**: 26,536 across 5 blocks
- **Perfect for testing LPU scalability** at 5k+ items

### 2. Lower MEV but Higher Complexity
Interestingly, these blocks have **lower profit** than previous blocks:
- Previous best (21200001): 0.002606 ETH ($6.52)
- New best (23092808): 0.000603 ETH ($1.51)

But they have **much more complexity**:
- More transactions to process
- Larger search space for optimization
- Better test of LPU performance at scale

### 3. Compute Time Still Fast
- Greedy handles 5,300 items in 5-32ms
- No significant slowdown despite 2.5x more items
- LPU has plenty of time budget (up to 10 seconds)

### 4. Profit Distribution
- Block 23092808: $1.51 (best, 128 profitable items)
- Block 23092809: $1.04 (moderate)
- Block 23092810: $0.02 (very low, only ~5 profitable)
- Block 23092811: $0.00 (no MEV)
- Block 23092812: $0.20 (low)

## Why These Blocks Are Valuable

### 1. Scalability Testing
With 5,300 items per block, these test your LPU at the **target scale** you mentioned (5k-10k items). If LPU can handle these efficiently, it proves feasibility.

### 2. Real-World Complexity
These aren't artificially high-MEV blocks - they're real mainnet blocks with:
- Normal transaction mix
- Real dependency constraints
- Actual gas constraints
- Realistic profit distribution

### 3. Comparison Baseline
Even with lower profits, if LPU finds **10% more** on block 23092808:
```
Greedy: 0.000603 ETH
LPU:    0.000663 ETH (10% better)
Delta:  0.000060 ETH per block

Annual improvement:
0.000060 ETH × 7,200 blocks/day × 365 days = 157 ETH/year
At $2,500/ETH = $393,000/year
```

## Files Generated

```
/Users/matanfield/Projects/lightsolver/rbuilder/
├── knapsack_instance_23092808.json  (875 KB, 5,290 items, $1.51 baseline)  ← BEST
├── knapsack_instance_23092809.json  (878 KB, 5,306 items, $1.04 baseline)
├── knapsack_instance_23092810.json  (877 KB, 5,302 items, $0.02 baseline)
├── knapsack_instance_23092811.json  (871 KB, 5,272 items, $0.00 baseline)
└── knapsack_instance_23092812.json  (889 KB, 5,366 items, $0.20 baseline)
```

## Complete Dataset Summary

You now have **11 knapsack instances** total:

### Small Scale (~2k items)
Blocks 21200000-21200005 (6 files, ~2 MB total)
- Best profit: 0.002606 ETH ($6.52)
- Orders: ~2,000 per block
- Good for: Initial testing, fast iteration

### Large Scale (~5k items)  
Blocks 23092808-23092812 (5 files, ~4.3 MB total)
- Best profit: 0.000603 ETH ($1.51)
- Orders: ~5,300 per block
- Good for: Scalability testing, production readiness

## Testing Strategy

### Phase 1: Quick Validation (Small Scale)
Test on `knapsack_instance_21200001.json` (2,057 items, $6.52 baseline)
- Fast to solve
- High baseline profit
- Easy to see improvement
- Quick iteration

### Phase 2: Scalability Test (Large Scale)
Test on `knapsack_instance_23092808.json` (5,290 items, $1.51 baseline)
- Realistic scale
- Tests LPU at target size
- Proves production feasibility
- If this works, you're ready!

### Phase 3: Full Comparison (All Blocks)
Test on all 11 blocks
- Get average improvement across different conditions
- Calculate realistic annual ROI
- Identify which block types benefit most

## Recommendations

### 1. Start Small
```bash
# Test on 2k-item block first
./your_lpu_emulator \
  --input knapsack_instance_21200001.json \
  --output solution_21200001.json \
  --timeout 5s
```

### 2. Then Scale Up
```bash
# Test on 5k-item block
./your_lpu_emulator \
  --input knapsack_instance_23092808.json \
  --output solution_23092808.json \
  --timeout 10s
```

### 3. Compare Both
- **Small block**: High profit, easy to beat greedy?
- **Large block**: Can LPU scale? Time < 10s?
- **Both good**: Strong case for production!

## Success Metrics

### Minimum Viable
- ✅ **Solves 2k items** in < 5 seconds
- ✅ **Solves 5k items** in < 10 seconds  
- ✅ **Finds 5-10% more profit** than greedy
- ✅ **Solution quality** > 95% optimal

### Production Ready
- ✅ **Solves 5k items** in < 5 seconds
- ✅ **Finds 10-20% more profit** than greedy
- ✅ **Solution quality** > 99% optimal
- ✅ **Consistent performance** across all block types

## Next Steps

1. ✅ **DONE**: Fetch and export high-value blocks
2. **TODO**: Test LPU on `knapsack_instance_21200001.json` (2k items)
3. **TODO**: Test LPU on `knapsack_instance_23092808.json` (5k items)
4. **TODO**: Compare timing and profit improvements
5. **TODO**: If both pass → Plan API integration

---

**Quick Commands**:

```bash
# Inspect large block
cat knapsack_instance_23092808.json | jq '{
  block_number,
  total_items: (.items | length),
  total_gas: (.items | map(.gas) | add),
  profitable_items: (.items | map(select(.profit != "0x0")) | length)
}'

# Compare file sizes
ls -lh knapsack_instance_*.json
```

**Key Takeaway**: You now have both **small-scale** (2k items, high MEV) and **large-scale** (5k items, realistic) test data. Perfect for proving LPU works at your target scale! 🚀
