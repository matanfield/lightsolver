#!/usr/bin/env python3
"""
Investigate: Why did test_more_runs.py show improvement but full retest didn't?

The specific case (n=10, seed=1200) improved from gap=8.740 to gap=0.123.
But the full test suite got WORSE with num_runs=10.

Let's test that specific case multiple times to see if results are consistent.
"""

import numpy as np
from laser_mind_client import LaserMind
from lightsolver_lib.lightsolver_lib import probmat_qubo_to_ising, coupling_matrix_xy, XYModelParams
from qubo_direct_solver import solve_qubo_bruteforce, validate_qubo_solution
from qubo_generator import generate_qubo

TOKEN_FILE = 'laser-mind-client/examples/lightsolver-token.txt'

print("="*80)
print("INVESTIGATING INCONSISTENCY")
print("="*80)

# The specific case that showed improvement
n = 10
seed = 1200

print(f"\nTest case: n={n}, seed={seed}")
print("This case showed: gap=8.740 with 5 runs → gap=0.123 with 10 runs")
print("\nLet's run it multiple times to check consistency...")

# Generate QUBO
Q, meta = generate_qubo(n, qubo_type='uniform', variance=1.0, seed=seed)
bf_solution, bf_energy, _ = solve_qubo_bruteforce(Q, verbose=False)

print(f"\nOptimal energy: {bf_energy:.6f}")
print(f"Optimal solution: {bf_solution}")

# Prepare coupling matrix (same for all runs)
Q_norm = Q / np.max(np.abs(Q))
I, _ = probmat_qubo_to_ising(Q_norm)
coupling_matrix = coupling_matrix_xy(I, XYModelParams())

print(f"\n{'='*80}")
print("TESTING REPEATABILITY")
print(f"{'='*80}")

print(f"\n{'Trial':<8} {'Runs':<8} {'LPU Energy':<12} {'Gap':<12} {'Gap %':<10} {'Status'}")
print("-"*65)

# Test with 5 runs, 3 times
for trial in range(3):
    try:
        lsClient = LaserMind(pathToRefreshTokenFile=TOKEN_FILE, logToConsole=False)
        
        res = lsClient.solve_coupling_matrix_sim_lpu(
            matrix_data=coupling_matrix.astype(np.complex64),
            num_runs=5,
            num_iterations=500,
            rounds_per_record=1
        )
        
        record_states = res['data']['result']['record_states']
        best_solution = None
        best_energy = float('inf')
        
        for run_idx in range(5):
            final_state = record_states[-1, run_idx, :]
            phases = np.angle(final_state)
            ising_state = np.where(phases >= 0, 1, -1)
            energy_ising = np.dot(ising_state, np.dot(I, ising_state))
            
            if energy_ising < best_energy:
                best_energy = energy_ising
                best_solution = ((ising_state + 1) // 2).astype(int)
        
        lpu_energy = validate_qubo_solution(Q, best_solution)
        gap = lpu_energy - bf_energy
        gap_pct = (gap / abs(bf_energy)) * 100
        status = "✅" if abs(gap) < 0.5 else "❌"
        
        print(f"{trial+1:<8} {5:<8} {lpu_energy:<12.3f} {gap:<12.3f} {gap_pct:<10.1f} {status}")
        
    except Exception as e:
        print(f"{trial+1:<8} {5:<8} {'ERROR':<12} {'':<12} {'':<10} ❌")

# Test with 10 runs, 3 times
for trial in range(3):
    try:
        lsClient = LaserMind(pathToRefreshTokenFile=TOKEN_FILE, logToConsole=False)
        
        res = lsClient.solve_coupling_matrix_sim_lpu(
            matrix_data=coupling_matrix.astype(np.complex64),
            num_runs=10,
            num_iterations=500,
            rounds_per_record=1
        )
        
        record_states = res['data']['result']['record_states']
        best_solution = None
        best_energy = float('inf')
        
        for run_idx in range(10):
            final_state = record_states[-1, run_idx, :]
            phases = np.angle(final_state)
            ising_state = np.where(phases >= 0, 1, -1)
            energy_ising = np.dot(ising_state, np.dot(I, ising_state))
            
            if energy_ising < best_energy:
                best_energy = energy_ising
                best_solution = ((ising_state + 1) // 2).astype(int)
        
        lpu_energy = validate_qubo_solution(Q, best_solution)
        gap = lpu_energy - bf_energy
        gap_pct = (gap / abs(bf_energy)) * 100
        status = "✅" if abs(gap) < 0.5 else "❌"
        
        print(f"{trial+1:<8} {10:<8} {lpu_energy:<12.3f} {gap:<12.3f} {gap_pct:<10.1f} {status}")
        
    except Exception as e:
        print(f"{trial+1:<8} {10:<8} {'ERROR':<12} {'':<12} {'':<10} ❌")

print(f"\n{'='*80}")
print("CONCLUSION")
print(f"{'='*80}")

print(f"\nOptimal: {bf_energy:.6f}")
print(f"\nIf results vary across trials:")
print(f"  → LPU is STOCHASTIC (different results each time)")
print(f"  → Need multiple trials and average")
print(f"\nIf 10 runs consistently better than 5:")
print(f"  → More runs helps")
print(f"  → Should use 10+ runs")
print(f"\nIf no clear pattern:")
print(f"  → LPU is unreliable")
print(f"  → Fundamental limitation")

