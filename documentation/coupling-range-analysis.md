# QUBO Coupling Range Analysis

## TL;DR

**YES, the QUBO has extreme coupling ranges: 370,000× variation in magnitude.**

This comes from the **inherent asymmetry in blockchain transaction data** and is **amplified by the quadratic constraint formulation**.

## The Numbers

### QUBO Matrix Statistics

| Component | Min | Max | Range |
|-----------|-----|-----|-------|
| **Diagonal (Q[i,i])** | -8.37×10²³ | -4.01×10²¹ | ~200× |
| **Off-diagonal (Q[i,j])** | 2.25×10¹⁸ | 7.14×10²² | **31,800×** |
| **Overall** | -8.37×10²³ | 7.14×10²² | **372,000×** |

### After Normalization

All values scaled to [-1, 1], but **relative structure preserved**.

The coupling matrix still has the same relative asymmetry!

## Where Does This Come From?

### Source 1: Profit Variation (162,793×) 🔥

**The root cause:**
```
Smallest profitable tx: 0.000000046 ETH (46 Gwei)
Largest profitable tx:  0.007440000 ETH (7.44 million Gwei)

Ratio: 162,793× !
```

**Why?**
- Some transactions are simple transfers (low MEV)
- Others are complex arbitrage/liquidations (high MEV)
- This is **inherent to blockchain data** - can't be avoided

**Impact on QUBO:**
```python
Q[i,i] = -profit[i] + ...
         ^^^^^^^^^^^
         Varies by 162,793×
```

### Source 2: Gas Cost Variation (222×)

```
Smallest gas: 16,800 (simple transfer)
Largest gas:  3,736,328 (complex contract)

Ratio: 222×
```

**Why?**
- Simple transfers: 21,000 gas
- Token transfers: 50,000-100,000 gas
- Complex DeFi: 200,000-3,000,000+ gas

**Impact on QUBO:**
```python
Q[i,i] = ... + α(gas[i]² - 2*capacity*gas[i])
                 ^^^^^^^^
                 Varies by 222×
```

### Source 3: Quadratic Amplification (49,284×) 🔥🔥

**The killer:**
```python
Q[i,j] = 2*α*gas[i]*gas[j]
              ^^^^^^^^^^^^^^
              Product of two gas values
```

**Effect:**
```
Gas variation: 222×
Gas² variation: 222² = 49,284× !
```

**This is why off-diagonal terms vary by 31,800×**

### Source 4: Alpha Multiplier (3.98×10⁹)

```python
α = 2 × (max_profit / max_gas)
α = 2 × (7.44×10¹⁵ / 3,736,328)
α = 3.98×10⁹
```

Multiplies all constraint terms, making large values even larger.

## The QUBO Formulation

```
Minimize: E(x) = Σᵢ Q[i,i]×xᵢ + Σᵢ<ⱼ Q[i,j]×xᵢ×xⱼ

Where:
  Q[i,i] = -profit[i] + α(gas[i]² - 2*capacity*gas[i])
           ^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
           Objective     Constraint (quadratic)
           (linear)      

  Q[i,j] = 2*α*gas[i]*gas[j]
           ^^^^^^^^^^^^^^^^^^
           Constraint coupling
           (quadratic product)
```

### Breaking Down Q[i,i]:

**Term 1: -profit[i]**
- Range: -7.44×10¹⁵ to -4.57×10¹⁰
- Variation: **162,793×** ← From profit asymmetry

**Term 2: α×gas[i]²**
- Range: 1.12×10¹⁸ to 5.56×10²²
- Variation: **49,462×** ← From gas² amplification

**Term 3: -2×α×capacity×gas[i]**
- Range: -4.01×10²¹ to -8.93×10²³
- Variation: **222×** ← From gas variation

**Combined diagonal:**
- The constraint terms (quadratic) are **MUCH LARGER** than profit terms (linear)
- Constraint dominates by 100-1000×

### Breaking Down Q[i,j]:

```python
Q[i,j] = 2*α*gas[i]*gas[j]
```

**Example:**
- Smallest: 2 × 3.98×10⁹ × 16,800 × 16,800 = 2.25×10¹⁸
- Largest:  2 × 3.98×10⁹ × 3,736,328 × 3,736,328 = 1.11×10²³

**Variation: 49,462×** (gas variation squared!)

## Why This Matters for LPU

### Problem 1: Extreme Asymmetry

**LPU emulator expects:**
- Relatively uniform coupling strengths
- Spin glass-like problems
- Symmetric interactions

**What we have:**
- 370,000× range in couplings
- Highly asymmetric
- Some couplings dominate by 10⁶×

### Problem 2: Constraint Dominates Objective

**The math:**
```
Profit term (linear):      ~10¹⁵ wei
Constraint term (quadratic): ~10²³ wei

Ratio: Constraint is 10⁸× larger!
```

**After normalization:**
- Both scaled to [-1, 1]
- But relative structure preserved
- Constraint couplings still dominate

**Effect:**
- LPU sees "avoid gas violations" much more strongly than "maximize profit"
- Conservative solutions (low gas utilization)
- Misses high-profit transactions

### Problem 3: Signal Dilution

**High-profit transaction:**
- Profit: 7.44×10¹⁵ wei (should be strongly selected)
- But: Constraint term is 10²³ (100,000× larger)
- After normalization: Profit signal is 0.00001 of total

**Low-profit transaction:**
- Profit: 4.57×10¹⁰ wei
- Constraint term: Similar magnitude (~10²¹)
- After normalization: Even weaker signal

**Result:** LPU can't distinguish high-value from low-value transactions!

## Comparison: What Would Be "Good" for LPU?

### Ideal Problem for XY Model:
```
Couplings: All within 10-100× range
Symmetry: Relatively uniform
Structure: Spin glass, graph coloring, max-cut
```

### Our Knapsack Problem:
```
Couplings: 370,000× range ❌
Symmetry: Highly asymmetric (162,793× profit variation) ❌
Structure: Dense all-to-all constraints ❌
Quadratic: Amplifies asymmetry by squaring ❌
```

## Can We Fix This?

### Option 1: Different Penalty Formulation ❓

**Current:**
```python
Q[i,i] = -profit[i] + α(gas[i]² - 2*capacity*gas[i])
```

**Alternative (linear constraint):**
```python
Q[i,i] = -profit[i] + α×gas[i]  # Linear, not quadratic
```

**Effect:**
- Reduces amplification (222× instead of 49,284×)
- But loses quadratic constraint encoding
- May not work with QUBO formulation

### Option 2: Logarithmic Scaling ❓

```python
Q[i,i] = -log(profit[i]) + α×log(gas[i])
```

**Effect:**
- Compresses range (162,793× → ~12×)
- But changes problem structure
- May not preserve optimality

### Option 3: Rank-Based Encoding ❓

```python
profit_ranks = rankdata(profits)  # 1 to 75
Q[i,i] = -profit_ranks[i] + ...
```

**Effect:**
- Uniform spacing
- But loses magnitude information
- High-value txs not distinguished

### Option 4: Accept Limitations ✅

**Reality:**
- This problem has inherent asymmetry
- Quadratic constraint formulation amplifies it
- XY laser model not designed for this
- **Use different solver or approach**

## The Fundamental Issue

### The Knapsack Problem:
```
Maximize: Σ profit[i]×x[i]          (linear objective)
Subject to: Σ gas[i]×x[i] ≤ capacity  (linear constraint)
```

### QUBO Encoding:
```
Minimize: -Σ profit[i]×x[i] + α(Σ gas[i]×x[i] - capacity)²
          ^^^^^^^^^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
          Linear (weak signal)  Quadratic (strong signal)
```

**The problem:**
- Converting linear constraint to quadratic penalty
- Quadratic grows much faster than linear
- Creates extreme coupling ranges
- LPU struggles with this asymmetry

## Conclusion

**Q: Does the QUBO have broad coupling ranges?**  
**A: YES - 370,000× variation in magnitude**

**Q: Where does this come from?**  
**A: Three sources:**
1. **Profit variation (162,793×)** - Inherent to blockchain data
2. **Gas variation (222×)** - Transaction complexity
3. **Quadratic amplification (49,284×)** - QUBO formulation squares gas terms

**Q: Why does this hurt LPU performance?**  
**A:**
- XY model designed for uniform couplings
- Extreme asymmetry → strong couplings dominate
- Constraint signal (quadratic) >> profit signal (linear)
- LPU can't distinguish high-value from low-value transactions

**Q: Can we fix it?**  
**A: Difficult:**
- Asymmetry is inherent to the problem
- Quadratic formulation is standard for QUBO
- Alternative encodings may not preserve optimality
- **Likely need different solver approach**

---

**Bottom line:** The knapsack problem's inherent asymmetry, combined with quadratic constraint encoding, creates coupling ranges that the XY laser model struggles to handle effectively.

