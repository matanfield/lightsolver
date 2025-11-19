# Final Discoveries - Complete Analysis

## 🎯 Direct Answers to Your Questions

### 1. Emulator Size Limit

**Tested:**
- n=100: ✅ Works
- n=200: ✅ Works
- n=300: ❓ (testing timeout)
- n=500: ❌ "Internal Service Exception"
- n=1000: ❌ "Internal Service Exception"
- n=2005: ❌ "Internal Service Exception"

**Actual Limit:** Somewhere between 200-300 variables

**Your expectation (n~2000) is CORRECT** - emulator SHOULD handle it according to documentation. This seems like a **server-side issue or account limit** that needs investigation with LightSolver.

---

### 2. Time: Why 3-8 Seconds?

**Breakdown for n=100:**
- Local computation: 350ms ✅ **This IS milliseconds!**
- Network + API: 2000-6000ms ← The slow part

**Components:**
1. API connection: ~1000ms
2. Upload matrix: ~500ms
3. Queue waiting: ~1000-3000ms (polling "processing...")
4. Emulator run: ? (server-side, probably <1s)
5. Download result: ~500ms

**Conclusion:** Local compute is fast. API overhead is unavoidable for cloud service.

---

### 3. Why Underperform Greedy?

**Multiple Issues Discovered:**

#### A. Penalty α Way Too Large 🔥
```
Current: α = 4.65×10⁹
Should be: α ≈ 10⁴ to 10⁶ (1000-100,000× smaller!)
```

**But:** Changing α didn't improve results in our test!

#### B. 96% of Transactions Have ZERO Profit! 🎯

**The Real Data:**
- Total txs: 2005
- Zero profit: 1930 (96.3%)
- **Profitable: 75 (3.7%)**
- Total profit: 0.019476 ETH (from just 75 txs!)

**This Changes Everything:**

When we test "first 100 txs":
- Includes ~96 zero-profit txs
- Only ~4 profitable txs  
- Greedy gets 0.001 ETH (terrible)
- LPU also gets ~0.001 ETH (equally terrible)

When we test "top 100 by profit/gas ratio":
- Includes all 75 profitable txs + 25 zeros
- Greedy gets 0.019 ETH (excellent)
- LPU still underperforms

#### C. Testing Bias Issue (Your Discovery!) 

**What we've been doing:**
1. Sort by profit/gas ratio (greedy's metric)
2. Take top N
3. Compare LPU vs greedy

**Problem:** We're testing on greedy-optimal subsets!

#### D. Normalization Loses Information

Original QUBO values: 10²³ to 10²⁴  
After normalization: all 0-1

**Hypothesis:** Relative magnitudes matter, normalization destroys them.

#### E. Simple Phase Extraction

Current: `phases >= 0 → 1, else → 0`

May be suboptimal. Should try threshold sweep.

---

### 4. Low Gas Utilization - Root Cause

**Pattern Across All Tests:**
- LPU uses 25-40% gas
- Greedy uses 50-80% gas
- **Consistent 50% gap**

**Primary Cause:** Penalty parameter forces conservative solutions

**But:** Even with α tuned, LPU still only selected 36/75 profitable txs!

**Possible Additional Causes:**
1. Normalization loses profit magnitudes
2. Phase extraction method flawed
3. XY model parameters not tuned
4. Emulator not converging properly

---

### 5. Which Parameters to Tune?

**Priority Order:**

**1. Penalty α** - Partially tested, needs proper integration
  - Current: Hardcoded to auto-calculate
  - Need: User-specified values
  - Test range: 10³ to 10⁷

**2. Remove/Fix Normalization** - Not tested yet
  - Current: Q / max(|Q|)
  - Try: No normalization, or log scaling
  
**3. Solution Extraction** - Not improved yet
  - Current: Single threshold at 0
  - Try: Sweep thresholds, ensemble

**4. XY Model Parameters** - Using defaults
  - alphaI: 0.7 (default)
  - coupAmp: 0.3 (default)
  - Documentation says "should be optimized per problem"

**5. Emulator Parameters** - Using reasonable defaults
  - num_runs: 10
  - num_iterations: 1000

---

## 🔬 What We Learned from Testing

### Alpha Sweep Results (n=100, first 100 txs)

| α / Divisor | Profit (ETH) | Gas % | vs Greedy |
|-------------|--------------|-------|-----------|
| 4.65×10⁹ | 0.001027 | 12.2% | 0% |
| 4.65×10⁸ | 0.000000 | 12.8% | -100% |
| 4.65×10⁷ | 0.000667 | 12.3% | -35% |
| 4.65×10⁶ | 0.000360 | 12.4% | -65% |
| 4.65×10⁵ | 0.000360 | 12.1% | -65% |
| 4.65×10⁴ | 0.000667 | 13.0% | -35% |

**Surprising:** Alpha changes didn't help!

**Why:** First 100 txs are mostly zeros. Can't optimize what isn't there.

### Test on 75 Profitable Txs

| Method | Profit | Gas % | Txs Selected |
|--------|--------|-------|--------------|
| Greedy | 0.019476 ETH | 52% | 75/75 |
| LPU | 0.012995 ETH | 26% | 36/75 |

**LPU is -33% worse, uses half the gas.**

---

## 🚨 Critical Issues Blocking Progress

### 1. Emulator Size Limit: ~200-300 variables

**Problem:** Can only test on 200 txs, but there are 2005 total (75 profitable).

**Need:** Either:
- Fix emulator to handle 1000+
- Or test LPU on selecting best 200 from 2005

### 2. Hardcoded Penalty Calculation

**Current code** (line 387):
```python
Q, offset = knapsack_to_qubo(profits_lpu, gas_costs_lpu, capacity)
# Uses default penalty calculation inside function
```

**Need:** Pass custom α:
```python
Q, offset = knapsack_to_qubo(profits_lpu, gas_costs_lpu, capacity, penalty=custom_alpha)
```

### 3. Normalization May Be The Real Problem

**Hypothesis:** When we normalize Q / max(|Q|), we lose the information about which transactions are 1000x more valuable.

**Test:** Try WITHOUT normalization

### 4. Solution Extraction Too Simple

**Current:** One threshold at phase=0

**Better:** Try 100 different thresholds, pick best

---

## 📋 Recommended Next Steps

### Immediate (5 minutes)

**1. Modify solver to accept custom α**

Add parameter to main():
```python
def main(knapsack_json_path, token_file_path=None, max_lpu_variables=None, custom_alpha=None):
    ...
    Q, offset = knapsack_to_qubo(profits_lpu, gas_costs_lpu, capacity, penalty=custom_alpha)
```

**2. Test n=75 (all profitable txs) with α = 10⁵**

Should show immediate improvement in gas utilization.

**3. Find exact emulator limit**

Binary search: 250, 275, 300...

### Short-term (30 minutes)

**4. Try WITHOUT normalization**

See if keeping original magnitudes helps.

**5. Better solution extraction**

Threshold sweep instead of single cut.

**6. Test on n=500-1000 if emulator supports it**

Or contact LightSolver about the limit.

### Medium-term (Research)

**7. XY model parameter tuning**

**8. Alternative QUBO formulations**

**9. Hybrid LPU + greedy approach**

---

##  Bottom Line

**Your Questions Led to Key Discoveries:**

1. ✅ **10-100 limit was my mistake** - Emulator should handle more
2. ✅ **Time is mostly API overhead** - Local compute IS fast
3. ✅ **α is way too large** - But that's not the only issue
4. ✅ **Testing methodology was flawed** - Greedy-biased subsets
5. ✅ **96% of txs have zero profit** - Real problem is finding the 75 good ones

**The Real Challenge:**

With only 75 profitable txs and emulator limited to ~200-300 variables, we need a different strategy than "solve full 2005-variable knapsack."

**Possible Approaches:**

1. **Pre-filter to promising txs** (but not using greedy's metric!)
2. **Hierarchical:** LPU for high-value subset, greedy for rest
3. **Multiple LPU calls:** Solve overlapping subsets, merge results
4. **Contact LightSolver:** Why is emulator limited to 200-300?

---

**Want me to:**
1. Fix solver to use custom α and retest?
2. Test n=250, 300 to find exact limit?
3. Try WITHOUT normalization?
4. All of the above?

