#!/usr/bin/env python3
"""
Phase 2, Step 2.1: Test LPU on Uniform Random QUBOs

Systematic testing of LPU emulator on controlled QUBO problems.
Compare with brute force ground truth for small n.
"""

import numpy as np
import time
from laser_mind_client import LaserMind
from lightsolver_lib.lightsolver_lib import probmat_qubo_to_ising, coupling_matrix_xy, XYModelParams

# Import our tools
from qubo_direct_solver import solve_qubo_bruteforce, validate_qubo_solution
from qubo_generator import generate_qubo

TOKEN_FILE = 'laser-mind-client/examples/lightsolver-token.txt'

def solve_qubo_with_lpu(Q, num_runs=10, num_iterations=500):
    """
    Solve QUBO using LPU emulator.
    
    Returns:
        solution: Binary vector
        energy: Energy of solution
        time: Solve time
        success: Whether it completed successfully
    """
    n = Q.shape[0]
    
    try:
        t0 = time.time()
        
        # Normalize
        Q_max = np.max(np.abs(Q))
        if Q_max == 0 or np.isnan(Q_max):
            return None, None, 0, False
        
        Q_norm = Q / Q_max
        
        # Convert to Ising
        I, offset_ising = probmat_qubo_to_ising(Q_norm)
        
        # Coupling matrix
        coupling_matrix = coupling_matrix_xy(I, XYModelParams())
        
        # Validate
        row_sums = np.abs(coupling_matrix).sum(axis=0)
        if not (row_sums < 1).all():
            return None, None, 0, False
        
        # Solve with LPU
        lsClient = LaserMind(pathToRefreshTokenFile=TOKEN_FILE, logToConsole=False)
        
        res = lsClient.solve_coupling_matrix_sim_lpu(
            matrix_data=coupling_matrix.astype(np.complex64),
            num_runs=num_runs,
            num_iterations=num_iterations,
            rounds_per_record=1
        )
        
        # Extract solution
        record_states = res['data']['result']['record_states']
        num_runs_actual = record_states.shape[1]
        
        best_solution = None
        best_energy = float('inf')
        
        for run_idx in range(num_runs_actual):
            final_state = record_states[-1, run_idx, :]
            phases = np.angle(final_state)
            ising_state = np.where(phases >= 0, 1, -1)
            energy_ising = np.dot(ising_state, np.dot(I, ising_state))
            
            if energy_ising < best_energy:
                best_energy = energy_ising
                best_solution = ((ising_state + 1) // 2).astype(int)
        
        elapsed = time.time() - t0
        
        # Calculate actual QUBO energy
        qubo_energy = validate_qubo_solution(Q, best_solution)
        
        return best_solution, qubo_energy, elapsed, True
        
    except Exception as e:
        return None, None, 0, False

# Main test
print("="*80)
print("PHASE 2: TEST LPU ON SIMPLE QUBOs")
print("="*80)

print("\nTest Plan:")
print("  1. Generate uniform random QUBOs of increasing size")
print("  2. Solve with brute force (ground truth, n≤15)")
print("  3. Solve with LPU emulator")
print("  4. Compare results")
print()

# Test parameters
test_sizes = [5, 10, 15]  # Start small, can verify with brute force
num_instances_per_size = 3  # Multiple instances to check consistency
variance = 1.0  # Start with moderate variance

results = []

for n in test_sizes:
    print(f"\n{'='*80}")
    print(f"TESTING n={n}")
    print(f"{'='*80}")
    
    for instance in range(num_instances_per_size):
        print(f"\nInstance {instance+1}/{num_instances_per_size}")
        print("-"*80)
        
        # Generate QUBO
        seed = 1000 + n * 100 + instance
        Q, meta = generate_qubo(n, qubo_type='uniform', variance=variance, seed=seed)
        
        print(f"Generated {n}×{n} uniform QUBO")
        print(f"  Coefficient range: [{meta['min_coeff']:.3f}, {meta['max_coeff']:.3f}]")
        print(f"  Range (max/min): {meta['coeff_range']:.1f}×")
        
        # Solve with brute force (ground truth)
        print(f"\nSolving with brute force...")
        t0 = time.time()
        bf_solution, bf_energy, all_energies = solve_qubo_bruteforce(Q, verbose=False)
        bf_time = time.time() - t0
        print(f"  ✓ Optimal energy: {bf_energy:.6f} (in {bf_time:.3f}s)")
        
        # Solve with LPU
        print(f"\nSolving with LPU emulator...")
        lpu_solution, lpu_energy, lpu_time, lpu_success = solve_qubo_with_lpu(Q)
        
        if not lpu_success:
            print(f"  ❌ LPU FAILED (coupling matrix invalid or timeout)")
            results.append({
                'n': n,
                'instance': instance,
                'bf_energy': bf_energy,
                'lpu_energy': None,
                'gap': None,
                'gap_percent': None,
                'found_optimal': False,
                'success': False
            })
            continue
        
        print(f"  ✓ LPU energy: {lpu_energy:.6f} (in {lpu_time:.1f}s)")
        
        # Compare
        gap = lpu_energy - bf_energy
        gap_percent = (gap / abs(bf_energy)) * 100 if bf_energy != 0 else 0
        found_optimal = abs(gap) < 1e-6
        
        print(f"\nComparison:")
        print(f"  Optimal (brute force): {bf_energy:.6f}")
        print(f"  LPU result:            {lpu_energy:.6f}")
        print(f"  Gap:                   {gap:+.6f} ({gap_percent:+.2f}%)")
        
        if found_optimal:
            print(f"  ✅ LPU FOUND OPTIMAL!")
        else:
            print(f"  ⚠️  LPU suboptimal by {gap:.6f}")
        
        results.append({
            'n': n,
            'instance': instance,
            'bf_energy': bf_energy,
            'lpu_energy': lpu_energy,
            'gap': gap,
            'gap_percent': gap_percent,
            'found_optimal': found_optimal,
            'success': True,
            'bf_time': bf_time,
            'lpu_time': lpu_time
        })

# Summary
print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}")

print(f"\nResults by size:")
for n in test_sizes:
    n_results = [r for r in results if r['n'] == n]
    successful = [r for r in n_results if r['success']]
    optimal = [r for r in successful if r['found_optimal']]
    
    print(f"\nn={n}:")
    print(f"  Successful: {len(successful)}/{len(n_results)}")
    print(f"  Found optimal: {len(optimal)}/{len(successful)}")
    
    if successful:
        avg_gap = np.mean([abs(r['gap']) for r in successful])
        max_gap = np.max([abs(r['gap']) for r in successful])
        print(f"  Average gap: {avg_gap:.6f}")
        print(f"  Max gap: {max_gap:.6f}")
        print(f"  Success rate: {len(optimal)/len(successful)*100:.1f}%")

# Overall statistics
all_successful = [r for r in results if r['success']]
all_optimal = [r for r in all_successful if r['found_optimal']]

print(f"\nOverall:")
print(f"  Total tests: {len(results)}")
print(f"  Successful: {len(all_successful)}/{len(results)} ({len(all_successful)/len(results)*100:.1f}%)")
print(f"  Found optimal: {len(all_optimal)}/{len(all_successful)} ({len(all_optimal)/len(all_successful)*100:.1f}%)")

if all_successful:
    avg_gap_all = np.mean([abs(r['gap']) for r in all_successful])
    print(f"  Average gap: {avg_gap_all:.6f}")

print(f"\n{'='*80}")
print("PHASE 2, STEP 2.1 COMPLETE")
print(f"{'='*80}")

if len(all_optimal) == len(all_successful):
    print("\n🎉 SUCCESS! LPU finds optimal for all uniform random QUBOs (n≤15, variance=1)")
    print("\nNext: Test with higher variance to find breaking point")
else:
    print(f"\n⚠️  LPU found optimal in {len(all_optimal)}/{len(all_successful)} cases")
    print("\nNeed to investigate why some cases fail")

# Save results
import json
with open('lpu_simple_qubo_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print("\nResults saved to: lpu_simple_qubo_results.json")

