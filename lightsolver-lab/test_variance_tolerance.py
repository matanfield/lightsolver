#!/usr/bin/env python3
"""
Phase 2, Step 2.3: Test LPU Variance Tolerance

Find at what variance level LPU starts failing.
"""

import numpy as np
import time
from laser_mind_client import LaserMind
from lightsolver_lib.lightsolver_lib import probmat_qubo_to_ising, coupling_matrix_xy, XYModelParams
from qubo_direct_solver import solve_qubo_bruteforce, validate_qubo_solution
from qubo_generator import generate_qubo

TOKEN_FILE = 'laser-mind-client/examples/lightsolver-token.txt'

def solve_qubo_with_lpu(Q):
    """Solve QUBO with LPU."""
    try:
        Q_max = np.max(np.abs(Q))
        if Q_max == 0 or np.isnan(Q_max):
            return None, None, False
        
        Q_norm = Q / Q_max
        I, _ = probmat_qubo_to_ising(Q_norm)
        coupling_matrix = coupling_matrix_xy(I, XYModelParams())
        
        row_sums = np.abs(coupling_matrix).sum(axis=0)
        if not (row_sums < 1).all():
            return None, None, False
        
        lsClient = LaserMind(pathToRefreshTokenFile=TOKEN_FILE, logToConsole=False)
        
        res = lsClient.solve_coupling_matrix_sim_lpu(
            matrix_data=coupling_matrix.astype(np.complex64),
            num_runs=5,
            num_iterations=500,
            rounds_per_record=1
        )
        
        record_states = res['data']['result']['record_states']
        num_runs = record_states.shape[1]
        
        best_solution = None
        best_energy = float('inf')
        
        for run_idx in range(num_runs):
            final_state = record_states[-1, run_idx, :]
            phases = np.angle(final_state)
            ising_state = np.where(phases >= 0, 1, -1)
            energy_ising = np.dot(ising_state, np.dot(I, ising_state))
            
            if energy_ising < best_energy:
                best_energy = energy_ising
                best_solution = ((ising_state + 1) // 2).astype(int)
        
        qubo_energy = validate_qubo_solution(Q, best_solution)
        return best_solution, qubo_energy, True
        
    except Exception as e:
        return None, None, False

print("="*80)
print("PHASE 2, STEP 2.3: VARIANCE TOLERANCE TEST")
print("="*80)

print("\nTest: How does LPU performance change with coefficient variance?")
print("Fixed: n=10 (can verify with brute force)")
print("Vary: variance from 0.1 to 10000")
print()

n = 10
variance_values = [0.1, 1.0, 10.0, 100.0, 1000.0]
num_instances = 3

results = []

print(f"{'Variance':<12} {'Instance':<10} {'Optimal':<12} {'LPU':<12} {'Gap':<12} {'Gap %':<10} {'Status'}")
print("-"*80)

for variance in variance_values:
    variance_results = []
    
    for instance in range(num_instances):
        seed = 2000 + int(variance * 10) + instance
        
        # Generate QUBO
        Q, meta = generate_qubo(n, qubo_type='uniform', variance=variance, seed=seed)
        
        # Solve with brute force
        bf_solution, bf_energy, _ = solve_qubo_bruteforce(Q, verbose=False)
        
        # Solve with LPU
        lpu_solution, lpu_energy, lpu_success = solve_qubo_with_lpu(Q)
        
        if not lpu_success:
            print(f"{variance:<12.1f} {instance+1:<10} {bf_energy:<12.3f} {'FAILED':<12} {'':<12} {'':<10} ❌")
            variance_results.append({
                'variance': variance,
                'instance': instance,
                'optimal': bf_energy,
                'lpu': None,
                'gap': None,
                'success': False,
                'coeff_range': meta['coeff_range']
            })
            continue
        
        gap = lpu_energy - bf_energy
        gap_percent = (gap / abs(bf_energy)) * 100 if bf_energy != 0 else 0
        found_optimal = abs(gap) < 1e-6
        
        status = "✅" if found_optimal else "❌"
        
        print(f"{variance:<12.1f} {instance+1:<10} {bf_energy:<12.3f} {lpu_energy:<12.3f} "
              f"{gap:<12.3f} {gap_percent:<10.1f} {status}")
        
        variance_results.append({
            'variance': variance,
            'instance': instance,
            'optimal': bf_energy,
            'lpu': lpu_energy,
            'gap': gap,
            'gap_percent': gap_percent,
            'found_optimal': found_optimal,
            'success': True,
            'coeff_range': meta['coeff_range']
        })
    
    results.extend(variance_results)

# Summary by variance
print(f"\n{'='*80}")
print("SUMMARY BY VARIANCE")
print(f"{'='*80}")

print(f"\n{'Variance':<12} {'Success':<12} {'Optimal':<12} {'Avg Gap':<12} {'Max Gap':<12} {'Coeff Range'}")
print("-"*80)

for variance in variance_values:
    var_results = [r for r in results if r['variance'] == variance]
    successful = [r for r in var_results if r['success']]
    optimal = [r for r in successful if r.get('found_optimal', False)]
    
    if successful:
        avg_gap = np.mean([abs(r['gap']) for r in successful])
        max_gap = np.max([abs(r['gap']) for r in successful])
        avg_range = np.mean([r['coeff_range'] for r in successful])
        
        print(f"{variance:<12.1f} {len(optimal)}/{len(successful):<10} "
              f"{len(optimal)/len(successful)*100:<12.1f} {avg_gap:<12.3f} "
              f"{max_gap:<12.3f} {avg_range:<.1f}×")
    else:
        print(f"{variance:<12.1f} {'0/0':<12} {'':<12} {'':<12} {'':<12}")

# Overall
all_successful = [r for r in results if r['success']]
all_optimal = [r for r in all_successful if r.get('found_optimal', False)]

print(f"\n{'='*80}")
print("OVERALL RESULTS")
print(f"{'='*80}")
print(f"Total tests: {len(results)}")
print(f"Successful: {len(all_successful)}/{len(results)}")
print(f"Found optimal: {len(all_optimal)}/{len(all_successful)} ({len(all_optimal)/len(all_successful)*100:.1f}%)")

if all_successful:
    avg_gap = np.mean([abs(r['gap']) for r in all_successful])
    print(f"Average gap: {avg_gap:.3f}")

print(f"\n{'='*80}")
print("CONCLUSIONS")
print(f"{'='*80}")

# Analyze pattern
success_by_variance = {}
for variance in variance_values:
    var_results = [r for r in results if r['variance'] == variance]
    successful = [r for r in var_results if r['success']]
    optimal = [r for r in successful if r.get('found_optimal', False)]
    success_rate = len(optimal) / len(successful) if successful else 0
    success_by_variance[variance] = success_rate

print("\nSuccess rate by variance:")
for variance, rate in success_by_variance.items():
    print(f"  Variance {variance:<8.1f}: {rate*100:5.1f}%")

# Find pattern
if success_by_variance[0.1] > success_by_variance[1000.0]:
    print("\n→ Success rate DECREASES with variance")
    print("  LPU works better on low-variance problems")
elif success_by_variance[0.1] < success_by_variance[1000.0]:
    print("\n→ Success rate INCREASES with variance")
    print("  Unexpected! Need to investigate further")
else:
    print("\n→ Success rate INDEPENDENT of variance")
    print("  Variance is not the main factor")

print(f"\n{'='*80}")
print("PHASE 2, STEP 2.3 COMPLETE")
print(f"{'='*80}")

