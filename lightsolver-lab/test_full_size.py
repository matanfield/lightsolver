#!/usr/bin/env python3
"""
Test with FULL problem size (all 2005 transactions) to answer:
1. Can emulator handle n=2005?
2. Where does the time go? (should be milliseconds, not seconds)
3. Why underperforming greedy?
"""

import time
import json
import numpy as np
from laser_mind_client import LaserMind
from lightsolver_lib.lightsolver_lib import probmat_qubo_to_ising, coupling_matrix_xy, XYModelParams
import os

# Timing decorator
def timed(desc):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            print(f"  [{desc}] {elapsed*1000:.1f} ms")
            return result
        return wrapper
    return decorator

CAPACITY = 30_000_000

# Load data
print("="*80)
print("FULL SIZE TEST (n=2005)")
print("="*80)

@timed("Load JSON")
def load_data():
    with open('../rbuilder/knapsack_instance_21200000.json') as f:
        return json.load(f)

data = load_data()
items = data['items']
n = len(items)

print(f"\nProblem size: {n} transactions")

# Parse
@timed("Parse data")
def parse():
    profits = []
    gas_costs = []
    for item in items:
        profit_hex = item['profit']
        profit = int(profit_hex, 16) if profit_hex.startswith('0x') else int(profit_hex)
        profits.append(profit)
        gas_costs.append(item['gas'])
    return profits, gas_costs

profits, gas_costs = parse()

# Build QUBO
@timed("Build QUBO matrix")
def build_qubo():
    Q = np.zeros((n, n))
    max_profit = max(profits) if profits else 1
    max_gas = max(gas_costs) if gas_costs else 1
    penalty = (max_profit / max_gas) * 2
    
    for i in range(n):
        Q[i, i] = -profits[i] + penalty * (gas_costs[i]**2 - 2*CAPACITY*gas_costs[i])
    
    for i in range(n):
        for j in range(i+1, n):
            Q[i, j] = 2 * penalty * gas_costs[i] * gas_costs[j]
    
    return Q

Q = build_qubo()
print(f"QUBO matrix: {Q.shape}, {Q.nbytes/1024/1024:.1f} MB")

# Normalize
@timed("Normalize QUBO")
def normalize():
    Q_max = np.max(np.abs(Q))
    return Q / Q_max if Q_max > 0 else Q

Q_norm = normalize()

# Convert to Ising
@timed("QUBO → Ising")
def to_ising():
    return probmat_qubo_to_ising(Q_norm)

I, offset = to_ising()

# Build coupling matrix
@timed("Ising → Coupling Matrix")
def to_coupling():
    return coupling_matrix_xy(I, XYModelParams())

coupling_matrix = to_coupling()

# Validate coupling matrix
@timed("Validate coupling matrix")
def validate():
    row_sums = np.abs(coupling_matrix).sum(axis=0)
    is_valid = (row_sums < 1).all()
    max_sum = np.max(row_sums)
    return is_valid, max_sum

is_valid, max_sum = validate()
print(f"Coupling matrix valid: {is_valid} (max row sum: {max_sum:.4f})")

if not is_valid:
    print("\n⚠️  PROBLEM: Coupling matrix constraint violated!")
    print("This is likely why we're getting poor results.")
    print("Need to scale down the coupling matrix or use different parameters.")
else:
    print("\n✅ Ready to send to emulator...")
    print("\nSending to emulator (this is where network time happens)...")
    
    token_file = "laser-mind-client/examples/lightsolver-token.txt"
    
    start_api = time.time()
    lsClient = LaserMind(pathToRefreshTokenFile=token_file)
    print(f"  [API connection] {(time.time() - start_api)*1000:.1f} ms")
    
    start_solve = time.time()
    res = lsClient.solve_coupling_matrix_sim_lpu(
        matrix_data=coupling_matrix.astype(np.complex64),
        num_runs=10,
        num_iterations=1000,
        rounds_per_record=1
    )
    solve_time = time.time() - start_solve
    
    print(f"  [Emulator solve (API call)] {solve_time*1000:.1f} ms = {solve_time:.2f} seconds")
    print(f"  [Server processing time] {res.get('solver_time', 'N/A')} seconds")
    
    # Extract solution
    @timed("Extract solution")
    def extract():
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
        
        return best_solution
    
    solution = extract()
    
    # Evaluate
    selected = np.where(solution == 1)[0]
    total_profit = sum(profits[i] for i in selected)
    total_gas = sum(gas_costs[i] for i in selected)
    
    print(f"\n{'='*80}")
    print(f"RESULTS")
    print(f"{'='*80}")
    print(f"Transactions selected: {len(selected)} / {n}")
    print(f"Total profit: {total_profit/1e18:.6f} ETH")
    print(f"Total gas: {total_gas:,}")
    print(f"Gas utilization: {total_gas/CAPACITY*100:.2f}%")
    print(f"Constraint satisfied: {total_gas <= CAPACITY}")

