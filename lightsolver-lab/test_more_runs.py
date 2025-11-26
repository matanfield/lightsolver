#!/usr/bin/env python3
"""
Test: Does increasing num_runs improve LPU success rate?

Hypothesis: With only 5 runs, LPU doesn't explore enough.
Test: Try 10, 20, 50 runs on a failed case.
"""

import numpy as np
import time
from laser_mind_client import LaserMind
from lightsolver_lib.lightsolver_lib import probmat_qubo_to_ising, coupling_matrix_xy, XYModelParams
from qubo_direct_solver import solve_qubo_bruteforce, validate_qubo_solution
from qubo_generator import generate_qubo

TOKEN_FILE = 'laser-mind-client/examples/lightsolver-token.txt'

print("="*80)
print("TEST: DOES MORE RUNS HELP?")
print("="*80)

# Use a case that failed with 5 runs
n = 10
seed = 1200  # This was instance 1, n=10, which had 120% gap

print(f"\nGenerating test QUBO (n={n}, seed={seed})...")
Q, meta = generate_qubo(n, qubo_type='uniform', variance=1.0, seed=seed)

print(f"QUBO properties:")
print(f"  Coefficient range: [{meta['min_coeff']:.3f}, {meta['max_coeff']:.3f}]")
print(f"  Range: {meta['coeff_range']:.1f}×")

# Ground truth
print(f"\nSolving with brute force (ground truth)...")
bf_solution, bf_energy, _ = solve_qubo_bruteforce(Q, verbose=False)
print(f"  ✓ Optimal energy: {bf_energy:.6f}")
print(f"  ✓ Optimal solution: {bf_solution}")

# Prepare for LPU
Q_norm = Q / np.max(np.abs(Q))
I, _ = probmat_qubo_to_ising(Q_norm)
coupling_matrix = coupling_matrix_xy(I, XYModelParams())

row_sums = np.abs(coupling_matrix).sum(axis=0)
print(f"\nCoupling matrix valid: {(row_sums < 1).all()} (max: {np.max(row_sums):.4f})")

# Test with different num_runs
print(f"\n{'='*80}")
print("TESTING DIFFERENT NUM_RUNS")
print(f"{'='*80}")

test_configs = [
    {'num_runs': 5, 'num_iterations': 500, 'name': 'Standard'},
    {'num_runs': 10, 'num_iterations': 500, 'name': 'More runs'},
    {'num_runs': 20, 'num_iterations': 500, 'name': 'Many runs'},
    {'num_runs': 5, 'num_iterations': 1000, 'name': 'More iterations'},
    {'num_runs': 10, 'num_iterations': 1000, 'name': 'More both'},
]

print(f"\n{'Config':<20} {'Runs':<8} {'Iters':<8} {'Time':<8} {'Energy':<12} {'Gap':<12} {'Status'}")
print("-"*85)

for config in test_configs:
    num_runs = config['num_runs']
    num_iterations = config['num_iterations']
    
    try:
        t0 = time.time()
        
        lsClient = LaserMind(pathToRefreshTokenFile=TOKEN_FILE, logToConsole=False)
        
        # Set timeout based on expected time
        import signal
        timeout_seconds = 60 if num_runs * num_iterations <= 5000 else 120
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Exceeded {timeout_seconds}s")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)
        
        res = lsClient.solve_coupling_matrix_sim_lpu(
            matrix_data=coupling_matrix.astype(np.complex64),
            num_runs=num_runs,
            num_iterations=num_iterations,
            rounds_per_record=1
        )
        
        signal.alarm(0)
        elapsed = time.time() - t0
        
        # Extract best solution across all runs
        record_states = res['data']['result']['record_states']
        actual_runs = record_states.shape[1]
        
        best_solution = None
        best_energy = float('inf')
        
        for run_idx in range(actual_runs):
            final_state = record_states[-1, run_idx, :]
            phases = np.angle(final_state)
            ising_state = np.where(phases >= 0, 1, -1)
            energy_ising = np.dot(ising_state, np.dot(I, ising_state))
            
            if energy_ising < best_energy:
                best_energy = energy_ising
                best_solution = ((ising_state + 1) // 2).astype(int)
        
        lpu_energy = validate_qubo_solution(Q, best_solution)
        gap = lpu_energy - bf_energy
        found_optimal = abs(gap) < 1e-6
        
        status = "✅ OPTIMAL" if found_optimal else f"❌ Gap {gap:+.3f}"
        
        print(f"{config['name']:<20} {num_runs:<8} {num_iterations:<8} {elapsed:<8.1f} "
              f"{lpu_energy:<12.3f} {gap:<12.3f} {status}")
        
    except TimeoutError:
        print(f"{config['name']:<20} {num_runs:<8} {num_iterations:<8} {'TIMEOUT':<8} "
              f"{'':<12} {'':<12} ❌ TIMEOUT")
    except Exception as e:
        print(f"{config['name']:<20} {num_runs:<8} {num_iterations:<8} {'ERROR':<8} "
              f"{'':<12} {'':<12} ❌ {str(e)[:20]}")

print(f"\n{'='*80}")
print("CONCLUSION")
print(f"{'='*80}")

print(f"\nOptimal energy: {bf_energy:.6f}")
print(f"\nDoes increasing num_runs/num_iterations help?")
print(f"  - If YES: LPU needs more exploration")
print(f"  - If NO: LPU has fundamental limitations")
print(f"\nNote: More runs/iterations = longer time, may timeout")

