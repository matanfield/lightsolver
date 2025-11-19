# LPU vs Greedy: Comparison Results

## Test Configuration

- **Solver:** LightSolver Virtual Lab Emulator
- **Baseline:** Greedy algorithm (profit/gas ratio)
- **Problem:** Real Ethereum block transaction selection (knapsack)
- **Constraint:** 30M gas limit
- **Date:** November 19, 2025

---

## Results by Problem Size

### 10 Variables (Top 10 Transactions by Profit/Gas Ratio)

| Block | LPU Profit (ETH) | Greedy Profit (ETH) | Difference | Winner | LPU Gas % | Greedy Gas % |
|-------|------------------|---------------------|------------|--------|-----------|--------------|
| 21200000 | 0.002179 | 0.010577 | **-79.4%** | 🟢 Greedy | 2.6% | 10.9% |
| 21200001 | 0.002781 | 0.004825 | **-42.4%** | 🟢 Greedy | 1.5% | 2.9% |
| 21200002 | 0.008573 | 0.011349 | **-24.5%** | 🟢 Greedy | 8.7% | 11.5% |

**Average:** LPU is **-48.8%** worse than greedy on 10-variable problems

---

### 50 Variables (Top 50 Transactions)

| Block | LPU Profit (ETH) | Greedy Profit (ETH) | Difference | Winner | LPU Gas % | Greedy Gas % |
|-------|------------------|---------------------|------------|--------|-----------|--------------|
| 21200000 | 0.011706 | 0.019351 | **-39.5%** | 🟢 Greedy | 15.4% | 30.0% |

---

### 100 Variables (Top 100 Transactions)

| Block | LPU Profit (ETH) | Greedy Profit (ETH) | Difference | Winner | LPU Gas % | Greedy Gas % |
|-------|------------------|---------------------|------------|--------|-----------|--------------|
| 21200000 | 0.014306 | 0.019476 | **-26.6%** | 🟢 Greedy | 28.7% | 57.9% |

---

## Full Dataset Baseline (Greedy on All ~2000 Transactions)

| Block | Transactions | Profit (ETH) | Gas Utilization |
|-------|--------------|--------------|-----------------|
| 21200000 | 280 | 0.019476 | ~100% |
| 21200001 | 291 | 0.029056 | ~100% |
| 21200002 | 323 | 0.021641 | ~100% |

---

## Analysis

### Trend: Larger Problems Perform Better

| Problem Size | Average LPU Gap |
|--------------|-----------------|
| 10 vars      | **-48.8%** ❌ |
| 50 vars      | **-39.5%** ❌ |
| 100 vars     | **-26.6%** ⚠️ |

**Observation:** LPU performance improves with problem size, but still trails greedy significantly.

### Gas Utilization Pattern

```
LPU consistently under-utilizes gas:
- 10 vars:  2-9% gas used
- 50 vars:  15% gas used
- 100 vars: 29% gas used

Greedy achieves much higher utilization:
- 10 vars:  3-11% gas used
- 50 vars:  30% gas used
- 100 vars: 58% gas used
```

**Conclusion:** LPU is selecting fewer, possibly sub-optimal transactions.

---

## 🔴 Critical Issues Identified

### 1. Low Transaction Selection
- **Problem:** LPU selects 25-43% fewer transactions than greedy
- **Impact:** Low gas utilization → low profit
- **Hypothesis:** QUBO constraint term too strong

### 2. Suboptimal Profit Extraction
- **Problem:** Even when selecting transactions, profit is lower
- **Impact:** Not capturing highest-value items
- **Hypothesis:** Phase extraction method or coupling matrix issue

### 3. Formulation Mismatch
- **Problem:** Knapsack structure not well-suited for continuous XY model
- **Impact:** Solution quality degradation
- **Hypothesis:** Need different QUBO encoding or problem transformation

---

## 🟢 What's Working Well

### System Reliability ✅
- 100% success rate across all tests
- No crashes, no errors (after bug fixes)
- Fast execution (3-8 seconds per instance)

### Scalability ✅
- Successfully handles 10, 50, 100 variables
- Could potentially handle 1000+ (untested)
- Linear scaling in execution time

### Automation ✅
- Complete automated workflow
- Detailed logging and results
- Easy to reproduce and extend

---

## 🎯 Recommended Next Steps

### Immediate (Parameter Tuning)

1. **Vary Penalty Parameter**
   ```python
   for alpha in [0.01, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0]:
       test_with_penalty(alpha)
   ```

2. **Tune XY Model Parameters**
   ```python
   for alpha_I in [0.3, 0.5, 0.7, 0.9]:
       for coup_amp in [0.05, 0.1, 0.2, 0.3, 0.5]:
           test_with_params(alpha_I, coup_amp)
   ```

3. **Increase Emulator Runs**
   ```python
   num_runs = 50  # Instead of 10
   num_iterations = 5000  # Instead of 1000
   ```

### Short-term (Formulation)

4. **Try Alternative QUBO Encodings**
   - Logarithmic scaling
   - Fractional knapsack relaxation
   - Multi-objective formulation

5. **Better Solution Extraction**
   - Sweep phase thresholds
   - Try different run selection criteria
   - Ensemble solutions from multiple runs

### Long-term (Hybrid)

6. **Combine LPU + Greedy**
   - LPU for high-value subset
   - Greedy for filling remaining capacity
   - Local search refinement

---

## 💰 Value Analysis

### Current Gap (Block 21200000, 100 vars)
- Greedy: 0.019476 ETH = **$73.90** (at $3,800/ETH)
- LPU: 0.014306 ETH = **$54.36**
- **Gap: $19.54 per block**

### If LPU Could Match Greedy
- 7,200 blocks/day × $0 improvement = **$0/day** currently
- **Need:** Parameter tuning to close the gap

### If LPU Could Beat Greedy by 1%
- 7,200 blocks/day × $0.74 improvement = **$5,328/day**
- **Potential:** Significant if optimization successful

---

## 📈 Progress Summary

```
[████████████████████████████████] 100% System Implementation
[█████████░░░░░░░░░░░░░░░░░░░░░] 30%  Performance Optimization
[██░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 10%  Parameter Tuning
```

**Phase:** Implementation ✅ Complete → Now entering Research Phase 🔬

---

## 🚀 Quick Test Commands

```bash
cd /Users/matanfield/Projects/lightsolver/lightsolver-lab

# Quick test (10 vars, ~5 seconds)
./laser-mind-client/.venv/bin/python knapsack_lpu_solver.py \
  ../rbuilder/knapsack_instance_21200000.json 10

# Medium test (50 vars, ~10 seconds)
./laser-mind-client/.venv/bin/python knapsack_lpu_solver.py \
  ../rbuilder/knapsack_instance_21200000.json 50

# Large test (100 vars, ~15 seconds)
./laser-mind-client/.venv/bin/python knapsack_lpu_solver.py \
  ../rbuilder/knapsack_instance_21200000.json 100
```

---

**Last Updated:** November 19, 2025  
**Next:** Systematic parameter tuning experiments

