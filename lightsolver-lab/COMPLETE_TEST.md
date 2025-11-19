# Complete Test Plan - Addressing All Issues

## Issue You Just Identified 🎯

**We've been testing on greedy-filtered data!**

Current approach:
1. Sort 2005 txs by profit/gas ratio
2. Take top N
3. Compare LPU vs greedy on this subset

**Problem:** This is exactly what greedy would choose! We're testing LPU on greedy's preferred dataset.

**Impact:**
- FIRST 100 txs: 0.001 ETH (24.7% gas)
- TOP 100 by ratio: 0.019 ETH (57.9% gas)
- **19x difference!**

## What We Need To Do

### Test 1: Find Actual Emulator Limit ✅
- n=100: ✅ Works
- n=200: ✅ Works  
- n=500: ⏳ Testing
- n=1000: ❌ "Internal Service Exception"
- Binary search between 200-1000 to find exact limit

### Test 2: Alpha Sweep on Full Dataset
Use ALL available transactions (up to emulator limit), not greedy-filtered subset.

Test alpha values:
- Current: 4.65×10⁹ (way too large)
- Test: 10³, 10⁴, 10⁵, 10⁶, 10⁷

### Test 3: Fair Comparison
On full dataset (e.g., first 500 txs without sorting):
- LPU with optimal α
- Greedy algorithm
- See which actually performs better

## Alpha Test Results (n=100, first 100 txs)

| Divisor | Alpha | LPU Profit | Gas % | vs Greedy |
|---------|-------|------------|-------|-----------|
| 1 | 4.65×10⁹ | 0.001027 | 12.2% | +0.0% |
| 10 | 4.65×10⁸ | 0.000000 | 12.8% | -100% |
| 100 | 4.65×10⁷ | 0.000667 | 12.3% | -35% |
| 1000 | 4.65×10⁶ | 0.000360 | 12.4% | -65% |
| 10000 | 4.65×10⁵ | 0.000360 | 12.1% | -65% |
| 100000 | 4.65×10⁴ | 0.000667 | 13.0% | -35% |

**Observation:** Changing alpha didn't help much!

**This suggests:**
1. The problem is NOT just penalty parameter
2. Possibly normalization loses information
3. Or phase extraction method is flawed
4. Or the FIRST 100 txs are just low-value (most are 0 profit!)

## Next Steps

1. **Count zero-profit transactions**
2. **Test on full 500-1000 with proper alpha**
3. **Try WITHOUT normalization**
4. **Better solution extraction**

---

**Want me to run n=500 on FULL dataset (first 500 txs) right now?**

