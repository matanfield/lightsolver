#!/usr/bin/env python3
"""
Debug version that shows exactly where the API call gets stuck.
"""

import json
import numpy as np
import time
import sys
from laser_mind_client import LaserMind
from lightsolver_lib.lightsolver_lib import probmat_qubo_to_ising, coupling_matrix_xy, XYModelParams

CAPACITY = 30_000_000
TOKEN_FILE = 'laser-mind-client/examples/lightsolver-token.txt'

def log(msg):
    """Log with timestamp."""
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

log("="*80)
log("DEBUG: API CALL INVESTIGATION")
log("="*80)

# Quick setup
log("Loading data...")
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

log(f"Problem size: n={len(profits)}")

# Build QUBO quickly
log("Building QUBO...")
max_profit = max(profits)
max_gas = max(gas_costs)
alpha = 2 * (max_profit / max_gas) / 10000
n = len(profits)
Q = np.zeros((n, n))
for i in range(n):
    Q[i, i] = -profits[i] + alpha * (gas_costs[i]**2 - 2*CAPACITY*gas_costs[i])
for i in range(n):
    for j in range(i+1, n):
        Q[i, j] = 2 * alpha * gas_costs[i] * gas_costs[j]

# Convert
log("Converting to Ising...")
Q_max = np.max(np.abs(Q))
Q_norm = Q / Q_max
I, offset_ising = probmat_qubo_to_ising(Q_norm)

log("Creating coupling matrix...")
coupling_matrix = coupling_matrix_xy(I, XYModelParams())

row_sums = np.abs(coupling_matrix).sum(axis=0)
is_valid = (row_sums < 1).all()
log(f"Coupling matrix valid: {is_valid} (max row sum: {np.max(row_sums):.4f})")

if not is_valid:
    log("ERROR: Invalid coupling matrix!")
    sys.exit(1)

# Now the critical part - API call with detailed logging
log("="*80)
log("STARTING API CALL SEQUENCE")
log("="*80)

try:
    log("Step 1: Creating LaserMind client...")
    t0 = time.time()
    lsClient = LaserMind(pathToRefreshTokenFile=TOKEN_FILE, logToConsole=True)
    log(f"  ✓ Client created ({time.time()-t0:.2f}s)")
    
    log("Step 2: Preparing matrix data...")
    t0 = time.time()
    matrix_data = coupling_matrix.astype(np.complex64)
    log(f"  ✓ Matrix prepared: shape={matrix_data.shape}, dtype={matrix_data.dtype} ({time.time()-t0:.2f}s)")
    
    log("Step 3: Calling solve_coupling_matrix_sim_lpu()...")
    log("  Parameters:")
    log(f"    - matrix_data: {matrix_data.shape} complex64")
    log(f"    - num_runs: 10")
    log(f"    - num_iterations: 1000")
    log(f"    - rounds_per_record: 1")
    log("  This is where it typically gets stuck...")
    log("  Expected: 3-8 seconds")
    log("  If > 30 seconds: likely timeout or server issue")
    
    t0 = time.time()
    
    # Add a simple timeout mechanism
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError("API call exceeded 60 seconds")
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(60)  # 60 second timeout
    
    try:
        log("  Calling API now...")
        res = lsClient.solve_coupling_matrix_sim_lpu(
            matrix_data=matrix_data,
            num_runs=10,
            num_iterations=1000,
            rounds_per_record=1
        )
        signal.alarm(0)  # Cancel timeout
        
        elapsed = time.time() - t0
        log(f"  ✓ API call completed! ({elapsed:.2f}s)")
        
        if elapsed > 10:
            log(f"  ⚠️  Unusually slow ({elapsed:.2f}s > 10s expected)")
        
        log("Step 4: Checking response...")
        log(f"  Response keys: {list(res.keys())}")
        
        if 'data' in res:
            log(f"  Data keys: {list(res['data'].keys())}")
            if 'result' in res['data']:
                log(f"  Result keys: {list(res['data']['result'].keys())}")
                record_states = res['data']['result']['record_states']
                log(f"  ✓ Got record_states: shape={record_states.shape}")
        
        log("="*80)
        log("SUCCESS! API call completed normally")
        log("="*80)
        
    except TimeoutError as e:
        log(f"  ❌ TIMEOUT after 60 seconds!")
        log(f"  This suggests:")
        log(f"    1. Server is overloaded or down")
        log(f"    2. Network connectivity issue")
        log(f"    3. Problem size too large for service")
        log(f"    4. Rate limiting in effect")
        raise
        
except Exception as e:
    elapsed = time.time() - t0
    log(f"  ❌ ERROR after {elapsed:.2f}s")
    log(f"  Error type: {type(e).__name__}")
    log(f"  Error message: {str(e)}")
    log("")
    log("="*80)
    log("DEBUGGING INFO")
    log("="*80)
    log("Possible causes:")
    log("  1. Authentication issue - Check token file")
    log("  2. Network issue - Check internet connection")
    log("  3. Service availability - LightSolver server down?")
    log("  4. Rate limiting - Too many requests?")
    log("  5. Problem size - n=75 too large? (unlikely)")
    log("")
    log("To investigate:")
    log("  - Check laser-mind.log for detailed error messages")
    log("  - Try with smaller problem (n=10)")
    log("  - Check LightSolver service status")
    log("  - Verify token hasn't expired")
    
    import traceback
    log("")
    log("Full traceback:")
    traceback.print_exc()
    
    sys.exit(1)

log("")
log("Script completed successfully!")


