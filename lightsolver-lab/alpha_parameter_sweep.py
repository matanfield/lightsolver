#!/usr/bin/env python3
"""
Alpha parameter sweep to find optimal penalty.

Current: α = 2 × (max_profit / max_gas)
Test: α / 1, α / 10, α / 100, α / 1000, etc.
"""

import json
import numpy as np
from laser_mind_client import LaserMind
from lightsolver_lib.lightsolver_lib import probmat_qubo_to_ising, coupling_matrix_xy, XYModelParams

CAPACITY = 30_000_000

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

def solve_with_emulator(Q, token_file):
    """Solve QUBO using emulator."""
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
        max_sum = np.max(row_sums)
        return None, f"Coupling matrix invalid (max row sum: {max_sum:.4f})"
    
    # Solve
    try:
        lsClient = LaserMind(pathToRefreshTokenFile=token_file, logToConsole=False)
        
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
        
        return best_solution, None
        
    except Exception as e:
        return None, str(e)

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

# Main test
print("="*80)
print("ALPHA PARAMETER SWEEP")
print("="*80)

# Load data
json_path = '../rbuilder/knapsack_instance_21200000.json'
token_file = 'laser-mind-client/examples/lightsolver-token.txt'

# Test with different problem sizes
for n in [100, 200, 500, 1000, 1500, 2000]:
    print(f"\n{'='*80}")
    print(f"TESTING n={n}")
    print(f"{'='*80}")
    
    try:
        tx_ids, profits, gas_costs = load_knapsack(json_path, max_items=n)
        
        # Calculate baseline alpha
        max_profit = max(profits)
        max_gas = max(gas_costs)
        base_alpha = 2 * (max_profit / max_gas)
        
        print(f"Problem size: {n}")
        print(f"Max profit: {max_profit:.2e} wei")
        print(f"Max gas: {max_gas}")
        print(f"Base alpha (2×max_profit/max_gas): {base_alpha:.2e}")
        
        # Alpha values to test (base / 1, 10, 100, 1000, ...)
        alpha_divisors = [1, 10, 100, 1000, 10000, 100000]
        
        # Greedy baseline
        print(f"\nGreedy baseline:")
        greedy_sol = greedy_knapsack(profits, gas_costs, CAPACITY)
        greedy_metrics = evaluate(greedy_sol, profits, gas_costs, CAPACITY)
        print(f"  Profit: {greedy_metrics['total_profit_eth']:.6f} ETH")
        print(f"  Gas: {greedy_metrics['gas_utilization']*100:.1f}%")
        print(f"  Txs: {greedy_metrics['num_selected']}")
        
        print(f"\nLPU with different alpha values:")
        print(f"{'Alpha Divisor':<15} {'Alpha Value':<15} {'Profit (ETH)':<15} {'Gas %':<10} {'Txs':<8} {'vs Greedy':<12} {'Status'}")
        print("-"*95)
        
        for divisor in alpha_divisors:
            alpha = base_alpha / divisor
            
            # Build QUBO
            Q, offset = knapsack_to_qubo(profits, gas_costs, CAPACITY, alpha)
            
            # Solve
            solution, error = solve_with_emulator(Q, token_file)
            
            if error:
                print(f"{divisor:<15} {alpha:<15.2e} {'ERROR':<15} {'':<10} {'':<8} {'':<12} {error[:30]}")
                if "Internal" in error or "Exception" in error:
                    print(f"\n⚠️  Server error at n={n}, stopping size tests.")
                    break
                continue
            
            # Evaluate
            lpu_metrics = evaluate(solution, profits, gas_costs, CAPACITY)
            diff_pct = (lpu_metrics['total_profit'] - greedy_metrics['total_profit']) / greedy_metrics['total_profit'] * 100
            
            winner = "🎉 LPU" if diff_pct > 0 else "Greedy"
            
            print(f"{divisor:<15} {alpha:<15.2e} {lpu_metrics['total_profit_eth']:<15.6f} "
                  f"{lpu_metrics['gas_utilization']*100:<10.1f} {lpu_metrics['num_selected']:<8} "
                  f"{diff_pct:>+10.1f}% {winner}")
        
        # If we got here without server error, try next size
        if n < 2000:
            print(f"\n✅ n={n} works! Trying larger size...")
        
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
        break
    except Exception as e:
        print(f"\n❌ Error at n={n}: {e}")
        break

print("\n" + "="*80)
print("SWEEP COMPLETE")
print("="*80)

