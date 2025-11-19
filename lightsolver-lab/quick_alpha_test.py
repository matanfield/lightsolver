#!/usr/bin/env python3
"""Quick alpha test on n=100."""
import json
import numpy as np
from laser_mind_client import LaserMind
from lightsolver_lib.lightsolver_lib import probmat_qubo_to_ising, coupling_matrix_xy, XYModelParams

CAPACITY = 30_000_000
token_file = 'laser-mind-client/examples/lightsolver-token.txt'

# Load n=100
with open('../rbuilder/knapsack_instance_21200000.json') as f:
    data = json.load(f)
items = data['items'][:100]
profits = [int(item['profit'], 16) if item['profit'].startswith('0x') else int(item['profit']) for item in items]
gas_costs = [item['gas'] for item in items]
n = 100

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

print(f"Greedy: {greedy_profit/1e18:.6f} ETH, {greedy_gas/CAPACITY*100:.1f}% gas\n")

# Base alpha
base_alpha = 2 * (max(profits) / max(gas_costs))
print(f"Base alpha: {base_alpha:.2e}\n")

# Test different alphas
for divisor in [1, 100, 10000, 1000000]:
    alpha = base_alpha / divisor
    print(f"Testing α/{divisor} = {alpha:.2e}...")
    
    # Build QUBO
    Q = np.zeros((n, n))
    for i in range(n):
        Q[i, i] = -profits[i] + alpha * (gas_costs[i]**2 - 2*CAPACITY*gas_costs[i])
    for i in range(n):
        for j in range(i+1, n):
            Q[i, j] = 2 * alpha * gas_costs[i] * gas_costs[j]
    
    # Normalize and solve
    Q_max = np.max(np.abs(Q))
    Q_norm = Q / Q_max
    I, _ = probmat_qubo_to_ising(Q_norm)
    coupling = coupling_matrix_xy(I, XYModelParams())
    
    try:
        lsClient = LaserMind(pathToRefreshTokenFile=token_file, logToConsole=False)
        res = lsClient.solve_coupling_matrix_sim_lpu(
            matrix_data=coupling.astype(np.complex64),
            num_runs=5,  # Faster
            num_iterations=500,
            rounds_per_record=100
        )
        
        # Extract
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
        diff = (lpu_profit - greedy_profit) / greedy_profit * 100
        
        print(f'  LPU: {lpu_profit/1e18:.6f} ETH, {lpu_gas/CAPACITY*100:.1f}% gas, {diff:+.1f}% vs greedy')
        
    except Exception as e:
        print(f'  ERROR: {str(e)[:50]}')
    print()
"
