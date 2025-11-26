#!/usr/bin/env python3
"""
Quick focused test: n=75 (all profitable) with different alphas.
This should be fast and tell us if alpha tuning works.
"""

import json
import numpy as np
from laser_mind_client import LaserMind
from lightsolver_lib.lightsolver_lib import probmat_qubo_to_ising, coupling_matrix_xy, XYModelParams

CAPACITY = 30_000_000
TOKEN_FILE = 'laser-mind-client/examples/lightsolver-token.txt'

def load_knapsack(json_path):
    """Load and parse knapsack data."""
    with open(json_path) as f:
        data = json.load(f)
    
    items = data['items']
    profits = []
    gas_costs = []
    
    for item in items:
        profit_hex = item['profit']
        profit = int(profit_hex, 16) if profit_hex.startswith('0x') else int(profit_hex)
        profits.append(profit)
        gas_costs.append(item['gas'])
    
    return profits, gas_costs

def knapsack_to_qubo(profits, gas_costs, capacity, penalty):
    """Convert knapsack to QUBO."""
    n = len(profits)
    Q = np.zeros((n, n))
    
    for i in range(n):
        Q[i, i] = -profits[i] + penalty * (gas_costs[i]**2 - 2*capacity*gas_costs[i])
    
    for i in range(n):
        for j in range(i+1, n):
            Q[i, j] = 2 * penalty * gas_costs[i] * gas_costs[j]
    
    return Q

def solve_with_emulator(Q):
    """Solve QUBO using emulator."""
    print(f"    Converting to coupling matrix...", end=" ", flush=True)
    
    # Normalize
    Q_max = np.max(np.abs(Q))
    Q_norm = Q / Q_max if Q_max > 0 else Q
    
    # Convert to Ising
    I, offset_ising = probmat_qubo_to_ising(Q_norm)
    
    # Coupling matrix
    coupling_matrix = coupling_matrix_xy(I, XYModelParams())
    
    # Validate
    row_sums = np.abs(coupling_matrix).sum(axis=0)
    is_valid = (row_sums < 1).all()
    
    if not is_valid:
        print(f"INVALID (max sum: {np.max(row_sums):.4f})")
        return None, "Invalid coupling matrix"
    
    print("OK", flush=True)
    print(f"    Sending to emulator...", end=" ", flush=True)
    
    try:
        lsClient = LaserMind(pathToRefreshTokenFile=TOKEN_FILE, logToConsole=False)
        
        res = lsClient.solve_coupling_matrix_sim_lpu(
            matrix_data=coupling_matrix.astype(np.complex64),
            num_runs=10,
            num_iterations=1000,
            rounds_per_record=1
        )
        
        print("DONE", flush=True)
        
        # Extract solution
        record_states = res['data']['result']['record_states']
        num_runs = record_states.shape[1]
        
        best_solution = None
        best_energy = float('inf')
        
        for run_idx in range(num_runs):
            final_state = record_states[-1, run_idx, :]
            phases = np.angle(final_state)
            ising_state = np.where(phases >= 0, 1, -1)
            energy = np.dot(ising_state, np.dot(I, ising_state))
            
            if energy < best_energy:
                best_energy = energy
                best_solution = ((ising_state + 1) // 2).astype(int)
        
        return best_solution, None
        
    except Exception as e:
        print(f"ERROR: {str(e)[:50]}", flush=True)
        return None, str(e)

# Load data
print("="*80)
print("QUICK ALPHA TEST: n=75 (ALL PROFITABLE TRANSACTIONS)")
print("="*80)

json_path = '../rbuilder/knapsack_instance_21200000.json'
all_profits, all_gas_costs = load_knapsack(json_path)

# Get profitable indices
profitable_indices = [i for i, p in enumerate(all_profits) if p > 0]
print(f"\nTotal transactions: {len(all_profits)}")
print(f"Profitable: {len(profitable_indices)}")

# Extract profitable subset
profits = [all_profits[i] for i in profitable_indices]
gas_costs = [all_gas_costs[i] for i in profitable_indices]

total_profit = sum(profits)
total_gas = sum(gas_costs)

print(f"Total profit: {total_profit/1e18:.6f} ETH")
print(f"Total gas: {total_gas:,} ({total_gas/CAPACITY*100:.1f}% of capacity)")
print(f"\nOptimal solution: Select all 75 (total profit: {total_profit/1e18:.6f} ETH)")

# Calculate base alpha
max_profit = max(profits)
max_gas = max(gas_costs)
base_alpha = 2 * (max_profit / max_gas)
print(f"\nBase alpha: {base_alpha:.2e}")

# Test different alphas
print(f"\n{'='*80}")
print("TESTING DIFFERENT ALPHA VALUES")
print("="*80)
print(f"{'Divisor':<10} {'Alpha':<15} {'Selected':<10} {'Profit (ETH)':<15} {'Gas %':<10} {'Status'}")
print("-"*80)

for divisor in [1, 100, 10000, 1000000]:
    alpha = base_alpha / divisor
    print(f"{divisor:<10} {alpha:<15.2e} ", end="", flush=True)
    
    # Build QUBO
    Q = knapsack_to_qubo(profits, gas_costs, CAPACITY, alpha)
    
    # Solve
    solution, error = solve_with_emulator(Q)
    
    if error:
        print(f"{'ERROR':<10} {'':<15} {'':<10} {error[:30]}")
        continue
    
    # Evaluate
    selected = np.where(solution == 1)[0]
    total_profit_selected = sum(profits[i] for i in selected)
    total_gas_selected = sum(gas_costs[i] for i in selected)
    
    status = "✅ PERFECT!" if len(selected) == 75 else "❌ Suboptimal"
    
    print(f"{len(selected):<10} {total_profit_selected/1e18:<15.6f} "
          f"{total_gas_selected/CAPACITY*100:<10.1f} {status}")

print(f"\n{'='*80}")
print("TEST COMPLETE")
print("="*80)
print("\nExpected: With correct alpha, LPU should select all 75 transactions")
print("If not, there's a deeper issue beyond just the penalty parameter.")


