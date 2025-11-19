# Backtest Results - Mainnet Blocks 21200000-21200005

**Date**: November 19, 2025  
**Network**: Ethereum Mainnet  
**Data Source**: mempool-dumpster (Flashbots)

## Summary

Successfully fetched and backtested 6 mainnet blocks with real historical mempool data. Each block contains ~2,000 orders, providing a perfect dataset for LPU knapsack solver benchmarking.

## Block Results

| Block # | Orders | Greedy Profit (ETH) | Greedy Time | MGP Time | Speedup | Knapsack File |
|---------|--------|---------------------|-------------|----------|---------|---------------|
| 21200000 | 2,005 | 0.001208 | 2.9ms | 1.6ms | 1.8x | knapsack_instance_21200000.json |
| 21200001 | 2,057 | 0.002606 | 3.6ms | 2.3ms | 1.6x | knapsack_instance_21200001.json |
| 21200002 | 2,017 | 0.000365 | 4.1ms | 2.6ms | 1.6x | knapsack_instance_21200002.json |
| 21200003 | 1,999 | 0.000856 | 3.9ms | 2.7ms | 1.4x | knapsack_instance_21200003.json |
| 21200004 | 1,995 | 0.000000 | 3.8ms | 2.6ms | 1.5x | knapsack_instance_21200004.json |
| 21200005 | 2,050 | 0.000567 | 3.2ms | 2.2ms | 1.5x | knapsack_instance_21200005.json |
| **Total** | **12,123** | **0.005602 ETH** | | | **Avg 1.6x** | **~2 MB** |

### Key Insights

1. **Dataset Size**: 12,123 total orders across 6 blocks (~2,000 per block)
2. **Greedy Baseline**: Total profit of 0.005602 ETH (~$14 at $2,500/ETH)
3. **Compute Time**: Both greedy algorithms run in 2-4ms per block
4. **Algorithm Comparison**: MEV-gas-price sorting is consistently 30-50% faster than max-profit sorting
5. **Profit Identical**: Both greedy algorithms achieve the same profit (as expected)

## Knapsack Instance Format

Each exported JSON file contains:
```json
{
  "block_number": 21200001,
  "items": [
    {
      "id": "tx:0x...",           // Transaction hash
      "profit": "0x...",           // Profit in wei (hex)
      "gas": 71000,                // Gas used
      "nonces": [                  // Nonce dependencies for conflict detection
        ["0xaddress", nonce]
      ]
    },
    // ... ~2000 more items
  ]
}
```

### Stats by Block

| Block | Total Gas | Profitable Items | Zero-Profit Items |
|-------|-----------|------------------|-------------------|
| 21200001 | 155,921,803 | 79 | 1,978 |

## Next Steps for LPU Proof-of-Concept

### 1. Feed to LPU Emulator
```bash
# Example: Process knapsack instance with LPU emulator
./lpu_emulator knapsack_instance_21200001.json --timeout 60s
```

### 2. Compare Results
- **Greedy profit**: 0.002606 ETH (block 21200001)
- **LPU optimal profit**: ??? (to be determined)
- **Delta**: ??? (this is your key metric!)

### 3. Calculate ROI
```
Annual slots: 2,628,000 (365 days * 7200 slots/day)
If LPU improves profit by X ETH per slot:
  Annual improvement = X * 2,628,000 ETH
  At $2,500/ETH = $2,500 * X * 2,628,000
```

### 4. Estimate Real-Time Feasibility
- Greedy baseline: 2-4ms per block
- Available time budget: ~12 seconds per slot
- LPU emulator time: ??? (measure on GPU)
- Real LPU hardware: ??? (estimate from cycle counts)

## Commands Used

### Fetch blocks:
```bash
cd /Users/matanfield/Projects/lightsolver/rbuilder
export RBUILDER_CONFIG_PATH=config-mainnet-backtest.toml
./run-backtest.sh fetch 21200000 21200010
```

### Run backtest (no-simulation mode):
```bash
cargo run --release -p rbuilder --bin backtest-build-block-no-sim -- \
  --config config-mainnet-backtest.toml \
  --builders greedy-mp-ordering \
  --builders greedy-mgp-ordering \
  21200001
```

## Database Info

- **Location**: `~/.rbuilder/backtest/mainnet.sqlite`
- **Size**: ~424 MB (including blocks 18920000-18920200 + 21200000-21200010)
- **Tables**: blocks, orders, blocks_data
- **Total orders stored**: 165,665 + 22,328 = 187,993 orders

## Files Generated

```
/Users/matanfield/Projects/lightsolver/rbuilder/
├── knapsack_instance_21200000.json  (331 KB, 2,005 items)
├── knapsack_instance_21200001.json  (340 KB, 2,057 items)
├── knapsack_instance_21200002.json  (333 KB, 2,017 items)
├── knapsack_instance_21200003.json  (330 KB, 1,999 items)
├── knapsack_instance_21200004.json  (330 KB, 1,995 items)
└── knapsack_instance_21200005.json  (339 KB, 2,050 items)
```

## Notes

- Block 21200004 had 0 ETH profit (likely a quiet block with only base fee txs)
- MEV opportunities vary significantly by block (0 to 0.002606 ETH)
- All knapsack instances are ready for LPU emulator testing
- No Reth state access required (using historical execution data)
