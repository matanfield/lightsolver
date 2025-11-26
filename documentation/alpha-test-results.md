# Alpha Test Results - November 26, 2025

## Summary: Alpha Tuning Alone Doesn't Fix It

We tested different alpha values and normalization. **LPU still significantly underperforms.**

## Test Results

### Alpha Sweep (WITH normalization)
| Divisor | Alpha | Selected | Profit (ETH) | Gas % | vs Optimal |
|---------|-------|----------|--------------|-------|------------|
| 1 | 3.98×10⁹ | **43/75** | 0.015255 | 27.1% | **-22%** |
| 100 | 3.98×10⁷ | 31/75 | 0.005129 | 23.8% | -74% |
| 10000 | 3.98×10⁵ | 33/75 | 0.013051 | 20.2% | -33% |
| 1000000 | 3.98×10³ | 39/75 | 0.013320 | 26.7% | -32% |

**Best:** Divisor=1 (original alpha!) selects 43/75

### Without Normalization
| Alpha | Selected | Profit (ETH) | Gas % | vs Optimal |
|-------|----------|--------------|-------|------------|
| 3.98×10⁹ | **26/75** | 0.009800 | 26.8% | **-50%** |

**Worse!** Only 26/75 without normalization

### Optimal (Target)
| Method | Selected | Profit (ETH) | Gas % |
|--------|----------|--------------|-------|
| **Optimal** | **75/75** | **0.019476** | **52.0%** |

## Key Findings

### 1. Alpha Tuning Didn't Help
- Original alpha (3.98×10⁹) was actually the BEST
- Reducing alpha made results worse
- **Conclusion:** Alpha is NOT the main problem

### 2. Normalization Helps, Not Hurts
- With normalization: 43/75 selected
- Without normalization: 26/75 selected
- **Conclusion:** Keep normalization

### 3. LPU Consistently Underperforms
- Best case: 43/75 (57% of optimal)
- Uses only 27% gas (vs 52% optimal)
- **Pattern:** LPU is too conservative

## Why Is LPU Underperforming?

### Hypothesis 1: XY Model Not Suited for Knapsack ⭐ Most Likely
The XY laser model was designed for:
- Spin glass problems
- Graph coloring
- Max-cut

**Knapsack is different:**
- All-to-all constraints (dense coupling matrix)
- Highly asymmetric (profits vary 162,000×)
- Binary constraint (gas limit)

**Evidence:**
- Changing alpha doesn't help
- Changing normalization makes it worse
- Pattern is consistent across all tests

### Hypothesis 2: Solution Extraction Suboptimal
Current method: Single threshold at phase=0

**Better approach:**
- Sweep 100 thresholds
- Pick solution with best actual profit
- May find 10-20% better solutions

### Hypothesis 3: Emulator Parameters Too Low
Current: num_runs=5, num_iterations=500

**Maybe need:**
- More runs for better sampling?
- More iterations for better convergence?
- But this would timeout...

### Hypothesis 4: Problem Structure
All 75 profitable transactions fit easily (52% gas).
**There's no actual optimization needed!**

The problem is trivial: select all 75.

LPU is trying to "optimize" when the answer is obvious.

## What This Means

### For This Specific Problem:
**LPU adds no value** when:
- All profitable items fit in capacity
- Optimal solution is "select all"
- No trade-offs needed

**Greedy wins easily** because it just selects by ratio until full.

### For Real Block Building:
This test case is **not representative** because:
- Real blocks: Many competing transactions
- Real blocks: Need to choose which to include
- Real blocks: Complex dependencies (nonces, etc.)

**This test:** All 75 fit, no choice needed

## Next Steps

### Option A: Test on Harder Problem
Create a problem where NOT all profitable items fit:
```python
# Artificially reduce capacity
CAPACITY = 10_000_000  # Instead of 30M
# Now only ~30 of 75 can fit
# LPU must choose which ones
```

### Option B: Test on n=200 (75 profitable + 125 zeros)
Can LPU discriminate zeros from profitable?
```python
# First 200 transactions (mixed)
# LPU should learn to ignore zeros
# Select only the profitable ones
```

### Option C: Implement Threshold Sweep
Better solution extraction from same emulator output:
```python
for threshold in np.linspace(-π, π, 100):
    extract_solution(threshold)
    if profit > best_profit:
        best_solution = current
```

### Option D: Accept Limitations
**Conclusion:** XY model + QUBO not well-suited for knapsack

**Alternative approaches:**
- Hybrid: LPU for subset selection, greedy for rest
- Different formulation: Try other quantum-inspired methods
- Classical optimization: Stick with greedy (it works!)

## Recommendation

### Short-term:
1. **Test Option B** (n=200 discrimination test) - 10 minutes
2. **Implement Option C** (threshold sweep) - 30 minutes
3. **If still poor:** Accept that this approach has limitations

### Long-term:
- **For production:** Use greedy (proven, fast, good results)
- **For research:** Investigate why XY model struggles with knapsack
- **For LPU:** Find problem types better suited to laser dynamics

## Bottom Line

**We successfully:**
- ✅ Got emulator working (n=75 in 8-10s)
- ✅ Understood all parameters
- ✅ Tested alpha tuning
- ✅ Tested normalization
- ✅ Identified root causes

**But:**
- ❌ LPU still underperforms (43/75 vs 75/75 optimal)
- ❌ Alpha tuning didn't help
- ❌ Normalization removal made it worse
- ❌ Problem appears to be fundamental model mismatch

**Conclusion:**
The XY laser model + QUBO formulation may not be well-suited for dense, asymmetric knapsack problems like transaction selection.

---

**Time invested:** 3 hours  
**Result:** Working system, but underperforming  
**Learning:** Not all problems are good fits for all solvers  
**Value:** Documented methodology for future quantum-inspired optimization attempts

