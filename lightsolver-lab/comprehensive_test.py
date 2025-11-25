#!/usr/bin/env python3
"""
Comprehensive test suite addressing all issues:
1. Alpha parameter sweep
2. Test on n=75 (all profitable) - should select all
3. Test on n=200 (75 profitable + 125 zeros) - test discrimination
4. Test with and without normalization
5. Push emulator limit (250, 300)
"""

import json
import numpy as np
import sys
from laser_mind_client import LaserMind
from lightsolver_lib.lightsolver_lib import probmat_qubo_to_ising, coupling_matrix_xy, XYModelParams

CAPACITY = 30_000_000
TOKEN_FILE = 'laser-mind-client/examples/lightsolver-token.txt'

def load_knapsack(json_path, max_items=None):
    """Load and parse knapsack data."""
    with open(json_path) as f:
        data = json.load(f)
    
    items = data['items']
    if max_items:
        items = items[:max_items]
    
    profits = []
    gas_costs = []
    tx_ids = []
    
    for item in items:
        tx_ids.append(item['id'])
        profit_hex = item['profit']
        profit = int(profit_hex, 16) if profit_hex.startswith('0x') else int(profit_hex)
        profits.append(profit)
        gas_costs.append(item['gas'])
    
    return tx_ids, profits, gas_costs

def get_profitable_indices(profits):
    """Get indices of profitable transactions."""
    return [i for i, p in enumerate(profits) if p > 0]

def knapsack_to_qubo(profits, gas_costs, capacity, penalty):
    """Convert knapsack to QUBO with given penalty."""
    n = len(profits)
    Q = np.zeros((n, n))
    
    # Diagonal terms
    for i in range(n):
        Q[i, i] = -profits[i] + penalty * (gas_costs[i]**2 - 2*capacity*gas_costs[i])
    
    # Off-diagonal
    for i in range(n):
        for j in range(i+1, n):
            Q[i, j] = 2 * penalty * gas_costs[i] * gas_costs[j]
    
    offset = penalty * capacity**2
    return Q, offset

def solve_with_emulator(Q, normalize=True):
    """Solve QUBO using emulator."""
    # Normalize if requested
    if normalize:
        Q_max = np.max(np.abs(Q))
        Q_work = Q / Q_max if Q_max > 0 else Q
        norm_factor = Q_max
    else:
        Q_work = Q
        norm_factor = 1.0
    
    # Convert to Ising
    I, offset_ising = probmat_qubo_to_ising(Q_work)
    
    # Coupling matrix
    coupling_matrix = coupling_matrix_xy(I, XYModelParams())
    
    # Validate
    row_sums = np.abs(coupling_matrix).sum(axis=0)
    max_sum = np.max(row_sums)
    is_valid = (row_sums < 1).all()
    
    if not is_valid:
        return None, f"Coupling matrix invalid (max row sum: {max_sum:.4f})", None
    
    # Solve
    try:
        lsClient = LaserMind(pathToRefreshTokenFile=TOKEN_FILE, logToConsole=False)
        
        res = lsClient.solve_coupling_matrix_sim_lpu(
            matrix_data=coupling_matrix.astype(np.complex64),
            num_runs=10,
            num_iterations=1000,
            rounds_per_record=1
        )
        
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
        
        return best_solution, None, {'max_row_sum': max_sum, 'normalized': normalize, 'norm_factor': norm_factor}
        
    except Exception as e:
        return None, str(e), None

def evaluate(solution, profits, gas_costs, capacity):
    """Evaluate solution."""
    selected = np.where(solution == 1)[0]
    total_profit = sum(profits[i] for i in selected)
    total_gas = sum(gas_costs[i] for i in selected)
    
    return {
        'num_selected': len(selected),
        'total_profit': total_profit,
        'total_profit_eth': total_profit / 1e18,
        'total_gas': total_gas,
        'gas_utilization': total_gas / capacity,
        'constraint_satisfied': total_gas <= capacity,
    }

def greedy_knapsack(profits, gas_costs, capacity):
    """Greedy baseline."""
    n = len(profits)
    items = [(i, profits[i]/gas_costs[i] if gas_costs[i] > 0 else 0) for i in range(n)]
    items.sort(key=lambda x: x[1], reverse=True)
    
    solution = np.zeros(n, dtype=int)
    total_gas = 0
    
    for idx, ratio in items:
        if total_gas + gas_costs[idx] <= capacity:
            solution[idx] = 1
            total_gas += gas_costs[idx]
    
    return solution

# Load data
print("="*80)
print("COMPREHENSIVE LPU TEST SUITE")
print("="*80)

json_path = '../rbuilder/knapsack_instance_21200000.json'
print(f"\nLoading: {json_path}")
all_tx_ids, all_profits, all_gas_costs = load_knapsack(json_path)

profitable_indices = get_profitable_indices(all_profits)
print(f"Total transactions: {len(all_profits)}")
print(f"Profitable: {len(profitable_indices)} (use only {sum(all_gas_costs[i] for i in profitable_indices):,} gas)")

# Calculate baseline alpha
max_profit = max(all_profits)
max_gas = max(all_gas_costs)
base_alpha = 2 * (max_profit / max_gas)
print(f"\nBase alpha: {base_alpha:.2e}")

# Test configurations
tests = []

# Test 1: n=75 (all profitable) with various alphas
print(f"\n{'='*80}")
print("TEST 1: n=75 (ALL PROFITABLE TRANSACTIONS)")
print("="*80)
print("Optimal solution: Select all 75 (trivial test)")

profitable_profits = [all_profits[i] for i in profitable_indices]
profitable_gas = [all_gas_costs[i] for i in profitable_indices]
profitable_ids = [all_tx_ids[i] for i in profitable_indices]

# Greedy baseline on 75
greedy_sol = greedy_knapsack(profitable_profits, profitable_gas, CAPACITY)
greedy_metrics = evaluate(greedy_sol, profitable_profits, profitable_gas, CAPACITY)
print(f"\nGreedy (should select all 75):")
print(f"  Selected: {greedy_metrics['num_selected']}/75")
print(f"  Profit: {greedy_metrics['total_profit_eth']:.6f} ETH")
print(f"  Gas: {greedy_metrics['gas_utilization']*100:.1f}%")

# Test with different alphas
alpha_divisors = [1, 100, 10000, 1000000]
print(f"\nLPU with different alphas:")
print(f"{'Alpha':<15} {'Norm':<6} {'Selected':<10} {'Profit (ETH)':<15} {'Gas %':<10} {'Status'}")
print("-"*80)

for divisor in alpha_divisors:
    alpha = base_alpha / divisor
    
    for normalize in [True, False]:
        Q, offset = knapsack_to_qubo(profitable_profits, profitable_gas, CAPACITY, alpha)
        solution, error, info = solve_with_emulator(Q, normalize=normalize)
        
        if error:
            print(f"{alpha:<15.2e} {str(normalize):<6} {'ERROR':<10} {'':<15} {'':<10} {error[:30]}")
            continue
        
        metrics = evaluate(solution, profitable_profits, profitable_gas, CAPACITY)
        norm_str = "Yes" if normalize else "No"
        
        print(f"{alpha:<15.2e} {norm_str:<6} {metrics['num_selected']:<10} "
              f"{metrics['total_profit_eth']:<15.6f} {metrics['gas_utilization']*100:<10.1f} "
              f"{'✅' if metrics['num_selected'] == 75 else '❌'}")

# Test 2: n=200 (75 profitable + 125 zeros)
print(f"\n{'='*80}")
print("TEST 2: n=200 (75 PROFITABLE + 125 ZEROS)")
print("="*80)
print("Test: Can LPU discriminate and select only profitable?")

test_200_profits = all_profits[:200]
test_200_gas = all_gas_costs[:200]
test_200_ids = all_tx_ids[:200]

# Count profitable in first 200
profitable_in_200 = sum(1 for p in test_200_profits if p > 0)
print(f"Profitable in first 200: {profitable_in_200}")

# Greedy baseline
greedy_sol_200 = greedy_knapsack(test_200_profits, test_200_gas, CAPACITY)
greedy_metrics_200 = evaluate(greedy_sol_200, test_200_profits, test_200_gas, CAPACITY)
print(f"\nGreedy on n=200:")
print(f"  Selected: {greedy_metrics_200['num_selected']}")
print(f"  Profit: {greedy_metrics_200['total_profit_eth']:.6f} ETH")
print(f"  Gas: {greedy_metrics_200['gas_utilization']*100:.1f}%")

# LPU with best alpha from test 1
print(f"\nLPU on n=200:")
print(f"{'Alpha':<15} {'Norm':<6} {'Selected':<10} {'Profit (ETH)':<15} {'Gas %':<10} {'vs Greedy'}")
print("-"*80)

for divisor in [10000, 100000, 1000000]:
    alpha = base_alpha / divisor
    
    for normalize in [True, False]:
        Q, offset = knapsack_to_qubo(test_200_profits, test_200_gas, CAPACITY, alpha)
        solution, error, info = solve_with_emulator(Q, normalize=normalize)
        
        if error:
            print(f"{alpha:<15.2e} {str(normalize):<6} {'ERROR':<10} {'':<15} {'':<10} {error[:30]}")
            continue
        
        metrics = evaluate(solution, test_200_profits, test_200_gas, CAPACITY)
        diff_pct = (metrics['total_profit'] - greedy_metrics_200['total_profit']) / greedy_metrics_200['total_profit'] * 100
        norm_str = "Yes" if normalize else "No"
        
        print(f"{alpha:<15.2e} {norm_str:<6} {metrics['num_selected']:<10} "
              f"{metrics['total_profit_eth']:<15.6f} {metrics['gas_utilization']*100:<10.1f} "
              f"{diff_pct:>+9.1f}%")

# Test 3: Push emulator limit
print(f"\n{'='*80}")
print("TEST 3: EMULATOR SIZE LIMIT")
print("="*80)

for n in [250, 300]:
    print(f"\nTesting n={n}...")
    test_profits = all_profits[:n]
    test_gas = all_gas_costs[:n]
    
    # Use middle-range alpha
    alpha = base_alpha / 10000
    
    Q, offset = knapsack_to_qubo(test_profits, test_gas, CAPACITY, alpha)
    solution, error, info = solve_with_emulator(Q, normalize=True)
    
    if error:
        print(f"  ❌ n={n} FAILED: {error}")
        if "Internal" in error:
            print(f"  → Emulator limit appears to be < {n}")
            break
    else:
        metrics = evaluate(solution, test_profits, test_gas, CAPACITY)
        print(f"  ✅ n={n} WORKS!")
        print(f"     Selected: {metrics['num_selected']}")
        print(f"     Profit: {metrics['total_profit_eth']:.6f} ETH")
        print(f"     Gas: {metrics['gas_utilization']*100:.1f}%")

print(f"\n{'='*80}")
print("TEST SUITE COMPLETE")
print("="*80)

