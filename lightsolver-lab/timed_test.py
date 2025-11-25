#!/usr/bin/env python3
"""
Test with detailed timing to show where time is spent.
"""

import json
import numpy as np
import time
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

print("="*80)
print("TIMING BREAKDOWN TEST")
print("="*80)

# Load data
t0 = time.time()
json_path = '../rbuilder/knapsack_instance_21200000.json'
all_profits, all_gas_costs = load_knapsack(json_path)
t_load = time.time() - t0

# Get profitable subset (n=75)
t0 = time.time()
profitable_indices = [i for i, p in enumerate(all_profits) if p > 0]
profits = [all_profits[i] for i in profitable_indices]
gas_costs = [all_gas_costs[i] for i in profitable_indices]
t_filter = time.time() - t0

print(f"\n1. Load JSON:        {t_load*1000:.1f} ms")
print(f"2. Filter data:      {t_filter*1000:.1f} ms")
print(f"   Problem size: n={len(profits)}")

# Build QUBO
t0 = time.time()
max_profit = max(profits)
max_gas = max(gas_costs)
alpha = 2 * (max_profit / max_gas) / 10000  # Use divisor=10000
n = len(profits)
Q = np.zeros((n, n))
for i in range(n):
    Q[i, i] = -profits[i] + alpha * (gas_costs[i]**2 - 2*CAPACITY*gas_costs[i])
for i in range(n):
    for j in range(i+1, n):
        Q[i, j] = 2 * alpha * gas_costs[i] * gas_costs[j]
t_qubo = time.time() - t0

print(f"3. Build QUBO:       {t_qubo*1000:.1f} ms")

# Normalize
t0 = time.time()
Q_max = np.max(np.abs(Q))
Q_norm = Q / Q_max if Q_max > 0 else Q
t_norm = time.time() - t0

print(f"4. Normalize:        {t_norm*1000:.1f} ms")

# QUBO to Ising
t0 = time.time()
I, offset_ising = probmat_qubo_to_ising(Q_norm)
t_ising = time.time() - t0

print(f"5. QUBO→Ising:       {t_ising*1000:.1f} ms")

# Coupling matrix
t0 = time.time()
coupling_matrix = coupling_matrix_xy(I, XYModelParams())
t_coupling = time.time() - t0

print(f"6. Coupling matrix:  {t_coupling*1000:.1f} ms")

# Validate
t0 = time.time()
row_sums = np.abs(coupling_matrix).sum(axis=0)
is_valid = (row_sums < 1).all()
t_validate = time.time() - t0

print(f"7. Validate:         {t_validate*1000:.1f} ms")

total_local = t_load + t_filter + t_qubo + t_norm + t_ising + t_coupling + t_validate
print(f"\n{'='*80}")
print(f"TOTAL LOCAL TIME:    {total_local*1000:.1f} ms ← THIS IS MILLISECONDS!")
print(f"{'='*80}")

if not is_valid:
    print(f"\n❌ Coupling matrix invalid (max row sum: {np.max(row_sums):.4f})")
    exit(1)

# Now the slow part: API call
print(f"\n8. Sending to LPU emulator API...")
print(f"   (This will take 3-8 seconds due to network + queue + server)")

t0 = time.time()
try:
    lsClient = LaserMind(pathToRefreshTokenFile=TOKEN_FILE, logToConsole=False)
    
    res = lsClient.solve_coupling_matrix_sim_lpu(
        matrix_data=coupling_matrix.astype(np.complex64),
        num_runs=10,
        num_iterations=1000,
        rounds_per_record=1
    )
    
    t_api = time.time() - t0
    print(f"   ✓ API call completed: {t_api:.1f} seconds")
    
    # Extract solution
    t0 = time.time()
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
    
    t_extract = time.time() - t0
    print(f"9. Extract solution: {t_extract*1000:.1f} ms")
    
    # Evaluate
    selected = np.where(best_solution == 1)[0]
    total_profit_selected = sum(profits[i] for i in selected)
    total_gas_selected = sum(gas_costs[i] for i in selected)
    
    print(f"\n{'='*80}")
    print(f"TIMING SUMMARY")
    print(f"{'='*80}")
    print(f"Local computation:   {total_local*1000:.1f} ms ({total_local/(total_local+t_api)*100:.1f}%)")
    print(f"API + Network:       {t_api:.1f} seconds ({t_api/(total_local+t_api)*100:.1f}%)")
    print(f"TOTAL:               {total_local+t_api:.1f} seconds")
    
    print(f"\n{'='*80}")
    print(f"RESULT")
    print(f"{'='*80}")
    print(f"Selected: {len(selected)}/75 transactions")
    print(f"Profit: {total_profit_selected/1e18:.6f} ETH")
    print(f"Gas: {total_gas_selected/CAPACITY*100:.1f}%")
    print(f"Status: {'✅ PERFECT!' if len(selected) == 75 else '❌ Suboptimal'}")
    
except Exception as e:
    t_api = time.time() - t0
    print(f"   ❌ Error after {t_api:.1f} seconds: {str(e)[:100]}")

print(f"\n{'='*80}")
print(f"CONCLUSION")
print(f"{'='*80}")
print(f"The LOCAL computation IS fast (~{total_local*1000:.0f}ms).")
print(f"The SLOW part is the cloud API (network + queue + server).")
print(f"This is unavoidable with a cloud-based service.")
print(f"{'='*80}")

