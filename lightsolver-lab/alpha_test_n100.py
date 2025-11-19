#!/usr/bin/env python3
"""Quick alpha test on n=100 to show immediate impact."""
import json
import numpy as np
from laser_mind_client import LaserMind
from lightsolver_lib.lightsolver_lib import probmat_qubo_to_ising, coupling_matrix_xy, XYModelParams

CAPACITY = 30_000_000
token_file = 'laser-mind-client/examples/lightsolver-token.txt'

# Load n=100 (FIRST 100, not filtered by greedy)
with open('../rbuilder/knapsack_instance_21200000.json') as f:
    data = json.load(f)
items = data['items'][:100]
profits = [int(item['profit'], 16) if item['profit'].startswith('0x') else int(item['profit']) for item in items]
gas_costs = [item['gas'] for item in items]
n = 100

print("="*80)
print(f"ALPHA PARAMETER TEST (n={n}, FIRST 100 transactions)")
print("="*80)

# Greedy baseline
ratios = [(i, profits[i]/gas_costs[i] if gas_costs[i] > 0 else 0) for i in range(n)]
ratios.sort(key=lambda x: x[1], reverse=True)
greedy_sol = np.zeros(n, dtype=int)
total_gas = 0
for idx, _ in ratios:
    if total_gas + gas_costs[idx] <= CAPACITY:
        greedy_sol[idx] = 1
        total_gas += gas_costs[idx]
greedy_profit = sum(profits[i] * greedy_sol[i] for i in range(n))
greedy_gas = sum(gas_costs[i] * greedy_sol[i] for i in range(n))

print(f"\nGreedy baseline: {greedy_profit/1e18:.6f} ETH, {greedy_gas/CAPACITY*100:.1f}% gas")

# Base alpha
base_alpha = 2 * (max(profits) / max(gas_costs))
print(f"Base alpha: {base_alpha:.2e}")
print()

# Test different alphas
print(f"{'Divisor':<10} {'Alpha':<15} {'LPU Profit (ETH)':<18} {'Gas %':<10} {'vs Greedy':<12} {'Winner'}")
print("-"*80)

for divisor in [1, 10, 100, 1000, 10000, 100000]:
    alpha = base_alpha / divisor
    
    try:
        # Build QUBO
        Q = np.zeros((n, n))
        for i in range(n):
            Q[i, i] = -profits[i] + alpha * (gas_costs[i]**2 - 2*CAPACITY*gas_costs[i])
        for i in range(n):
            for j in range(i+1, n):
                Q[i, j] = 2 * alpha * gas_costs[i] * gas_costs[j]
        
        # Normalize and convert
        Q_max = np.max(np.abs(Q))
        Q_norm = Q / Q_max
        I, _ = probmat_qubo_to_ising(Q_norm)
        coupling = coupling_matrix_xy(I, XYModelParams())
        
        # Validate
        row_sums = np.abs(coupling).sum(axis=0)
        if not (row_sums < 1).all():
            print(f"{divisor:<10} {alpha:<15.2e} {'INVALID':<18} {'N/A':<10} {'N/A':<12} Coupling matrix failed")
            continue
        
        # Solve
        lsClient = LaserMind(pathToRefreshTokenFile=token_file, logToConsole=False)
        res = lsClient.solve_coupling_matrix_sim_lpu(
            matrix_data=coupling.astype(np.complex64),
            num_runs=5,
            num_iterations=500,
            rounds_per_record=100
        )
        
        # Extract solution
        record_states = res['data']['result']['record_states']
        best_sol = None
        best_e = float('inf')
        for run in range(record_states.shape[1]):
            final = record_states[-1, run, :]
            phases = np.angle(final)
            ising = np.where(phases >= 0, 1, -1)
            e = np.dot(ising, np.dot(I, ising))
            if e < best_e:
                best_e = e
                best_sol = ((ising + 1) // 2).astype(int)
        
        lpu_profit = sum(profits[i] * best_sol[i] for i in range(n))
        lpu_gas = sum(gas_costs[i] * best_sol[i] for i in range(n))
        diff_pct = (lpu_profit - greedy_profit) / greedy_profit * 100
        
        winner = "🎉 LPU WINS" if diff_pct > 0 else "Greedy"
        
        print(f"{divisor:<10} {alpha:<15.2e} {lpu_profit/1e18:<18.6f} {lpu_gas/CAPACITY*100:<10.1f} {diff_pct:>+10.1f}% {winner}")
        
    except Exception as e:
        print(f"{divisor:<10} {alpha:<15.2e} ERROR: {str(e)[:30]}")

print("="*80)

