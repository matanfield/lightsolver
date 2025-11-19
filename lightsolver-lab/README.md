# LightSolver Lab - Knapsack to QUBO to LPU Solver

This directory contains scripts to solve knapsack problems (transaction selection for blockchain blocks) using LightSolver's LPU (Laser Processing Unit) via QUBO formulation.

## Setup

### Two Python Environments

Due to package compatibility requirements, we maintain two separate Python environments:

1. **Python 3.12** for LPU Lab (laser-mind-client)
   - Location: `laser-mind-client/.venv/`
   - Used for: LightSolver LPU client and examples
   
2. **Python 3.9** for pyqubo (optional)
   - Location: `.venv-py39/`
   - Used for: pyqubo library (alternative QUBO formulation tool)

## Scripts

### 1. `knapsack_lpu_solver.py`

**Main workflow script** that performs end-to-end knapsack solving via LPU.

**What it does:**
1. Loads knapsack instance JSON (real Ethereum block data)
2. Pre-filters to top N transactions by profit/gas ratio (LPU constraint: ~10-20 variables max)
3. Converts knapsack to QUBO matrix formulation
4. Sends QUBO to LightSolver LPU for solving
5. Converts LPU solution back to transaction list
6. Compares with greedy knapsack algorithm
7. Saves detailed results

**Usage:**
```bash
# Using Python 3.12 environment
cd lightsolver-lab
../laser-mind-client/.venv/bin/python knapsack_lpu_solver.py <knapsack.json> [max_variables]

# Examples:
../laser-mind-client/.venv/bin/python knapsack_lpu_solver.py ../rbuilder/knapsack_instance_21200000.json 10
../laser-mind-client/.venv/bin/python knapsack_lpu_solver.py ../rbuilder/knapsack_instance_21200000.json 20
```

**Parameters:**
- `knapsack.json`: Path to knapsack instance JSON file
- `max_variables`: Maximum number of variables for LPU (default: 20, recommended: 10-20)

**Output:**
- Console: Detailed progress and comparison results
- File: `knapsack_instance_*_lpu_results.json` - JSON with full results

### 2. `batch_solve_knapsacks.py`

**Batch processor** for solving multiple knapsack instances.

**Usage:**
```bash
# Process all knapsack JSONs in a directory
../laser-mind-client/.venv/bin/python batch_solve_knapsacks.py ../rbuilder/

# Process specific pattern
../laser-mind-client/.venv/bin/python batch_solve_knapsacks.py ../rbuilder/knapsack_instance_*.json
```

**Output:**
- Console: Progress for each instance + aggregate summary
- File: `batch_lpu_results_summary.json` - Aggregate comparison across all instances

### 3. `knapsack_to_qubo.py`

**Direct mathematical QUBO conversion** without external libraries.

Converts knapsack problem to QUBO using the mathematical formulation:
```
Minimize: Q^T x Q where
Q[i,i] = -profit[i] + α(w[i]² - 2Ww[i])
Q[i,j] = 2αw[i]w[j]
```

**Usage:**
```bash
python knapsack_to_qubo.py
```

### 4. `knapsack_to_qubo_pyqubo.py`

**Alternative QUBO conversion using pyqubo library** with built-in verification.

Uses symbolic Hamiltonian formulation and includes simulated annealing solver for verification.

**Requirements:** Python 3.9 (pyqubo doesn't support 3.10+)

**Usage:**
```bash
# Using Python 3.9 environment
.venv-py39/bin/python knapsack_to_qubo_pyqubo.py
```

## Input Format

Knapsack instance JSON files (e.g., `knapsack_instance_21200000.json`):

```json
{
  "block_number": 21200000,
  "items": [
    {
      "id": "tx:0xabc...",
      "profit": "0x123...",  // Hex-encoded profit in wei
      "gas": 21000,          // Gas cost
      "nonces": [["0xaddress", nonce]]
    },
    ...
  ]
}
```

- **Capacity:** Ethereum block gas limit (30,000,000)
- **Objective:** Maximize total profit while staying within gas limit

## Output Format

LPU results JSON (`*_lpu_results.json`):

```json
{
  "block_number": 21200000,
  "problem_size_original": 2005,
  "problem_size_filtered": 20,
  "lpu_solution": {
    "selected_tx_indices": [0, 2, 5, ...],
    "num_txs": 15,
    "total_profit_eth": 0.012345,
    "total_gas": 28500000,
    "gas_utilization": 0.95,
    "constraint_satisfied": true
  },
  "greedy_solution_filtered": { ... },
  "greedy_solution_full": { ... },
  "comparison": {
    "profit_difference_eth": 0.000123,
    "profit_improvement_percent": 1.5,
    "lpu_is_better": true
  }
}
```

## LPU Constraints & Limitations

### Variable Limit
- **LPU supports ~5-100 variables** (documentation says 5-100)
- **Recommended: 10-20 variables** for reliable operation
- **Hardware constraint:** Number of physical lasers in the LPU

### Workaround
Since real blocks have 1000-2000+ transactions, we:
1. Pre-filter to top N transactions by profit/gas ratio
2. Solve the filtered subset with LPU
3. Compare with greedy on both filtered and full sets

This gives us:
- **Fair comparison:** LPU vs Greedy on same subset
- **Reference baseline:** Greedy on full dataset
- **Proof of concept:** Can LPU improve over greedy on high-value transactions?

## Algorithm Comparison

### Greedy Algorithm
```python
1. Calculate profit/gas ratio for each transaction
2. Sort by ratio (descending)
3. Select transactions greedily while gas < capacity
```
- **Time:** O(n log n)
- **Quality:** Good approximation, not optimal
- **Used by:** Current rbuilder implementation

### LPU (Quantum-inspired)
```python
1. Formulate as QUBO matrix
2. Solve using laser-based optimizer
3. Returns binary solution vector
```
- **Time:** Depends on LPU processing
- **Quality:** Aims for optimal or near-optimal
- **Constraint:** Limited problem size (10-20 variables)

## Knapsack to QUBO Formulation

The 0-1 knapsack problem:
```
Maximize: Σ profit[i] × x[i]
Subject to: Σ gas[i] × x[i] ≤ capacity
Where: x[i] ∈ {0, 1}
```

Converted to QUBO (minimization):
```
Minimize: -Σ profit[i]×x[i] + α(Σ gas[i]×x[i] - capacity)²

Expanded:
Q[i,i] = -profit[i] + α(gas[i]² - 2×capacity×gas[i])
Q[i,j] = 2α × gas[i] × gas[j]  (i < j)
offset = α × capacity²
```

Where:
- **α (penalty):** Scales constraint violation cost
- **Auto-calculated:** α = 2 × (max_profit / max_gas)

## Files

- `knapsack_lpu_solver.py` - Main LPU solver with comparison
- `batch_solve_knapsacks.py` - Batch processing script
- `knapsack_to_qubo.py` - Direct QUBO converter (pure math)
- `knapsack_to_qubo_pyqubo.py` - Pyqubo-based converter with verification
- `laser-mind-client/` - LightSolver Python client library
- `.venv-py39/` - Python 3.9 environment for pyqubo

## Example Workflow

```bash
# 1. Activate LPU environment
cd lightsolver-lab

# 2. Solve single instance
../laser-mind-client/.venv/bin/python knapsack_lpu_solver.py \
  ../rbuilder/knapsack_instance_21200000.json 15

# 3. Batch solve all instances
../laser-mind-client/.venv/bin/python batch_solve_knapsacks.py \
  ../rbuilder/knapsack_instance_*.json

# 4. Check results
cat batch_lpu_results_summary.json
```

## Troubleshooting

### Connection Errors
- **Issue:** "No access to LightSolver Cloud"
- **Causes:** Network issues, API rate limits, token expiration
- **Solution:** Check network, verify token, retry later

### Matrix Size Errors
- **Issue:** "Number of variables must be between 5-100" or "greater than number of lasers"
- **Solution:** Reduce `max_variables` parameter to 10-20

### Import Errors
- **Issue:** "No module named 'laser_mind_client'"
- **Solution:** Use correct Python environment
  ```bash
  ../laser-mind-client/.venv/bin/python script.py
  ```

## Future Improvements

1. **Hierarchical approach:** LPU for high-value subset, greedy for remainder
2. **Multiple LPU calls:** Solve overlapping subsets, merge results
3. **Hybrid optimizer:** Use LPU result as starting point for local search
4. **Larger LPU:** When hardware scales to 100+ variables
5. **Different formulations:** Try alternative QUBO encodings

## References

- LightSolver LPU Documentation: [lightsolver.com](https://lightsolver.com)
- QUBO formulation for knapsack: Standard optimization literature
- rbuilder knapsack instances: Generated from real Ethereum mainnet blocks

