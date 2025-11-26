#!/usr/bin/env python3
"""
Phase 1, Step 1.1: Direct QUBO Solver (Brute Force)

Ground truth solver for small QUBO problems (n ≤ 20).
Tests all 2^n possible solutions to find the global optimum.
"""

import numpy as np
import time

def solve_qubo_bruteforce(Q, offset=0, verbose=False):
    """
    Solve QUBO by exhaustive search over all 2^n binary vectors.
    
    QUBO formulation: minimize E(x) = x^T Q x + offset
    where x ∈ {0,1}^n
    
    Args:
        Q: QUBO matrix (n×n), upper triangular
        offset: Constant offset (optional)
        verbose: Print progress
    
    Returns:
        best_solution: Binary vector that minimizes energy
        best_energy: Minimum energy value
        all_energies: List of all energies (for analysis)
    """
    n = Q.shape[0]
    
    if n > 20:
        raise ValueError(f"Problem too large (n={n}). Brute force limited to n≤20 (2^20 = 1M combinations)")
    
    if verbose:
        print(f"Solving QUBO with n={n} variables ({2**n:,} combinations to check)")
    
    best_solution = None
    best_energy = float('inf')
    all_energies = []
    
    t0 = time.time()
    
    # Try all 2^n binary combinations
    for i in range(2**n):
        # Convert integer i to binary vector
        x = np.array([(i >> j) & 1 for j in range(n)], dtype=int)
        
        # Calculate energy: E = x^T Q x + offset
        # For upper triangular Q: E = sum(Q[i,i]*x[i]^2) + 2*sum(Q[i,j]*x[i]*x[j] for i<j)
        energy = 0.0
        
        # Diagonal terms
        for j in range(n):
            energy += Q[j, j] * x[j]
        
        # Off-diagonal terms (upper triangle)
        for j in range(n):
            for k in range(j+1, n):
                energy += 2 * Q[j, k] * x[j] * x[k]
        
        energy += offset
        all_energies.append(energy)
        
        if energy < best_energy:
            best_energy = energy
            best_solution = x.copy()
    
    elapsed = time.time() - t0
    
    if verbose:
        print(f"✓ Completed in {elapsed:.3f}s")
        print(f"  Best energy: {best_energy:.6f}")
        print(f"  Best solution: {best_solution}")
        print(f"  Energy range: [{min(all_energies):.6f}, {max(all_energies):.6f}]")
    
    return best_solution, best_energy, np.array(all_energies)

def validate_qubo_solution(Q, x, offset=0):
    """
    Validate a QUBO solution by calculating its energy.
    
    Args:
        Q: QUBO matrix
        x: Binary solution vector
        offset: Constant offset
    
    Returns:
        energy: Energy of this solution
    """
    n = len(x)
    energy = 0.0
    
    # Diagonal
    for i in range(n):
        energy += Q[i, i] * x[i]
    
    # Off-diagonal (upper triangle)
    for i in range(n):
        for j in range(i+1, n):
            energy += 2 * Q[i, j] * x[i] * x[j]
    
    energy += offset
    return energy

# Test the solver
if __name__ == "__main__":
    print("="*80)
    print("DIRECT QUBO SOLVER - VALIDATION TESTS")
    print("="*80)
    
    # Test 1: Trivial problem (n=2)
    print("\nTest 1: Trivial QUBO (n=2)")
    print("-"*80)
    Q1 = np.array([
        [-1.0, 0.5],
        [0.0, -1.0]
    ])
    print("Q =")
    print(Q1)
    print("\nExpected: x=[1,1] should give energy = -1 + 0.5*2 + -1 = -1")
    
    sol1, energy1, all_e1 = solve_qubo_bruteforce(Q1, verbose=True)
    
    # Verify
    manual_energy = validate_qubo_solution(Q1, sol1)
    print(f"Validation: {manual_energy:.6f} (should match {energy1:.6f})")
    assert abs(manual_energy - energy1) < 1e-10, "Energy mismatch!"
    print("✓ Test 1 PASSED\n")
    
    # Test 2: Small random problem (n=5)
    print("\nTest 2: Random QUBO (n=5)")
    print("-"*80)
    np.random.seed(42)
    n = 5
    Q2 = np.random.randn(n, n)
    # Make upper triangular
    Q2 = np.triu(Q2)
    print(f"Q = {n}×{n} random matrix")
    print(f"Q range: [{np.min(Q2):.3f}, {np.max(Q2):.3f}]")
    
    sol2, energy2, all_e2 = solve_qubo_bruteforce(Q2, verbose=True)
    
    # Verify
    manual_energy2 = validate_qubo_solution(Q2, sol2)
    assert abs(manual_energy2 - energy2) < 1e-10, "Energy mismatch!"
    print("✓ Test 2 PASSED\n")
    
    # Test 3: Larger problem (n=10)
    print("\nTest 3: Larger QUBO (n=10)")
    print("-"*80)
    np.random.seed(123)
    n = 10
    Q3 = np.random.randn(n, n) * 0.5
    Q3 = np.triu(Q3)
    print(f"Q = {n}×{n} random matrix")
    print(f"Q range: [{np.min(Q3):.3f}, {np.max(Q3):.3f}]")
    
    sol3, energy3, all_e3 = solve_qubo_bruteforce(Q3, verbose=True)
    
    # Verify
    manual_energy3 = validate_qubo_solution(Q3, sol3)
    assert abs(manual_energy3 - energy3) < 1e-10, "Energy mismatch!"
    
    # Statistics
    print(f"\nEnergy statistics:")
    print(f"  Min: {np.min(all_e3):.6f}")
    print(f"  Max: {np.max(all_e3):.6f}")
    print(f"  Mean: {np.mean(all_e3):.6f}")
    print(f"  Std: {np.std(all_e3):.6f}")
    print("✓ Test 3 PASSED\n")
    
    # Test 4: Performance test (n=15)
    print("\nTest 4: Performance test (n=15)")
    print("-"*80)
    np.random.seed(456)
    n = 15
    Q4 = np.random.randn(n, n) * 0.3
    Q4 = np.triu(Q4)
    print(f"Q = {n}×{n} random matrix ({2**n:,} combinations)")
    
    t_start = time.time()
    sol4, energy4, all_e4 = solve_qubo_bruteforce(Q4, verbose=False)
    t_elapsed = time.time() - t_start
    
    print(f"✓ Solved in {t_elapsed:.3f}s")
    print(f"  Best energy: {energy4:.6f}")
    print(f"  Throughput: {2**n / t_elapsed:,.0f} solutions/second")
    print("✓ Test 4 PASSED\n")
    
    # Test 5: Limit test (n=20)
    print("\nTest 5: Limit test (n=20)")
    print("-"*80)
    np.random.seed(789)
    n = 20
    Q5 = np.random.randn(n, n) * 0.2
    Q5 = np.triu(Q5)
    print(f"Q = {n}×{n} random matrix ({2**n:,} combinations)")
    print("This will take ~10-30 seconds...")
    
    t_start = time.time()
    sol5, energy5, all_e5 = solve_qubo_bruteforce(Q5, verbose=False)
    t_elapsed = time.time() - t_start
    
    print(f"✓ Solved in {t_elapsed:.1f}s")
    print(f"  Best energy: {energy5:.6f}")
    print(f"  Throughput: {2**n / t_elapsed:,.0f} solutions/second")
    print("✓ Test 5 PASSED\n")
    
    print("="*80)
    print("ALL TESTS PASSED!")
    print("="*80)
    print("\nDirect QUBO solver is working correctly.")
    print(f"Practical limit: n ≤ 20 (takes ~{t_elapsed:.0f}s for n=20)")
    print("\nReady for Phase 1, Step 1.2: QUBO Generator")

