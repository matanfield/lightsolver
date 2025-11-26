# Systematic Debug Plan - Bottom-Up Approach

## Goal
Understand exactly where and why the LPU emulator fails, starting from basic QUBO solving.

## Phase 1: QUBO Fundamentals (Direct Solver)

### Step 1.1: Create Direct QUBO Solver (Brute Force)
**Purpose:** Ground truth for small problems (n ≤ 20)

**Implementation:**
```python
def solve_qubo_bruteforce(Q, offset=0):
    """
    Solve QUBO by trying all 2^n combinations.
    Returns: best_solution, best_energy
    """
    n = Q.shape[0]
    best_solution = None
    best_energy = float('inf')
    
    for i in range(2**n):
        # Convert i to binary vector
        x = np.array([(i >> j) & 1 for j in range(n)])
        
        # Calculate energy: x^T Q x
        energy = np.dot(x, np.dot(Q, x)) + offset
        
        if energy < best_energy:
            best_energy = energy
            best_solution = x
    
    return best_solution, best_energy
```

**Test:** n=5, n=10, n=15, n=20

**Validation:** Verify energy calculation is correct

---

### Step 1.2: Create Controlled QUBO Generator
**Purpose:** Generate QUBOs with known properties

**Types to generate:**
1. **Uniform random:** All coefficients in [-1, 1]
2. **Sparse:** Most coefficients zero
3. **Ferromagnetic:** All negative (easy)
4. **Antiferromagnetic:** All positive (hard)
5. **Mixed:** Controlled variance

**Parameters:**
- `n`: Problem size
- `density`: Fraction of non-zero couplings
- `variance`: Range of coefficient values
- `bias`: Diagonal vs off-diagonal strength

**Implementation:**
```python
def generate_qubo(n, density=1.0, variance=1.0, seed=None):
    """
    Generate controlled QUBO matrix.
    
    Args:
        n: Problem size
        density: Fraction of non-zero couplings (0-1)
        variance: Coefficient range multiplier
        seed: Random seed for reproducibility
    
    Returns:
        Q: QUBO matrix (n×n, upper triangular)
    """
```

---

## Phase 2: LPU on Simple QUBOs

### Step 2.1: Test LPU on Uniform Random QUBOs
**Purpose:** Establish baseline performance

**Test matrix:**
- n = 5, 10, 15, 20, 25, 30
- density = 1.0 (fully connected)
- variance = 1.0 (coefficients in [-1, 1])
- 10 random instances per size

**Metrics:**
- Success rate (finds optimal?)
- Energy gap (LPU energy - optimal energy)
- Time per solve

**Expected:** Should work well for uniform, moderate-size problems

---

### Step 2.2: Test LPU on Sparse QUBOs
**Purpose:** See if sparsity helps

**Test matrix:**
- n = 20, 30, 40, 50
- density = 0.1, 0.3, 0.5, 0.7, 1.0
- variance = 1.0

**Hypothesis:** Sparse problems easier for LPU

---

### Step 2.3: Test LPU on High-Variance QUBOs
**Purpose:** Understand variance tolerance

**Test matrix:**
- n = 20
- variance = 1, 10, 100, 1000, 10000
- density = 1.0

**Hypothesis:** High variance (>100×) causes problems

**This is the key test for our knapsack issue!**

---

## Phase 3: Compare with Classical Heuristics

### Step 3.1: Implement Simulated Annealing for QUBO
**Purpose:** Classical baseline for larger problems

**Implementation:**
```python
def solve_qubo_simulated_annealing(Q, T_start=1.0, T_end=0.01, steps=1000):
    """
    Solve QUBO using simulated annealing.
    Standard classical heuristic.
    """
```

**Test:** Same QUBOs as LPU tests

---

### Step 3.2: Implement Tabu Search for QUBO
**Purpose:** Another classical baseline

**Implementation:**
```python
def solve_qubo_tabu_search(Q, tabu_tenure=10, max_iter=1000):
    """
    Solve QUBO using tabu search.
    """
```

---

### Step 3.3: Compare All Solvers
**Purpose:** Understand LPU's competitive position

**Solvers:**
1. Brute force (n ≤ 20, optimal)
2. LPU emulator
3. Simulated annealing
4. Tabu search
5. Greedy (if applicable)

**Metrics:**
- Solution quality (energy)
- Success rate (finds optimal for small n)
- Time
- Scalability (max n that works)

---

## Phase 4: Knapsack-Specific QUBOs

### Step 4.1: Generate Simple Knapsack QUBOs
**Purpose:** Test on knapsack structure specifically

**Start simple:**
- n = 10 items
- All profits = 1 (uniform)
- All weights = 1 (uniform)
- Capacity = 5

**Expected:** Should find optimal easily (select any 5)

---

### Step 4.2: Add Profit Variation
**Purpose:** Introduce asymmetry gradually

**Test sequence:**
- Profit range: 1-2× (easy)
- Profit range: 1-10× (moderate)
- Profit range: 1-100× (hard)
- Profit range: 1-1000× (very hard)
- Profit range: 1-162,793× (our actual problem!)

**Track:** At what variance does LPU start failing?

---

### Step 4.3: Test Real Knapsack Instances
**Purpose:** Validate on actual problem

**Test:**
1. Small subset (n=10) from real data
2. Medium subset (n=25) from real data
3. Large subset (n=50) from real data
4. Full problem (n=75) from real data

**Compare:**
- LPU vs brute force (n=10)
- LPU vs simulated annealing (n=25, 50, 75)
- LPU vs greedy (all sizes)

---

## Phase 5: Identify Breaking Point

### Step 5.1: Binary Search for Variance Threshold
**Purpose:** Find exact variance where LPU fails

**Method:**
- Fix n = 20 (can verify with brute force)
- Test variance: 1, 10, 100, 1000, 10000
- Find where success rate drops below 80%

**Result:** "LPU works for variance < X"

---

### Step 5.2: Binary Search for Size Threshold
**Purpose:** Find max n for given variance

**Method:**
- Fix variance = 10 (moderate)
- Test n: 10, 20, 30, 40, 50, 60, 70, 80
- Find where success rate drops below 80%

**Result:** "LPU works for n < Y at variance 10"

---

### Step 5.3: Map Operating Region
**Purpose:** Define LPU's sweet spot

**Create 2D map:**
- X-axis: Problem size (n)
- Y-axis: Variance
- Color: Success rate

**Result:** Visual map of where LPU works

---

## Phase 6: Root Cause Analysis

### Step 6.1: Analyze Failed Cases
**Purpose:** Understand failure mode

**For each failed case:**
1. Examine QUBO matrix structure
2. Check coupling matrix validity
3. Analyze laser dynamics (final states)
4. Compare with successful cases

**Questions:**
- Do lasers converge?
- Are final states stable?
- Is energy landscape too rugged?

---

### Step 6.2: Test Mitigation Strategies
**Purpose:** Try to expand operating region

**Strategies:**
1. Adjust XY parameters (alphaI, coupAmp)
2. Increase num_runs, num_iterations
3. Different normalization schemes
4. Pre-conditioning the QUBO

**Result:** Can we make LPU work for higher variance?

---

## Phase 7: Conclusions and Recommendations

### Step 7.1: Document Operating Region
**Output:** "LPU works well for:"
- n < X
- variance < Y
- density > Z
- etc.

---

### Step 7.2: Knapsack Applicability
**Conclusion:** Does our knapsack problem fit LPU's operating region?

**If NO:** Document why and recommend alternatives

**If YES:** Identify what we were doing wrong

---

### Step 7.3: Final Recommendations
**For this project:**
- Use LPU? (Yes/No)
- Use hybrid approach? (LPU + classical)
- Use classical only? (Greedy, SA, etc.)

**For future projects:**
- What problem types suit LPU?
- What to avoid?
- Best practices?

---

## Implementation Order

### Week 1: QUBO Fundamentals
- Day 1: Steps 1.1-1.2 (Direct solver + generator)
- Day 2: Step 2.1 (LPU on uniform QUBOs)
- Day 3: Steps 2.2-2.3 (Sparse and high-variance)

### Week 2: Comparisons
- Day 1: Step 3.1-3.2 (Classical heuristics)
- Day 2: Step 3.3 (Full comparison)
- Day 3: Steps 4.1-4.2 (Simple knapsacks)

### Week 3: Analysis
- Day 1: Step 4.3 (Real knapsacks)
- Day 2: Steps 5.1-5.3 (Find breaking points)
- Day 3: Steps 6.1-6.2 (Root cause)

### Week 4: Conclusions
- Day 1: Step 7.1-7.3 (Documentation)

---

## Success Criteria

### Minimum Success:
- ✅ Understand where LPU works and where it doesn't
- ✅ Identify exact breaking point (variance, size)
- ✅ Document findings clearly

### Strong Success:
- ✅ Find mitigation strategies that expand operating region
- ✅ Make LPU work for our knapsack problem
- ✅ Achieve competitive performance vs classical

### Exceptional Success:
- ✅ LPU beats classical heuristics in its operating region
- ✅ Hybrid approach beats all pure approaches
- ✅ Clear guidelines for future LPU applications

---

## Current Status

**Ready to begin Phase 1, Step 1.1**

**Estimated time:** 
- Quick version (just Phase 1-2): 2-3 hours
- Full systematic analysis: 1-2 weeks

**Immediate next step:** Create direct QUBO solver for validation

---

## Notes

- Keep all test results in structured format
- Generate plots for visualization
- Document every finding
- Be ready to pivot based on discoveries

**Let's start with Phase 1, Step 1.1!**

