# Complete Parameters Guide - LightSolver LPU Lab

## Overview: The Pipeline

```
Knapsack Problem
    ↓ [QUBO Parameters]
QUBO Matrix
    ↓ [Normalization]
Normalized QUBO
    ↓ [Ising Conversion]
Ising Matrix
    ↓ [XY Model Parameters]
Coupling Matrix
    ↓ [Emulator Parameters]
LPU Emulator Results
    ↓ [Extraction Parameters]
Binary Solution
```

---

## 1. QUBO Formulation Parameters

### `penalty` (α - Alpha)
**What it controls:** Strength of the constraint penalty term

**Formula:**
```python
QUBO = -Σ profit[i]×x[i] + α(Σ gas[i]×x[i] - capacity)²
       ^^^^^^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
       Objective term     Constraint penalty term
```

**Purpose:** Balance between:
- Maximizing profit (objective)
- Satisfying gas constraint (penalty)

**Values:**
- **Current (wrong):** `α = 2 × (max_profit / max_gas) = 4.65×10⁹`
- **Should be:** `α ≈ 10⁴ to 10⁶` (1000-10000× smaller!)

**Effect:**
- **Too large:** Constraint dominates → LPU selects fewer items → Low profit
- **Too small:** Constraint ignored → LPU violates gas limit
- **Just right:** Balances profit and constraint

**Where used:** `knapsack_to_qubo()` function
```python
Q[i, i] = -profits[i] + penalty * (gas_costs[i]**2 - 2*capacity*gas_costs[i])
Q[i, j] = 2 * penalty * gas_costs[i] * gas_costs[j]
```

**Test range:**
```python
base_alpha = 2 * (max_profit / max_gas)
for divisor in [1, 10, 100, 1000, 10000, 100000, 1000000]:
    alpha = base_alpha / divisor
```

---

## 2. Normalization Parameters

### `normalize` (Boolean)
**What it controls:** Whether to scale QUBO matrix to [-1, 1] range

**Current:**
```python
Q_max = np.max(np.abs(Q))
Q_normalized = Q / Q_max
```

**Purpose:** 
- Ensure coupling matrix satisfies constraint: `Σ|coupling[i,:]| < 1`
- Prevent numerical overflow/underflow

**Values:**
- `True` (default): Normalize
- `False`: Use raw QUBO values

**Effect:**
- **With normalization:** Loses relative magnitude information
- **Without normalization:** May violate coupling constraint

**Where used:** Before `probmat_qubo_to_ising()`

**Trade-off:**
```
Normalize = True:
  ✅ Coupling matrix always valid
  ❌ Loses 6 orders of magnitude of profit information

Normalize = False:
  ✅ Preserves relative profit magnitudes
  ❌ May create invalid coupling matrix
```

---

## 3. XY Model Parameters

These control how the Ising problem maps to the laser coupling matrix.

### `alphaI` (Self-coupling strength)
**What it controls:** How strongly each laser couples to itself

**Default:** `0.7`

**Range:** `0.0` to `1.0`

**Effect:**
- **Too small (<0.3):** Lasers "die" (zero amplitude)
- **Too large (>0.9):** Poor coupling between spins
- **Optimal:** Problem-dependent, usually `0.5-0.8`

**Where used:** `XYModelParams(alphaI=0.7)`

### `coupAmp` (Coupling amplitude)
**What it controls:** Strength of interaction between lasers

**Default:** `0.3`

**Range:** `0.0` to `1.0` (but must satisfy row sum constraint)

**Effect:**
- **Too small:** Weak interactions, poor optimization
- **Too large:** May violate coupling constraint
- **Optimal:** Problem-dependent, usually `0.1-0.5`

**Where used:** `XYModelParams(coupAmp=0.3)`

**Constraint:**
```python
# Must satisfy for all rows i:
Σ|coupling_matrix[i, :]| < 1

# Typically:
alphaI + (n-1) × coupAmp / n < 1
```

**Documentation says:** "Should be optimized per problem"

**Test range:**
```python
for alphaI in [0.3, 0.5, 0.7, 0.9]:
    for coupAmp in [0.05, 0.1, 0.2, 0.3, 0.5]:
        # Test combination
```

---

## 4. Emulator Parameters

These control the actual simulation on LightSolver's servers.

### `num_runs` 
**What it controls:** Number of independent simulation runs

**Purpose:** Sample different initial conditions to find best solution

**Default:** `10`

**Range:** `1` to `100+` (limited by time/cost)

**Effect:**
- **More runs:** Better sampling, more robust, slower
- **Fewer runs:** Faster, but may miss good solutions

**Where used:** `solve_coupling_matrix_sim_lpu(num_runs=...)`

**Current findings:**
- `num_runs=10` → Timeout (60+ seconds)
- `num_runs=5` → Works (8-10 seconds) ✅
- `num_runs=1` → Untested (probably too few)

**Trade-off:**
```
num_runs=10:  Better quality, but 2× slower
num_runs=5:   Good quality, fits in timeout ✅
num_runs=1:   Fast, but poor quality
```

### `num_iterations`
**What it controls:** Number of time steps in each simulation run

**Purpose:** Allow system to converge to stable state

**Default:** `1000`

**Range:** `100` to `10000+`

**Effect:**
- **More iterations:** Better convergence, slower
- **Fewer iterations:** Faster, but may not converge

**Where used:** `solve_coupling_matrix_sim_lpu(num_iterations=...)`

**Current findings:**
- `num_iterations=1000` → Timeout
- `num_iterations=500` → Works ✅
- `num_iterations=100` → Untested (may not converge)

**Convergence:**
```
iterations=100:   May not reach steady state
iterations=500:   Usually sufficient ✅
iterations=1000:  Safe, but slower
iterations=5000:  Overkill for most problems
```

### `rounds_per_record`
**What it controls:** How often to record laser states during simulation

**Purpose:** For visualization and analysis of dynamics

**Default:** `1` (record every iteration)

**Range:** `1` to `num_iterations`

**Effect:**
- `1`: Record every iteration (full time series)
- `10`: Record every 10th iteration (less data)
- `num_iterations`: Record only final state

**Where used:** `solve_coupling_matrix_sim_lpu(rounds_per_record=...)`

**Current:** We use `1` to get full dynamics, but only use final state

**Optimization:**
```python
# If only need final state:
rounds_per_record = num_iterations  # Faster, less data transfer

# If need dynamics:
rounds_per_record = 1  # Full time series
```

### `timeout`
**What it controls:** Maximum allowed solver time (seconds)

**Purpose:** Prevent hanging on difficult problems

**Default:** No explicit timeout in API (server-side limit ~60s)

**Range:** `10` to `300` seconds

**Effect:**
- **Too short:** May timeout on valid problems
- **Too long:** Wastes time on impossible problems

**Where used:** Not directly in API, but we add client-side timeout

**Current findings:**
- Server timeout: ~60 seconds
- Our client timeout: 30-60 seconds
- Actual solve time: 8-10 seconds for n=75 ✅

### `initial_states_seed`
**What it controls:** Random seed for initial laser states

**Purpose:** Reproducibility or exploration

**Default:** `-1` (random)

**Range:** `-1` (random) or any positive integer

**Effect:**
- `-1`: Different initial states each run (exploration)
- `Fixed seed`: Same initial states (reproducibility)

**Where used:** `solve_coupling_matrix_sim_lpu(initial_states_seed=...)`

**Current:** We use default `-1` for exploration

### `initial_states_vector`
**What it controls:** Explicit initial laser states (advanced)

**Purpose:** Warm start from known good state

**Default:** `None` (generate randomly)

**Type:** `numpy.ndarray`, shape `[num_runs, num_lasers]`, dtype `complex64`

**Where used:** `solve_coupling_matrix_sim_lpu(initial_states_vector=...)`

**Current:** We don't use this (let emulator choose)

---

## 5. Gain Parameters (Advanced)

These control laser gain dynamics (usually keep defaults).

### `gain_info_initial_gain`
**What it controls:** Starting gain for each laser

**Default:** Has a default (not documented)

**Where used:** `solve_coupling_matrix_sim_lpu(gain_info_initial_gain=...)`

**Current:** We use defaults

### Other gain parameters:
- `gain_info_pump_max`
- `gain_info_pump_tau`
- `gain_info_pump_threshold`
- `gain_info_amplification_saturation`

**Recommendation:** Don't touch these unless you understand laser physics!

---

## 6. Solution Extraction Parameters

### `phase_threshold`
**What it controls:** Where to cut phases to extract binary solution

**Current:**
```python
phases = np.angle(final_state)  # Range: [-π, π]
ising = np.where(phases >= 0, 1, -1)  # Threshold at 0
```

**Purpose:** Convert continuous phases to binary {-1, +1}

**Range:** `-π` to `π`

**Effect:**
- Different thresholds → Different solutions
- Optimal threshold → Best profit

**Where used:** After getting `final_states` from emulator

**Better approach:**
```python
best_solution = None
best_profit = 0

for threshold in np.linspace(-π, π, 100):
    ising = np.where(phases >= threshold, 1, -1)
    qubo = (ising + 1) / 2
    
    profit = calculate_profit(qubo)
    gas = calculate_gas(qubo)
    
    if gas <= capacity and profit > best_profit:
        best_profit = profit
        best_solution = qubo
```

---

## Summary Table

| Parameter | Current | Works | Optimal | Priority |
|-----------|---------|-------|---------|----------|
| **penalty (α)** | 4.65×10⁹ | ? | 10⁴-10⁶ | 🔥 HIGHEST |
| **normalize** | True | ✅ | ? | 🔥 HIGH |
| **alphaI** | 0.7 | ✅ | 0.5-0.8 | 🟡 MEDIUM |
| **coupAmp** | 0.3 | ✅ | 0.1-0.5 | 🟡 MEDIUM |
| **num_runs** | 10 → 5 | ✅ | 5-10 | ✅ FIXED |
| **num_iterations** | 1000 → 500 | ✅ | 500-1000 | ✅ FIXED |
| **rounds_per_record** | 1 | ✅ | 1 or n_iter | 🟢 LOW |
| **phase_threshold** | 0 | ✅ | sweep | 🟡 MEDIUM |

---

## Recommended Testing Order

### 1. Alpha Parameter Sweep (PRIORITY 1)
```python
base_alpha = 2 * (max_profit / max_gas)
for divisor in [1, 100, 10000, 1000000]:
    alpha = base_alpha / divisor
    test_with_emulator(
        penalty=alpha,
        num_runs=5,
        num_iterations=500
    )
```

**Expected:** With α ≈ 10⁵, LPU should select all 75 profitable txs

### 2. Normalization Test (PRIORITY 2)
```python
for normalize in [True, False]:
    test_with_emulator(
        penalty=optimal_alpha,
        normalize=normalize,
        num_runs=5,
        num_iterations=500
    )
```

**Expected:** May help preserve profit magnitudes

### 3. XY Parameters (PRIORITY 3)
```python
for alphaI in [0.5, 0.7, 0.9]:
    for coupAmp in [0.1, 0.2, 0.3]:
        test_with_emulator(
            penalty=optimal_alpha,
            alphaI=alphaI,
            coupAmp=coupAmp,
            num_runs=5,
            num_iterations=500
        )
```

**Expected:** May improve solution quality

### 4. Solution Extraction (PRIORITY 4)
```python
# After getting results, try multiple thresholds
for threshold in np.linspace(-π, π, 100):
    extract_solution(threshold)
    evaluate_profit()
```

**Expected:** May find better solutions from same emulator output

---

## What We Know Works (n=75)

```python
# QUBO
penalty = base_alpha / 10000  # Need to test more values

# Normalization
normalize = True  # Works, but may not be optimal

# XY Model
alphaI = 0.7      # Default, works
coupAmp = 0.3     # Default, works

# Emulator
num_runs = 5           # ✅ Works (10 times out)
num_iterations = 500   # ✅ Works (1000 times out)
rounds_per_record = 1  # Works

# Result: 8-10 seconds, successful completion
```

---

## Quick Reference

**To make LPU faster:**
- ↓ Reduce `num_runs` (5 instead of 10)
- ↓ Reduce `num_iterations` (500 instead of 1000)
- ↑ Increase `rounds_per_record` (only if don't need dynamics)

**To improve solution quality:**
- ↑ Increase `num_runs` (more sampling)
- ↑ Increase `num_iterations` (better convergence)
- 🔧 Tune `penalty` (α)
- 🔧 Tune `alphaI` and `coupAmp`
- 🔍 Sweep `phase_threshold`

**To debug problems:**
- Check coupling matrix validity (row sums < 1)
- Try different `penalty` values
- Reduce problem size
- Check for numerical issues (NaN, inf)

---

**Next step:** Run alpha parameter sweep with working configuration (num_runs=5, num_iterations=500) to find optimal penalty!

