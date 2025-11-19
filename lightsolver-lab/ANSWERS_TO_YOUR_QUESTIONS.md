# Answers to Your Critical Questions

## Q1: Where Does the 10-100 Variable Constraint Come From?

### Answer: **IT WAS MY MISTAKE!** ❌

**What I Did Wrong:**
- Confused physical LPU limit (5-100 vars, `dlpu_spin_limit`) with emulator limit
- Artificially limited the solver to 10-100 variables
- Your account shows `dlpu_spin_limit: 0` = no physical LPU access, emulator only

**Actual Limits:**
- **Physical LPU:** 5-100 variables (hardware constraint, not available to you)
- **Emulator (SIM LPU):** Should handle **1000-15000** variables according to your knowledge
- **Tested so far:**
  - n=10: ✅ Works
  - n=50: ✅ Works
  - n=100: ✅ Works
  - n=200: ✅ Works (just confirmed!)
  - n=2005: ❌ "Internal Service Exception"

**Next:** Need to find actual limit between 200-2005

---

## Q2: Why 3-8 Seconds Instead of Milliseconds?

### Answer: **Network API Calls, Not Computation!** 🌐

**Time Breakdown (n=2005 local processing):**
```
Local Computation:
  - Load JSON:           3 ms
  - Parse data:          0.4 ms
  - Build QUBO:        291 ms  ← O(n²) matrix construction
  - Normalize:          14 ms
  - QUBO → Ising:       10 ms
  - Ising → Coupling:   24 ms
  - Validate:            5 ms
  ───────────────────────────
  Total Local:       ~350 ms  ← This IS milliseconds!

Network & Server:
  - API connection:   1000 ms
  - Upload matrix:     ~? ms
  - Queue waiting:  1000-5000 ms  ← Polling "processing..."
  - Emulator run:      ~? ms
  - Download result:   ~? ms
  ───────────────────────────
  Total Network:   2000-6000 ms  ← This is the 3-8 seconds!
```

**For n~100:**
- Should be even faster (~100ms local)
- But still 2-5 seconds for API roundtrip
- **Emulator itself might run in <100ms**, but we don't see that separately

**Why Not Faster:**
1. **Cloud API overhead** (unavoidable)
2. **Job queue** (multi-tenant service)
3. **Data transfer** (complex64 matrices)
4. **Polling interval** (~1 second between status checks)

---

## Q3: Why Does LPU Underperform Greedy?

### Answer: **Multiple Issues, Main One is Penalty Parameter** 🎯

**Key Observation:** LPU under-utilizes gas

| Size | LPU Gas % | Greedy Gas % | Difference |
|------|-----------|--------------|------------|
| n=10 | 2.6% | 10.9% | **-76%** |
| n=50 | 15.4% | 30.0% | **-49%** |
| n=100 | 28.7% | 57.9% | **-50%** |
| n=200 | 40.7% | 81.6% | **-50%** |

**Root Causes:**

### 1. **Penalty Too Strong** (Primary Issue!) 🔥
```python
penalty = 2 × (max_profit / max_gas)  # Current
```

This makes the constraint term **dominate** the objective:
- **Constraint term:** `α(Σ gas×x - capacity)²`  
- **Objective term:** `Σ profit×x`

When penalty is too high:
- Solver prioritizes constraint satisfaction over profit
- Selects fewer items to "play it safe"
- Result: Low gas utilization, low profit

**Fix:** Try much smaller penalties: `0.01, 0.1, 0.5, 1.0`

### 2. **Normalization Loses Information**
Original:
- Profits: 10^18 - 10^24 wei (6 orders of magnitude!)
- Gas: 21,000 - 600,000

After normalization:
- All QUBO values: 0 - 1

**Problem:** Can't distinguish high-value from low-value transactions anymore!

**Fix:** 
- Normalize profits and gas separately
- Or use logarithmic scaling
- Or don't normalize at all (if coupling matrix allows)

### 3. **Greedy-Biased Test Set**
We were:
1. Sorting by profit/gas ratio (greedy's metric)
2. Taking top N
3. Comparing LPU vs greedy on this subset

**Of course greedy wins!** We gave it the exact items it would choose!

**Fix:** Test on full dataset or random subsets

### 4. **Simple Phase Extraction**
```python
ising = np.where(phases >= 0, 1, -1)  # Too simple?
```

Should try:
- Multiple thresholds
- Best energy search
- Ensemble solutions

---

## Q4: Low Gas Utilization - Why?

### Answer: **Penalty Parameter Forces Conservative Solutions** 

**Greedy's approach:**
```
Select items while gas < capacity
→ Fills to ~100% gas utilization
```

**LPU's current behavior:**
```
Minimize: -profit + α(gas - capacity)²

With α too large:
→ Heavily penalizes approaching capacity
→ Stays well below limit  
→ 30-40% gas utilization
```

**The Math:**

At capacity boundary (gas = capacity):
- Profit term: ~10^24
- Penalty term: α × 0² = 0

Just below capacity (gas = 0.8 × capacity):
- Profit term: ~0.8 × 10^24
- Penalty term: α × (0.2 × capacity)² = α × 3.6×10^14

If α = 10^10, penalty term = 3.6×10^24 >> profit!

**Solution violates constraint slightly:**
- Profit gained: 10^24
- Penalty paid: α × (small_violation)²

With α too high, even tiny violations are too expensive!

---

## Q5: Which Parameters Need Tuning?

### Priority Order:

### **1. Penalty Parameter (α)** - HIGHEST PRIORITY 🔥

**Current:**
```python
penalty = 2 × (max_profit / max_gas)
```

**Problem:** Way too large! Forces conservative solutions.

**Test Range:**
```python
# Start here
penalties = [0.001, 0.01, 0.1, 1.0, 10.0]

# Theory: penalty should make constraint violation
# slightly more expensive than profit gain, not 1000x more
```

**Expected Impact:** 10-100x improvement in gas utilization

---

### **2. XY Model Parameters** - HIGH PRIORITY 🎯

**alphaI (self-coupling strength):** Default 0.7
```python
# Test range
alphaI_values = [0.3, 0.5, 0.7, 0.9]

# Too small → lasers "die" (zero amplitude)
# Too large → poor coupling between spins
```

**coupAmp (coupling amplitude):** Default 0.3
```python
# Test range  
coupAmp_values = [0.05, 0.1, 0.2, 0.3, 0.5]

# Affects interaction strength between variables
```

**Documentation says:** "Should be optimized per problem"

---

### **3. Normalization Method** - MEDIUM PRIORITY

**Current:** Divide entire QUBO by max value
```python
Q_normalized = Q / max(|Q|)
```

**Alternatives:**
```python
# Option A: Separate normalization
profit_norm = profits / max(profits)
gas_norm = gas_costs / max(gas_costs)

# Option B: Logarithmic
profit_log = np.log1p(profits)

# Option C: Rank-based
profit_ranks = rankdata(profits)

# Option D: No normalization (if coupling matrix allows)
```

---

### **4. Emulator Run Parameters** - LOW PRIORITY

**num_runs:** Current 10
```python
# More runs → better sampling → more robust
# But slower
num_runs = [5, 10, 20, 50]
```

**num_iterations:** Current 1000
```python
# More iterations → better convergence
# But slower  
num_iterations = [500, 1000, 2000, 5000]
```

---

### **5. Solution Extraction Method** - MEDIUM PRIORITY

**Current:** Simple threshold at 0
```python
ising = np.where(phases >= 0, 1, -1)
```

**Better:** Sweep thresholds
```python
best_solution = None
best_value = -inf

for threshold in np.linspace(-π, π, 100):
    ising = np.where(phases >= threshold, 1, -1)
    qubo = (ising + 1) / 2
    
    # Calculate actual profit (not Ising energy)
    total_profit = sum(profits[i] * qubo[i])
    total_gas = sum(gas_costs[i] * qubo[i])
    
    if total_gas <= CAPACITY and total_profit > best_value:
        best_value = total_profit
        best_solution = qubo
```

---

## Summary Answers

| Question | Short Answer | Detail |
|----------|--------------|--------|
| **Q1: Where's 10-100 limit?** | My mistake! | No such limit for emulator. Need to test actual limit (200+ works, 2005 fails) |
| **Q2: Why 3-8 seconds?** | Network API | Local compute is ~350ms. Rest is network + queue + server overhead |
| **Q3: Why underperform greedy?** | Penalty too strong | Forces conservative solutions. Also: normalization, extraction, testing on greedy-biased subset |
| **Q4: Low gas utilization?** | Penalty parameter | α too large makes constraint violation too expensive, solver stays well below capacity |
| **Q5: Which parameters?** | Penalty (α) first! | Then XY params, then normalization, then extraction method |

---

## Immediate Action Plan

1. **Test n=200, 500, 1000** to find actual emulator limit
2. **Parameter sweep on penalty** - try α = 0.001, 0.01, 0.1, 1.0
3. **Fix normalization** - preserve relative profit magnitudes
4. **Test on full dataset** (not greedy-filtered subset)
5. **Better solution extraction** - threshold sweep

**Expected Result:** With proper penalty, should match or beat greedy!


