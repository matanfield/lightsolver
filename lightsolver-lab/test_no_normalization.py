#!/usr/bin/env python3
"""
Test WITHOUT normalization to see if preserving magnitude information helps.
"""

import json
import numpy as np
import time
from laser_mind_client import LaserMind
from lightsolver_lib.lightsolver_lib import probmat_qubo_to_ising, coupling_matrix_xy, XYModelParams

CAPACITY = 30_000_000
TOKEN_FILE = 'laser-mind-client/.venv/bin/python'

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

# Load data
json_path = '../rbuilder/knapsack_instance_21200000.json'
with open(json_path) as f:
    data = json.load(f)

all_profits = []
all_gas_costs = []
for item in data['items']:
    profit_hex = item['profit']
    profit = int(profit_hex, 16) if profit_hex.startswith('0x') else int(profit_hex)
    all_profits.append(profit)
    all_gas_costs.append(item['gas'])

# Get profitable subset
profitable_indices = [i for i, p in enumerate(all_profits) if p > 0]
profits = [all_profits[i] for i in profitable_indices]
gas_costs = [all_gas_costs[i] for i in profitable_indices]

log("="*80)
log("TEST WITHOUT NORMALIZATION")
log("="*80)
log(f"Hypothesis: Normalization loses magnitude information")
log(f"Test: Skip Q_norm = Q / Q_max step")
log("")

# Build QUBO with best alpha from previous test
max_profit = max(profits)
max_gas = max(gas_costs)
base_alpha = 2 * (max_profit / max_gas)
alpha = base_alpha / 1  # Use divisor=1 (best from previous test)

log(f"Using alpha: {alpha:.2e}")
log(f"Building QUBO...")

n = len(profits)
Q = np.zeros((n, n))
for i in range(n):
    Q[i, i] = -profits[i] + alpha * (gas_costs[i]**2 - 2*CAPACITY*gas_costs[i])
for i in range(n):
    for j in range(i+1, n):
        Q[i, j] = 2 * alpha * gas_costs[i] * gas_costs[j]

log(f"QUBO range: {np.min(Q):.2e} to {np.max(Q):.2e}")

# WITHOUT normalization
log(f"\nConverting to Ising WITHOUT normalization...")
try:
    I, _ = probmat_qubo_to_ising(Q)  # No normalization!
    log(f"Ising range: {np.min(I):.2e} to {np.max(I):.2e}")
    
    log(f"Creating coupling matrix...")
    coupling_matrix = coupling_matrix_xy(I, XYModelParams())
    
    # Check validity
    row_sums = np.abs(coupling_matrix).sum(axis=0)
    max_sum = np.max(row_sums)
    is_valid = (row_sums < 1).all()
    
    log(f"Coupling matrix max row sum: {max_sum:.4f}")
    log(f"Valid (< 1): {is_valid}")
    
    if not is_valid:
        log(f"\n❌ INVALID! Without normalization, coupling matrix violates constraint.")
        log(f"   This is why normalization is needed.")
        log(f"   Need to adjust XY parameters or use normalization.")
    else:
        log(f"\n✅ VALID! Can proceed without normalization.")
        log(f"\nCalling emulator...")
        
        t0 = time.time()
        lsClient = LaserMind(pathToRefreshTokenFile='laser-mind-client/examples/lightsolver-token.txt', logToConsole=False)
        
        res = lsClient.solve_coupling_matrix_sim_lpu(
            matrix_data=coupling_matrix.astype(np.complex64),
            num_runs=5,
            num_iterations=500,
            rounds_per_record=1
        )
        
        elapsed = time.time() - t0
        log(f"✅ Completed in {elapsed:.1f}s")
        
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
        
        # Evaluate
        selected = np.where(best_solution == 1)[0]
        total_profit = sum(profits[i] for i in selected)
        total_gas = sum(gas_costs[i] for i in selected)
        
        log(f"\n{'='*80}")
        log("RESULTS WITHOUT NORMALIZATION")
        log(f"{'='*80}")
        log(f"Selected: {len(selected)}/75 transactions")
        log(f"Profit: {total_profit/1e18:.6f} ETH")
        log(f"Gas: {total_gas/CAPACITY*100:.1f}%")
        
        if len(selected) == 75:
            log(f"\n🎉 SUCCESS! Selected all 75!")
        else:
            log(f"\n⚠️  Still only {len(selected)}/75")
            log(f"   Normalization is NOT the main problem.")
        
except Exception as e:
    log(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

log(f"\n{'='*80}")
log("TEST COMPLETE")
log(f"{'='*80}")

