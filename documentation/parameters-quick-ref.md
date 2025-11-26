# Parameters Quick Reference

## The Pipeline with Parameters

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. KNAPSACK → QUBO                                              │
│    Parameters: penalty (α)                                       │
│    Current: 4.65×10⁹ (TOO LARGE!)                              │
│    Should be: 10⁴ to 10⁶                                        │
│    Effect: Controls constraint vs objective balance             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. NORMALIZATION                                                 │
│    Parameters: normalize (True/False)                            │
│    Current: True                                                 │
│    Effect: Scales matrix to [-1,1], loses magnitude info        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. QUBO → ISING                                                  │
│    No parameters (automatic conversion)                          │
│    x ∈ {0,1} → s ∈ {-1,+1}                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. ISING → COUPLING MATRIX (XY Model)                           │
│    Parameters: alphaI, coupAmp                                   │
│    Current: alphaI=0.7, coupAmp=0.3 (defaults)                  │
│    Effect: Controls laser self-coupling and interactions        │
│    Constraint: Row sums must be < 1                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. LPU EMULATOR                                                  │
│    Parameters: num_runs, num_iterations, rounds_per_record      │
│    Previous: num_runs=10, num_iterations=1000 (TIMEOUT!)       │
│    Current: num_runs=5, num_iterations=500 (WORKS!)            │
│    Effect: More = better quality but slower                      │
│    Time: 8-10 seconds for n=75                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. SOLUTION EXTRACTION                                           │
│    Parameters: phase_threshold                                   │
│    Current: threshold=0 (simple cut)                            │
│    Better: Sweep thresholds, pick best profit                   │
│    Effect: Different thresholds → different solutions           │
└─────────────────────────────────────────────────────────────────┘
```

## Critical Parameters (Priority Order)

### 🔥 1. penalty (α) - HIGHEST PRIORITY
```
What: Constraint penalty strength
Where: QUBO formulation
Current: 4.65×10⁹
Problem: WAY TOO LARGE (forces conservative solutions)
Fix: Try 10⁴, 10⁵, 10⁶, 10⁷
Impact: Could improve profit by 50-100%
```

### 🔥 2. num_runs & num_iterations - FIXED!
```
What: Emulator sampling and convergence
Where: LPU emulator call
Previous: 10 runs × 1000 iter = TIMEOUT
Current: 5 runs × 500 iter = WORKS ✅
Impact: Made n=75 possible
```

### 🟡 3. normalize - HIGH PRIORITY
```
What: Scale QUBO to [-1,1]
Where: Before Ising conversion
Current: True
Problem: Loses 6 orders of magnitude of profit info
Test: Try False (may need to adjust XY params)
Impact: May help LPU distinguish high-value txs
```

### 🟡 4. alphaI & coupAmp - MEDIUM PRIORITY
```
What: XY model laser coupling parameters
Where: Coupling matrix creation
Current: 0.7 and 0.3 (defaults)
Problem: Not tuned for knapsack problems
Test: Grid search [0.3-0.9] × [0.1-0.5]
Impact: May improve solution quality 10-20%
```

### 🟢 5. phase_threshold - MEDIUM PRIORITY
```
What: Where to cut phases for binary solution
Where: Solution extraction
Current: 0 (simple)
Better: Sweep [-π, π], pick best
Impact: May find 5-10% better solutions from same run
```

## What Each Parameter Does

### penalty (α)
```python
# In QUBO formulation:
Energy = -profit + α × (gas - capacity)²
         ^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^
         Want high  Want zero

α too large  → Constraint dominates → Select fewer items
α too small  → Constraint ignored   → Violate gas limit
α just right → Balance both         → Optimal solution
```

### num_runs
```python
# Multiple independent simulations
num_runs = 1:  Fast, but may miss good solutions
num_runs = 5:  Good balance ✅
num_runs = 10: Better, but 2× slower (timeout)
num_runs = 50: Overkill, very slow
```

### num_iterations
```python
# Time steps for convergence
num_iterations = 100:  May not converge
num_iterations = 500:  Usually sufficient ✅
num_iterations = 1000: Safe, but 2× slower (timeout)
num_iterations = 5000: Overkill
```

### alphaI (self-coupling)
```python
alphaI < 0.3:  Lasers die (zero amplitude) ❌
alphaI = 0.5:  Weak self-coupling
alphaI = 0.7:  Default, balanced ✅
alphaI = 0.9:  Strong self-coupling
alphaI > 0.9:  Poor interaction between lasers ❌
```

### coupAmp (interaction strength)
```python
coupAmp = 0.05: Very weak interactions
coupAmp = 0.1:  Weak interactions
coupAmp = 0.3:  Default, moderate ✅
coupAmp = 0.5:  Strong interactions
coupAmp > 0.5:  May violate row sum constraint ❌
```

## Current Working Configuration

```python
# Problem size
n = 75  # All profitable transactions

# QUBO
penalty = base_alpha / 10000  # NEEDS TESTING!

# Normalization
normalize = True  # May not be optimal

# XY Model
alphaI = 0.7    # Default
coupAmp = 0.3   # Default

# Emulator
num_runs = 5           # ✅ Works
num_iterations = 500   # ✅ Works
rounds_per_record = 1

# Result
Time: 8-10 seconds
Status: Success ✅
```

## Testing Checklist

- [ ] Alpha sweep: Test 10³, 10⁴, 10⁵, 10⁶, 10⁷
- [ ] Normalization: Test True vs False
- [ ] XY parameters: Test alphaI [0.5, 0.7, 0.9] × coupAmp [0.1, 0.2, 0.3]
- [ ] Solution extraction: Implement threshold sweep
- [ ] Verify on n=75 (all profitable transactions)
- [ ] Compare with greedy baseline

## Expected Improvements

| Fix | Expected Improvement |
|-----|---------------------|
| Optimal α | 50-100% better profit |
| No normalization | 10-20% better discrimination |
| Tuned XY params | 5-15% better quality |
| Threshold sweep | 5-10% better extraction |
| **TOTAL** | **Could match or beat greedy!** |

---

**Next:** Run alpha parameter sweep with num_runs=5, num_iterations=500

