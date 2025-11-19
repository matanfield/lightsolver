#!/usr/bin/env python3
"""
Find the actual emulator limit by binary search.
"""

import time
import json
import numpy as np
from laser_mind_client import LaserMind
from lightsolver_lib.lightsolver_lib import probmat_qubo_to_ising, coupling_matrix_xy, XYModelParams

CAPACITY = 30_000_000

# Load full dataset
with open('../rbuilder/knapsack_instance_21200000.json') as f:
    data = json.load(f)

items = data['items']
all_profits = [int(item['profit'], 16) if item['profit'].startswith('0x') else int(item['profit']) for item in items]
all_gas = [item['gas'] for item in items]

def test_size(n):
    """Test if emulator can handle n variables."""
    print(f"\nTesting n={n}...")
    
    # Take top n by profit/gas ratio
    ratios = [(i, all_profits[i]/all_gas[i] if all_gas[i] > 0 else 0) for i in range(len(all_profits))]
    ratios.sort(key=lambda x: x[1], reverse=True)
    top_indices = [ratios[i][0] for i in range(n)]
    
    profits = [all_profits[i] for i in top_indices]
    gas_costs = [all_gas[i] for i in top_indices]
    
    # Build QUBO
    Q = np.zeros((n, n))
    max_profit = max(profits)
    max_gas = max(gas_costs)
    penalty = (max_profit / max_gas) * 2
    
    for i in range(n):
        Q[i, i] = -profits[i] + penalty * (gas_costs[i]**2 - 2*CAPACITY*gas_costs[i])
    for i in range(n):
        for j in range(i+1, n):
            Q[i, j] = 2 * penalty * gas_costs[i] * gas_costs[j]
    
    # Normalize
    Q_max = np.max(np.abs(Q))
    Q_norm = Q / Q_max
    
    # Convert
    I, offset = probmat_qubo_to_ising(Q_norm)
    coupling_matrix = coupling_matrix_xy(I, XYModelParams())
    
    # Validate
    row_sums = np.abs(coupling_matrix).sum(axis=0)
    is_valid = (row_sums < 1).all()
    max_sum = np.max(row_sums)
    
    if not is_valid:
        print(f"  ❌ Coupling matrix invalid (max row sum: {max_sum:.4f})")
        return False, "coupling_matrix_invalid"
    
    print(f"  ✓ Coupling matrix valid (max row sum: {max_sum:.4f})")
    
    # Try to solve
    try:
        token_file = "laser-mind-client/examples/lightsolver-token.txt"
        lsClient = LaserMind(pathToRefreshTokenFile=token_file, logToConsole=False)
        
        start = time.time()
        res = lsClient.solve_coupling_matrix_sim_lpu(
            matrix_data=coupling_matrix.astype(np.complex64),
            num_runs=5,  # Fewer runs for speed
            num_iterations=500,  # Fewer iterations for speed
            rounds_per_record=100,  # Less recording for speed
            timeout=60
        )
        elapsed = time.time() - start
        
        print(f"  ✅ SUCCESS in {elapsed:.2f}s")
        return True, None
        
    except Exception as e:
        error_msg = str(e)
        print(f"  ❌ FAILED: {error_msg}")
        return False, error_msg

# Binary search for limit
print("="*80)
print("FINDING EMULATOR SIZE LIMIT")
print("="*80)

# Test a few specific sizes
test_sizes = [50, 100, 200, 500, 1000, 1500, 2000]

results = {}
for size in test_sizes:
    if size > len(items):
        break
    success, error = test_size(size)
    results[size] = (success, error)
    
    if not success:
        print(f"\n⚠️  Failed at n={size}")
        if "coupling_matrix_invalid" in str(error):
            print("Issue: Coupling matrix constraint violated")
            print("This means the problem structure doesn't fit XY model well")
        break

print("\n" + "="*80)
print("RESULTS")
print("="*80)
for size, (success, error) in results.items():
    status = "✅ PASS" if success else f"❌ FAIL ({error})"
    print(f"n={size:4d}: {status}")

