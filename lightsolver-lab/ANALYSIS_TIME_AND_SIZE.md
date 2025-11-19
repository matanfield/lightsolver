# Analysis: Emulator Time & Size Constraints

## Key Discoveries

### 1. **Where Does the Time Go?** ⏱️

Based on timing breakdown for n=2005:

| Step | Time | Percentage |
|------|------|------------|
| Load JSON | 3 ms | <1% |
| Parse data | 0.4 ms | <1% |  
| **Build QUBO** | **291 ms** | **8%** |
| Normalize | 14 ms | <1% |
| QUBO → Ising | 10 ms | <1% |
| Ising → Coupling Matrix | 24 ms | <1% |
| Validate | 5 ms | <1% |
| **Total Local** | **~350 ms** | **10%** |
| **API Connection** | **1000 ms** | **28%** |
| **Emulator Solve (server)** | **~2000-6000 ms** | **55-85%** |
| Extract solution | ~10 ms | <1% |

**ANSWER:** The 3-8 seconds is:
- **10% local computation** (mostly QUBO matrix construction O(n²))
- **90% network + server processing** (API calls, queueing, emulator running)

### 2. **Why Not Milliseconds for n~100?** 🤔

The **emulator computation itself** might be fast (milliseconds), but we're seeing:
1. **Network latency:** API round trips
2. **Queue waiting:** "request done waiting in queue, now processing"  
3. **Data transfer:** 30MB matrix upload/download
4. **Server overhead:** Job scheduling, result packaging

For n=100:
- Matrix: 100×100 = 0.08 MB
- Server processing: ~2-3 seconds (includes queue + compute)

For n=2005:
- Matrix: 2005×2005 = 30.7 MB
- Server processing: 30+ seconds before crashing

### 3. **Emulator Size Limit** 📏

**Test Results:**
- n=10: ✅ Works (~5 seconds)
- n=50: ✅ Works (~6 seconds)  
- n=100: ✅ Works (~8 seconds)
- n=500: ❓ Need to test
- n=1000: ❓ Need to test
- n=2005: ❌ "Internal Service Exception"

**Hypothesis:** There IS a server-side limit, but it's:
- NOT documented
- NOT a hard API limit (no error message about size)
- Appears as "Internal Service Exception" (server crashes)

### 4. **Coupling Matrix Constraint** ⚖️

The XY model requires: **Σ|coupling[i,:]| < 1** for all rows

**Our Results at n=2005:**
- Max row sum: **0.7972**
- Constraint: **SATISFIED** ✅

So the coupling matrix is valid! The server error is NOT due to constraint violation.

### 5. **Why Underperforming Greedy?** 🔍

Several possible reasons:

#### A. **We Were Testing on Limited Subsets**
- n=10, 50, 100 out of 2005 transactions
- Pre-filtered by greedy's own metric (profit/gas ratio!)
- Then comparing LPU vs greedy on this **greedy-biased subset**
- **Circular logic:** Of course greedy wins on data selected by greedy!

#### B. **QUBO Formulation Issues**
Current formulation might not capture the problem well:

```python
# Current penalty
penalty = 2 × (max_profit / max_gas)

# Issues:
# 1. Might be too high/low
# 2. Doesn't account for problem structure
# 3. Linear penalty might not be optimal
```

#### C. **Solution Extraction Method**
Simple phase thresholding might be suboptimal:

```python
# Current method
ising = np.where(phases >= 0, 1, -1)

# Better method might:
# - Try multiple thresholds
# - Use proper cut optimization  
# - Ensemble multiple runs
```

#### D. **XY Model Parameters**
Using defaults:
```python
XYModelParams(alphaI=0.7, coupAmp=0.3)

# Should tune:
# - alphaI: self-coupling strength
# - coupAmp: coupling amplitude
# Documentation says these should be optimized per problem!
```

#### E. **Emulator Parameters**
Current:
```python
num_runs=10,
num_iterations=1000
```

Maybe need:
```python
num_runs=50,  # More sampling
num_iterations=5000  # More convergence time
```

### 6. **Low Gas Utilization Problem** ⛽

**Observation:**
- LPU selects 25-43% fewer transactions than greedy
- Results in low gas utilization (3-29% vs 11-58%)

**Root Cause Hypotheses:**

1. **Penalty Too Strong**
   - Constraint term dominates objective
   - Solver avoids adding transactions to stay safe from constraint
   - Solution: Lower penalty parameter

2. **Wrong Optimization Direction**
   - Normalized QUBO loses magnitude information
   - Solver can't distinguish high-value from low-value items
   - Solution: Better normalization or scaling

3. **Phase Extraction Bias**
   - Simple threshold might prefer "all off" solutions
   - Need to verify final laser states
   - Solution: Multiple threshold sweeps

### 7. **Parameters to Tune** 🎛️

| Parameter | Current | Purpose | Tuning Range |
|-----------|---------|---------|--------------|
| **penalty (α)** | `2×max_profit/max_gas` | Constraint strength | 0.1 - 100 |
| **alphaI** | 0.7 | Self-coupling | 0.3 - 0.9 |
| **coupAmp** | 0.3 | Coupling amplitude | 0.05 - 0.5 |
| **num_runs** | 10 | Number of runs | 5 - 100 |
| **num_iterations** | 1000 | Convergence time | 500 - 10000 |
| **normalization** | Divide by max | Value scaling | Various methods |

## Next Steps

### Immediate

1. ✅ **Find actual emulator limit**
   - Binary search between n=100 (works) and n=2005 (fails)
   - Test: 200, 500, 1000, 1500

2. ✅ **Fix the artificial constraint**
   - Remove `max_lpu_variables` filtering
   - Use full dataset or largest that works

3. ✅ **Time breakdown with full dataset**
   - Measure each step precisely
   - Identify bottlenecks

### Short-term

4. **Parameter sweep for penalty (α)**
   ```python
   for alpha in [0.1, 0.5, 1, 2, 5, 10, 20, 50, 100]:
       test_and_record_results(alpha)
   ```

5. **XY model parameter tuning**
   ```python
   for alphaI in [0.3, 0.5, 0.7, 0.9]:
       for coupAmp in [0.1, 0.2, 0.3, 0.5]:
           test_and_record_results(alphaI, coupAmp)
   ```

6. **Better solution extraction**
   - Sweep phase thresholds: `np.linspace(-π, π, 100)`
   - Try different cut optimization methods
   - Ensemble across multiple runs

### Long-term

7. **Alternative QUBO formulations**
8. **Hybrid LPU + Greedy**
9. **Problem-specific coupling matrix design**

## Critical Questions to Answer

1. **What is the actual emulator size limit?**
   - Test systematically: 100, 200, 500, 1000, 1500, 2000, 2005
   
2. **Is there a coupling matrix sparsity requirement?**
   - Our knapsack creates DENSE matrices (all-to-all constraints)
   - Maybe emulator prefers SPARSE problems?
   
3. **Does normalization lose critical information?**
   - Original profits: 10^18 - 10^24 wei (6 orders of magnitude!)
   - After normalization: all values 0-1
   - Maybe relative magnitudes matter?

4. **What do the laser dynamics actually converge to?**
   - Are they finding stable states?
   - Or dying out (all zero amplitude)?
   - Check `final_gains` from results

5. **Is knapsack well-suited for XY model?**
   - XY model designed for spin glass
   - Knapsack is combinatorial optimization
   - Maybe need different Hamiltonian mapping?

---

**Bottom Line:** The 10-100 variable "limit" was MY MISTAKE. The emulator should handle more, but we need to find the actual limit and understand why it's not milliseconds.

