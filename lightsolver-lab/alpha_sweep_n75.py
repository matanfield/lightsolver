#!/usr/bin/env python3
"""
Alpha parameter sweep on n=75 (all profitable transactions).
Tests different penalty values to find optimal.
"""

import json
import numpy as np
import time
from laser_mind_client import LaserMind
from lightsolver_lib.lightsolver_lib import probmat_qubo_to_ising, coupling_matrix_xy, XYModelParams

CAPACITY = 30_000_000
TOKEN_FILE = 'laser-mind-client/examples/lightsolver-token.txt'

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

# Get profitable subset (n=75)
profitable_indices = [i for i, p in enumerate(all_profits) if p > 0]
profits = [all_profits[i] for i in profitable_indices]
gas_costs = [all_gas_costs[i] for i in profitable_indices]

log("="*80)
log("ALPHA PARAMETER SWEEP - n=75 (ALL PROFITABLE TRANSACTIONS)")
log("="*80)
log(f"Problem size: n={len(profits)}")
log(f"Total profit if all selected: {sum(profits)/1e18:.6f} ETH")
log(f"Total gas if all selected: {sum(gas_costs):,} ({sum(gas_costs)/CAPACITY*100:.1f}%)")
log(f"Optimal solution: Select all 75 (trivial, no choice needed)")

# Calculate base alpha
max_profit = max(profits)
max_gas = max(gas_costs)
base_alpha = 2 * (max_profit / max_gas)
log(f"\nBase alpha (current formula): {base_alpha:.2e}")
log(f"This is WAY TOO LARGE!")

# Test different alpha values
log(f"\n{'='*80}")
log("TESTING DIFFERENT ALPHA VALUES")
log(f"{'='*80}")
log(f"Using: num_runs=5, num_iterations=500 (proven to work)")
log("")
log(f"{'Divisor':<10} {'Alpha':<15} {'Time':<8} {'Selected':<10} {'Profit (ETH)':<15} {'Gas %':<10} {'Status'}")
log("-"*95)

results = []

# Test alphas from large to small
for divisor in [1, 100, 10000, 1000000]:
    alpha = base_alpha / divisor
    print(f"[{time.strftime('%H:%M:%S')}] {divisor:<10} {alpha:<15.2e} ", end="", flush=True)
    
    # Build QUBO
    n = len(profits)
    Q = np.zeros((n, n))
    for i in range(n):
        Q[i, i] = -profits[i] + alpha * (gas_costs[i]**2 - 2*CAPACITY*gas_costs[i])
    for i in range(n):
        for j in range(i+1, n):
            Q[i, j] = 2 * alpha * gas_costs[i] * gas_costs[j]
    
    # Convert
    Q_max = np.max(np.abs(Q))
    if Q_max == 0 or np.isnan(Q_max):
        print(f"{'N/A':<8} {'ERROR':<10} {'':<15} {'':<10} Invalid QUBO")
        results.append((divisor, alpha, None, None, None, "Invalid QUBO"))
        continue
    
    Q_norm = Q / Q_max
    I, _ = probmat_qubo_to_ising(Q_norm)
    coupling_matrix = coupling_matrix_xy(I, XYModelParams())
    
    # Validate
    row_sums = np.abs(coupling_matrix).sum(axis=0)
    is_valid = (row_sums < 1).all()
    
    if not is_valid:
        print(f"{'N/A':<8} {'ERROR':<10} {'':<15} {'':<10} Invalid coupling")
        results.append((divisor, alpha, None, None, None, "Invalid coupling"))
        continue
    
    # Solve with emulator
    t0 = time.time()
    try:
        lsClient = LaserMind(pathToRefreshTokenFile=TOKEN_FILE, logToConsole=False)
        
        res = lsClient.solve_coupling_matrix_sim_lpu(
            matrix_data=coupling_matrix.astype(np.complex64),
            num_runs=5,           # Reduced from 10
            num_iterations=500,   # Reduced from 1000
            rounds_per_record=1
        )
        
        elapsed = time.time() - t0
        
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
        
        status = "✅ PERFECT!" if len(selected) == 75 else f"❌ Only {len(selected)}/75"
        
        print(f"{elapsed:<8.1f} {len(selected):<10} {total_profit/1e18:<15.6f} "
              f"{total_gas/CAPACITY*100:<10.1f} {status}")
        
        results.append((divisor, alpha, elapsed, len(selected), total_profit/1e18, status))
        
    except Exception as e:
        elapsed = time.time() - t0
        error_msg = str(e)[:30]
        print(f"{elapsed:<8.1f} {'ERROR':<10} {'':<15} {'':<10} {error_msg}")
        results.append((divisor, alpha, elapsed, None, None, error_msg))

# Summary
log(f"\n{'='*80}")
log("RESULTS SUMMARY")
log(f"{'='*80}")
log(f"Target: Select all 75 profitable transactions (0.019476 ETH, 52% gas)")
log("")

best_result = None
best_count = 0

for divisor, alpha, elapsed, selected, profit, status in results:
    if selected and selected > best_count:
        best_count = selected
        best_result = (divisor, alpha, selected, profit)

if best_result:
    divisor, alpha, selected, profit = best_result
    log(f"BEST RESULT:")
    log(f"  Alpha divisor: {divisor}")
    log(f"  Alpha value: {alpha:.2e}")
    log(f"  Selected: {selected}/75 transactions")
    log(f"  Profit: {profit:.6f} ETH")
    
    if selected == 75:
        log(f"\n🎉 SUCCESS! LPU selected all 75 profitable transactions!")
        log(f"   This proves alpha was the problem.")
        log(f"   Optimal alpha: {alpha:.2e} (divisor={divisor})")
    else:
        log(f"\n⚠️  Still suboptimal - selected only {selected}/75")
        log(f"   Need to investigate further:")
        log(f"   - Try more alpha values between working divisors")
        log(f"   - Test without normalization")
        log(f"   - Tune XY parameters")
        log(f"   - Implement threshold sweep")
else:
    log("❌ NO SUCCESSFUL RESULTS")
    log("   All tests failed - need to debug further")

log(f"\n{'='*80}")
log("TEST COMPLETE")
log(f"{'='*80}")

