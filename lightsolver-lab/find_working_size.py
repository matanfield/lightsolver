#!/usr/bin/env python3
"""
Find the actual working problem size by testing incrementally.
"""

import json
import numpy as np
import time
from laser_mind_client import LaserMind
from lightsolver_lib.lightsolver_lib import probmat_qubo_to_ising, coupling_matrix_xy, XYModelParams

CAPACITY = 30_000_000
TOKEN_FILE = 'laser-mind-client/examples/lightsolver-token.txt'
TIMEOUT = 30  # 30 second timeout per test

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

log("="*80)
log("FINDING WORKING PROBLEM SIZE")
log("="*80)

# Test sizes
test_sizes = [10, 25, 50, 75]

results = []

for n in test_sizes:
    log(f"\n{'='*80}")
    log(f"TESTING n={n}")
    log(f"{'='*80}")
    
    # Get subset
    profits = all_profits[:n]
    gas_costs = all_gas_costs[:n]
    
    # Build QUBO
    log(f"Building QUBO...")
    max_profit = max(profits)
    max_gas = max(gas_costs)
    alpha = 2 * (max_profit / max_gas) / 10000
    
    Q = np.zeros((n, n))
    for i in range(n):
        Q[i, i] = -profits[i] + alpha * (gas_costs[i]**2 - 2*CAPACITY*gas_costs[i])
    for i in range(n):
        for j in range(i+1, n):
            Q[i, j] = 2 * alpha * gas_costs[i] * gas_costs[j]
    
    # Convert
    Q_max = np.max(np.abs(Q))
    Q_norm = Q / Q_max
    I, _ = probmat_qubo_to_ising(Q_norm)
    coupling_matrix = coupling_matrix_xy(I, XYModelParams())
    
    # Validate
    row_sums = np.abs(coupling_matrix).sum(axis=0)
    is_valid = (row_sums < 1).all()
    
    if not is_valid:
        log(f"❌ Invalid coupling matrix (max sum: {np.max(row_sums):.4f})")
        results.append((n, False, 0, "Invalid coupling matrix"))
        continue
    
    # Try emulator with timeout
    log(f"Calling emulator (timeout={TIMEOUT}s)...")
    t0 = time.time()
    
    try:
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Exceeded {TIMEOUT}s")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(TIMEOUT)
        
        lsClient = LaserMind(pathToRefreshTokenFile=TOKEN_FILE, logToConsole=False)
        
        res = lsClient.solve_coupling_matrix_sim_lpu(
            matrix_data=coupling_matrix.astype(np.complex64),
            num_runs=5,  # Reduced from 10
            num_iterations=500,  # Reduced from 1000
            rounds_per_record=1
        )
        
        signal.alarm(0)
        elapsed = time.time() - t0
        
        log(f"✅ SUCCESS in {elapsed:.1f}s")
        results.append((n, True, elapsed, "Success"))
        
    except TimeoutError as e:
        elapsed = time.time() - t0
        log(f"❌ TIMEOUT after {elapsed:.1f}s")
        results.append((n, False, elapsed, "Timeout"))
        
    except Exception as e:
        elapsed = time.time() - t0
        error_msg = str(e)[:50]
        log(f"❌ ERROR after {elapsed:.1f}s: {error_msg}")
        results.append((n, False, elapsed, error_msg))

# Summary
log(f"\n{'='*80}")
log("RESULTS SUMMARY")
log(f"{'='*80}")
log(f"{'Size':<8} {'Status':<10} {'Time':<10} {'Notes'}")
log("-"*80)

for n, success, elapsed, note in results:
    status = "✅ WORKS" if success else "❌ FAILS"
    log(f"{n:<8} {status:<10} {elapsed:<10.1f} {note}")

# Find maximum working size
working_sizes = [n for n, success, _, _ in results if success]
if working_sizes:
    max_working = max(working_sizes)
    log(f"\n{'='*80}")
    log(f"MAXIMUM WORKING SIZE: n={max_working}")
    log(f"{'='*80}")
    log(f"\nRecommendation: Use n≤{max_working} for reliable results")
else:
    log(f"\n{'='*80}")
    log("NO WORKING SIZES FOUND!")
    log(f"{'='*80}")
    log("\nPossible issues:")
    log("  - Server unavailable")
    log("  - Token expired")
    log("  - Network problems")
    log("  - Need to reduce num_runs/num_iterations further")

