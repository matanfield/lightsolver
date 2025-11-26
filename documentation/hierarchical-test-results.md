# Hierarchical LPU Test Results

## Summary

**Result:** 43/75 transactions selected (61.1% efficiency)

**Same as flat LPU!** The hierarchical approach didn't improve performance.

## Test Configuration

### Tiers Created (6 tiers by orders of magnitude):

| Tier | Range | Count | Profit | Gas | Variance |
|------|-------|-------|--------|-----|----------|
| 1 | 10¹⁵-10¹⁶ wei | 3 | 0.009466 ETH (49%) | 11% | 7.4× |
| 2 | 10¹⁴-10¹⁵ wei | 26 | 0.008857 ETH (46%) | 17% | 8.5× |
| 3 | 10¹³-10¹⁴ wei | 24 | 0.001108 ETH (6%) | 5% | 8.7× |
| 4 | 10¹²-10¹³ wei | 13 | 0.000042 ETH (0.2%) | 15% | 5.2× |
| 5 | 10¹¹-10¹² wei | 7 | 0.000003 ETH (0.0%) | 4% | 5.0× |
| 6 | 10¹⁰-10¹¹ wei | 2 | 0.000000 ETH (0.0%) | 0.4% | 1.9× |

**Variance reduction achieved:** 162,793× → 5-9× in most tiers ✅

## Results by Tier

| Tier | Available | Selected | Profit | Gas Used | Efficiency |
|------|-----------|----------|--------|----------|------------|
| 1 | 3 | 1/3 | 0.007440 ETH | 2.4M | **33%** ❌ |
| 2 | 26 | 11/26 | 0.003760 ETH | 2.8M | **42%** ❌ |
| 3 | 24 | 15/24 | 0.000665 ETH | 0.7M | **63%** ⚠️ |
| 4 | 13 | 10/13 | 0.000032 ETH | 0.8M | **77%** ✅ |
| 5 | 7 | 5/7 | 0.000002 ETH | 0.6M | **71%** ✅ |
| 6 | 2 | 1/2 | 0.000000 ETH | 0.04M | **50%** |

**Pattern:** LPU performs WORSE on high-value tiers, BETTER on low-value tiers!

## Why Didn't It Help?

### Issue 1: LPU Still Underperforms Within Each Tier

Even with reduced variance (7-9×), LPU only selects:
- Tier 1: 1/3 (should select all 3!)
- Tier 2: 11/26 (should select all 26!)

**The variance reduction helped, but not enough.**

### Issue 2: High-Value Tiers Hurt Most

Missing from Tier 1:
- 2/3 transactions
- Lost profit: 0.002 ETH (10% of total!)

Missing from Tier 2:
- 15/26 transactions
- Lost profit: 0.005 ETH (26% of total!)

**Total: 36% of profit lost in top 2 tiers alone!**

### Issue 3: Low-Value Tiers Perform Better

Tiers 4-5 (lowest value):
- 77% and 71% efficiency
- But these are only 0.2% of total profit!

**LPU works better on low-value transactions (less important ones).**

## Comparison

| Method | Selected | Profit | Efficiency | Time |
|--------|----------|--------|------------|------|
| **Optimal** | 75/75 | 0.019476 ETH | 100% | - |
| **Flat LPU** | 43/75 | 0.015255 ETH | 78% | 13s |
| **Hierarchical LPU** | 43/75 | 0.011899 ETH | **61%** | 36s |
| **Greedy** | 75/75 | 0.019476 ETH | 100% | <1s |

**Hierarchical is actually WORSE than flat!** (61% vs 78%)

## Why Is Hierarchical Worse?

### Hypothesis: Sequential Errors Compound

**Flat approach:**
- One optimization over all 75
- Makes one set of mistakes
- Result: 43/75 selected

**Hierarchical approach:**
- 6 separate optimizations
- Each tier makes mistakes
- **Mistakes in Tier 1 can't be corrected later**
- Result: 43/75 selected, but worse distribution

**Example:**
- Tier 1 misses 2 high-value txs (0.002 ETH)
- Tier 2 selects some low-value txs instead
- Net result: Lower total profit

### The Problem: LPU Underperforms at ALL Scales

Even with 7-9× variance (vs 162,793×):
- LPU still only selects 33-42% in top tiers
- The fundamental issue remains

**Variance reduction helped, but LPU still can't optimize well.**

## What We Learned

### ✅ Good News:

1. **Hierarchical approach works mechanically** - All tiers ran successfully
2. **Variance reduction achieved** - 162,793× → 5-9× in most tiers
3. **Fast per tier** - 5-7 seconds each
4. **Scalable** - Could handle more tiers if needed

### ❌ Bad News:

1. **LPU still underperforms** - Even with reduced variance
2. **High-value tiers hurt most** - 33-42% efficiency where it matters
3. **Sequential errors compound** - Can't recover from early mistakes
4. **Worse than flat** - 61% vs 78% efficiency

## Root Cause Analysis

### The Fundamental Issue Remains:

Even within tiers with 7-9× variance:
- QUBO couplings still span 1000-10,000×
- Constraint terms still dominate objective
- LPU still can't distinguish well

**The problem is deeper than just variance.**

### What's Really Happening:

**In Tier 1 (3 transactions, 7.4× variance):**
```
Transaction A: 0.007440 ETH, 2.4M gas
Transaction B: 0.001024 ETH, 0.6M gas  
Transaction C: 0.001002 ETH, 0.3M gas

Optimal: Select all 3 (total 3.3M gas, fits easily!)
LPU: Selects only A (misses 0.002 ETH)
```

**Why?** Even with 7× variance, the QUBO formulation still creates issues:
- Quadratic gas terms dominate
- LPU is overly conservative
- Selects fewer items than optimal

## Conclusion

### Hierarchical Strategy:

**✅ Concept is sound:**
- Reduces variance dramatically
- Prioritizes high-value decisions
- Scalable and fast

**❌ Doesn't solve the fundamental problem:**
- LPU still underperforms within each tier
- Errors in high-value tiers hurt most
- Sequential approach can't recover from mistakes

### The Real Issue:

**The XY laser model + QUBO formulation is not well-suited for knapsack problems**, even with:
- Optimal alpha
- Reduced variance (hierarchical)
- Normalized values
- Multiple attempts

**LPU consistently selects 40-60% of transactions across all approaches.**

## Recommendations

### Option 1: Accept Limitations ✅

**Conclusion:** XY model not suitable for this problem type

**For production:** Use greedy (100% efficient, <1s)

**For research:** Document findings, try different problems

### Option 2: Try Constrained Problem

**Test on:** Capacity = 10M (instead of 30M)

**Hypothesis:** When NOT all fit, hierarchical may help more

**Expected:** Still underperforms, but might be closer to greedy

### Option 3: Hybrid Approach

**Strategy:**
- Use greedy for high-value tiers (reliable)
- Use LPU for low-value tiers (where it works better)
- Combine results

**Expected:** 90-95% efficiency

## Bottom Line

**Hierarchical approach:**
- ✅ Successfully implemented
- ✅ Reduces variance as intended
- ❌ Doesn't improve LPU performance
- ❌ Actually performs worse (61% vs 78%)

**The fundamental issue:**
- XY laser model struggles with knapsack
- Even with optimal parameters and reduced variance
- Consistently underperforms across all approaches

**Time to conclude:** This approach has limitations for this problem type.

---

**Total time invested:** 4+ hours  
**Result:** Complete understanding of why it doesn't work  
**Value:** Documented methodology for future attempts  
**Recommendation:** Use greedy for production, document learnings

