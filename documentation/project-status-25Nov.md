# LightSolver LPU Project Status - November 25, 2025

## 🎯 Project Goal
Demonstrate that LightSolver's LPU emulator can outperform classical greedy algorithms for Ethereum block building (transaction selection knapsack problem).

## 📊 Current Status: FUNCTIONAL BUT UNDERPERFORMING

### What's Built ✅
- **Complete Pipeline**: Blockchain data → Knapsack → QUBO → Ising → Coupling Matrix → LPU Emulator → Solution
- **Working Scripts**:
  - `knapsack_lpu_solver.py` - Main solver with emulator integration
  - `alpha_parameter_sweep.py` - Systematic parameter testing
  - `batch_solve_knapsacks.py` - Batch processing
- **Real Data**: 11 knapsack instances from Ethereum mainnet blocks (21200000-21200005, 23092808-23092812)
- **Environment**: Python 3.12 with laser-mind-client, all dependencies working

### Current Performance 🔴
| Problem Size | LPU Profit | Greedy Profit | Gap | LPU Gas% | Greedy Gas% |
|--------------|-----------|---------------|-----|----------|-------------|
| n=10         | 0.002 ETH | 0.011 ETH     | **-79%** | 2.6%     | 10.9%       |
| n=50         | 0.012 ETH | 0.019 ETH     | **-40%** | 15.4%    | 30.0%       |
| n=100        | 0.014 ETH | 0.019 ETH     | **-27%** | 28.7%    | 57.9%       |
| n=200        | Not tested | -            | -        | -        | -           |

**Pattern**: LPU consistently underperforms greedy by 25-79%, uses ~50% less gas.

## 🔍 Root Causes Identified

### 1. Penalty Parameter α Too Large (PRIMARY SUSPECT)
```
Current:  α = 2 × (max_profit / max_gas) = 4.65×10⁹
Expected: α ≈ 10⁴ to 10⁶ (1000-10000× smaller!)
```

**Effect**: Constraint term dominates objective → LPU selects fewer transactions → Low gas utilization

**Evidence**: 
- At 80% gas: constraint penalty = 1.67×10²⁴, profit term = ~10¹⁵
- Penalty is **1 MILLION times** larger than profit!

### 2. Testing Methodology Bias
**Current approach**:
1. Sort transactions by profit/gas ratio (greedy's metric)
2. Take top N
3. Compare LPU vs greedy on this subset

**Problem**: Testing on greedy-optimal subsets! Of course greedy wins.

**Fix**: Test on unbiased subsets (e.g., all profitable transactions, or first N without sorting)

### 3. Data Reality: 96% Zero-Profit Transactions
- Total transactions: 2,005
- **Profitable: 75 (3.7%)**
- Zero profit: 1,930 (96.3%)
- All value concentrated in 75 transactions!

**Implication**: Testing on "first 100" includes ~96 zeros, only ~4 profitable. Both algorithms perform poorly.

### 4. Emulator Size Limit: ~200-300 Variables
**Tested**:
- n=100: ✅ Works (~8 seconds)
- n=200: ✅ Works (confirmed)
- n=500: ❌ "Internal Service Exception"
- n=1000: ❌ "Internal Service Exception"

**Expected per docs**: Should handle 1000-15000 variables

**Status**: Likely server-side limit or account restriction. Need to contact LightSolver.

### 5. Normalization May Lose Information
**Current**: `Q_normalized = Q / max(|Q|)`

**Problem**: 
- Original profits: 10¹⁸-10²⁴ wei (6 orders of magnitude variation)
- After normalization: All values 0-1
- May lose relative magnitude information critical for optimization

**Hypothesis**: LPU emulator may not handle extreme coupling matrix variations well (heard this before)

### 6. Simple Phase Extraction
**Current**: Single threshold at phase=0
```python
ising = np.where(phases >= 0, 1, -1)
```

**Better**: Sweep 100 thresholds, pick solution with best actual profit (not Ising energy)

## 📋 Immediate Action Plan

### Test 1: Alpha Parameter Sweep ⚡ HIGHEST PRIORITY
**Script**: `alpha_parameter_sweep.py` (already coded)

**Tests**:
- Problem sizes: n=100, 200, 300, 500, 1000, 1500, 2000
- Alpha divisors: 1, 10, 100, 1000, 10000, 100000
- Auto-stops at emulator limit

**Expected**: With α ≈ 10⁵, gas utilization should jump from 30% → 70-80%

**Status**: Ready to run

### Test 2: All 75 Profitable Transactions
**Question**: Do all 75 fit in one block, or is there still optimization needed?

**Check**: Sum gas costs of all 75 profitable transactions vs 30M limit

**Test**: Run LPU on exactly these 75 (no greedy pre-filtering)

**Expected**: Fair test of LPU's optimization capability

### Test 3: Push Emulator Limit
**Binary search**: 250, 275, 300 to find exact breaking point

**Goal**: Understand if 200-300 is hard limit or can be increased

### Test 4: Remove Normalization
**Hypothesis**: Normalization destroys magnitude information

**Test**: 
```python
# Current
Q_norm = Q / np.max(np.abs(Q))
I, offset = probmat_qubo_to_ising(Q_norm)

# Try
I, offset = probmat_qubo_to_ising(Q)  # No normalization
```

**Risk**: Coupling matrix may violate row sum constraint (Σ|coupling[i,:]| < 1)

**Mitigation**: Adjust XY model parameters (alphaI, coupAmp) if needed

### Test 5: Better Solution Extraction
**Current**: Single cut at phase=0

**Improved**: Threshold sweep
```python
best_solution = None
best_profit = 0

for threshold in np.linspace(-π, π, 100):
    ising = np.where(phases >= threshold, 1, -1)
    qubo = (ising + 1) / 2
    
    profit = sum(profits[i] * qubo[i] for i in range(n))
    gas = sum(gas_costs[i] * qubo[i] for i in range(n))
    
    if gas <= capacity and profit > best_profit:
        best_profit = profit
        best_solution = qubo
```

## 🔬 Technical Details

### QUBO Formulation
```
Knapsack: maximize Σ profit[i]×x[i] 
          subject to Σ gas[i]×x[i] ≤ 30,000,000

QUBO: minimize x^T Q x where:
  Q[i,i] = -profit[i] + α(gas[i]² - 2×capacity×gas[i])
  Q[i,j] = 2α×gas[i]×gas[j]  (i < j)
  offset = α × capacity²
```

### Workflow Pipeline
```
JSON → Parse → QUBO (n×n matrix) → Normalize → Ising → 
Coupling Matrix (XY model) → Emulator (10 runs, 1000 iterations) → 
Laser States → Phase Extraction → Binary Solution → Evaluation
```

### Time Breakdown (n=100)
- Local computation: ~350ms (10%)
  - QUBO construction: 291ms
  - Conversions: 59ms
- Network + Server: 2-6 seconds (90%)
  - API overhead, queue, emulator run

## 📁 Project Structure

```
lightsolver/
├── lightsolver-lab/           # LPU solver implementation
│   ├── knapsack_lpu_solver.py       # Main solver
│   ├── alpha_parameter_sweep.py     # Parameter testing
│   ├── batch_solve_knapsacks.py     # Batch processor
│   ├── laser-mind-client/           # LightSolver Python client
│   └── documentation/               # API specs
├── rbuilder/                  # Block builder (data source)
│   ├── knapsack_instance_*.json     # 11 real knapsack instances
│   └── crates/rbuilder/             # Rust implementation
└── documentation/             # Project docs
    ├── project.md                   # Original project plan
    └── project-status-25Nov.md      # This file
```

## 🎯 Success Criteria

### Minimum Viable Success
- LPU matches greedy performance (±5%) on 75 profitable transactions
- Demonstrates feasibility of LPU for blockchain optimization

### Strong Success
- LPU beats greedy by 5-10% on high-value transactions
- Scales to n=200-500 transactions
- Processing time < 10 seconds

### Exceptional Success
- LPU beats greedy by 10%+ consistently
- Scales to n=1000+
- Hybrid approach (LPU + greedy) shows clear ROI

## 🚀 Next Steps (Ordered)

1. **Run alpha parameter sweep** → Find optimal α
2. **Analyze 75 profitable transactions** → Check if they fit in one block
3. **Test n=200-300** → Find emulator limit
4. **Test without normalization** → See if magnitude preservation helps
5. **Implement threshold sweep** → Better solution extraction
6. **If still underperforming**: XY parameter tuning, alternative formulations

## 📞 Open Questions

1. **Why is emulator limited to ~200-300?** (Should handle 1000+ per docs)
2. **Does LPU handle extreme coupling variations?** (10⁶ orders of magnitude)
3. **Is normalization required or harmful?** (Preserves constraint but loses info)
4. **What's the optimal α formula for knapsack?** (Current formula clearly wrong)

## 💡 Lessons Learned

1. **Penalty parameters are critical** - Wrong α can make algorithm useless
2. **Testing methodology matters** - Greedy-biased subsets give misleading results
3. **Data characteristics matter** - 96% zeros changes the problem entirely
4. **Documentation ≠ Reality** - Emulator limits don't match documentation
5. **Formulation is everything** - QUBO encoding critically important

## 📊 Expected Outcomes After Tests

### If α fix works:
- Gas utilization: 30% → 70-80%
- Profit improvement: 27% deficit → competitive or better
- **Conclusion**: Problem was formulation, not LPU capability

### If α fix doesn't work:
- Need to investigate normalization, XY parameters, solution extraction
- May need alternative QUBO formulation
- Could be fundamental limitation of XY model for knapsack

### If emulator scales to n=500+:
- Can test on larger, more realistic subsets
- Better chance of beating greedy
- More practical for production use

---

**Status**: Ready to run systematic tests. Infrastructure complete, hypotheses clear, next steps defined.

**Timeline**: 1-2 hours of testing should answer all critical questions.

**Risk**: If all tests fail, may need to conclude that XY model + QUBO is not suitable for this problem type.

