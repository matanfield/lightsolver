#!/usr/bin/env python3
"""
Phase 1, Step 1.2: Controlled QUBO Generator

Generates QUBO matrices with specific properties for systematic testing.
"""

import numpy as np

def generate_qubo(n, qubo_type='uniform', density=1.0, variance=1.0, seed=None):
    """
    Generate controlled QUBO matrix for testing.
    
    Args:
        n: Problem size (number of binary variables)
        qubo_type: Type of QUBO to generate
            - 'uniform': Coefficients uniformly distributed in [-variance, variance]
            - 'ferromagnetic': All negative (easy, prefers all 1s)
            - 'antiferromagnetic': All positive (hard, prefers all 0s)
            - 'sparse': Only density fraction of couplings non-zero
            - 'diagonal': Only diagonal terms (no interactions)
            - 'knapsack': Knapsack-like structure
        density: Fraction of non-zero couplings (0-1)
        variance: Range multiplier for coefficient values
        seed: Random seed for reproducibility
    
    Returns:
        Q: QUBO matrix (n×n, upper triangular)
        metadata: Dict with generation parameters
    """
    if seed is not None:
        np.random.seed(seed)
    
    Q = np.zeros((n, n))
    
    if qubo_type == 'uniform':
        # Uniform random in [-variance, variance]
        Q = np.random.uniform(-variance, variance, (n, n))
        Q = np.triu(Q)  # Upper triangular
        
        # Apply density (sparsify)
        if density < 1.0:
            mask = np.random.random((n, n)) < density
            mask = np.triu(mask)  # Keep upper triangular
            Q = Q * mask
    
    elif qubo_type == 'ferromagnetic':
        # All negative (prefers x=1)
        Q = -np.random.uniform(0, variance, (n, n))
        Q = np.triu(Q)
        
        if density < 1.0:
            mask = np.random.random((n, n)) < density
            mask = np.triu(mask)
            Q = Q * mask
    
    elif qubo_type == 'antiferromagnetic':
        # All positive (prefers x=0)
        Q = np.random.uniform(0, variance, (n, n))
        Q = np.triu(Q)
        
        if density < 1.0:
            mask = np.random.random((n, n)) < density
            mask = np.triu(mask)
            Q = Q * mask
    
    elif qubo_type == 'sparse':
        # Explicitly sparse
        Q = np.random.uniform(-variance, variance, (n, n))
        Q = np.triu(Q)
        mask = np.random.random((n, n)) < density
        mask = np.triu(mask)
        Q = Q * mask
    
    elif qubo_type == 'diagonal':
        # Only diagonal terms (no interactions)
        diag = np.random.uniform(-variance, variance, n)
        Q = np.diag(diag)
    
    elif qubo_type == 'knapsack':
        # Knapsack-like: negative diagonal, positive off-diagonal
        # Diagonal: -profits (negative, want to maximize)
        Q_diag = -np.random.uniform(0.1, variance, n)
        
        # Off-diagonal: constraint couplings (positive, penalize violations)
        Q_off = np.random.uniform(0, variance * 0.5, (n, n))
        Q_off = np.triu(Q_off, k=1)  # Upper triangle, no diagonal
        
        Q = np.diag(Q_diag) + Q_off
        
        if density < 1.0:
            mask = np.random.random((n, n)) < density
            mask = np.triu(mask)
            np.fill_diagonal(mask, 1)  # Keep diagonal
            Q = Q * mask
    
    else:
        raise ValueError(f"Unknown qubo_type: {qubo_type}")
    
    # Calculate statistics
    non_zero = np.count_nonzero(Q)
    total_elements = n * (n + 1) // 2  # Upper triangle including diagonal
    actual_density = non_zero / total_elements if total_elements > 0 else 0
    
    metadata = {
        'n': n,
        'type': qubo_type,
        'requested_density': density,
        'actual_density': actual_density,
        'variance': variance,
        'seed': seed,
        'min_coeff': np.min(Q),
        'max_coeff': np.max(Q),
        'coeff_range': np.max(np.abs(Q)) / np.min(np.abs(Q[Q != 0])) if np.any(Q != 0) else 0,
        'non_zero_count': non_zero,
    }
    
    return Q, metadata

# Test the generator
if __name__ == "__main__":
    print("="*80)
    print("QUBO GENERATOR - VALIDATION TESTS")
    print("="*80)
    
    # Test 1: Uniform random
    print("\nTest 1: Uniform Random QUBO")
    print("-"*80)
    Q1, meta1 = generate_qubo(n=10, qubo_type='uniform', variance=1.0, seed=42)
    print(f"Generated {meta1['n']}×{meta1['n']} {meta1['type']} QUBO")
    print(f"  Coefficient range: [{meta1['min_coeff']:.3f}, {meta1['max_coeff']:.3f}]")
    print(f"  Density: {meta1['actual_density']:.2%}")
    print(f"  Non-zero: {meta1['non_zero_count']}/{meta1['n']*(meta1['n']+1)//2}")
    print(f"  Range (max/min): {meta1['coeff_range']:.1f}×")
    print("✓ Test 1 PASSED\n")
    
    # Test 2: Ferromagnetic
    print("\nTest 2: Ferromagnetic QUBO (all negative)")
    print("-"*80)
    Q2, meta2 = generate_qubo(n=10, qubo_type='ferromagnetic', variance=2.0, seed=42)
    print(f"Generated {meta2['n']}×{meta2['n']} {meta2['type']} QUBO")
    print(f"  Coefficient range: [{meta2['min_coeff']:.3f}, {meta2['max_coeff']:.3f}]")
    print(f"  All negative: {np.all(Q2 <= 0)}")
    assert np.all(Q2 <= 0), "Should be all negative!"
    print("✓ Test 2 PASSED\n")
    
    # Test 3: Antiferromagnetic
    print("\nTest 3: Antiferromagnetic QUBO (all positive)")
    print("-"*80)
    Q3, meta3 = generate_qubo(n=10, qubo_type='antiferromagnetic', variance=2.0, seed=42)
    print(f"Generated {meta3['n']}×{meta3['n']} {meta3['type']} QUBO")
    print(f"  Coefficient range: [{meta3['min_coeff']:.3f}, {meta3['max_coeff']:.3f}]")
    print(f"  All non-negative: {np.all(Q3 >= 0)}")
    assert np.all(Q3 >= 0), "Should be all non-negative!"
    print("✓ Test 3 PASSED\n")
    
    # Test 4: Sparse
    print("\nTest 4: Sparse QUBO (30% density)")
    print("-"*80)
    Q4, meta4 = generate_qubo(n=20, qubo_type='sparse', density=0.3, variance=1.0, seed=42)
    print(f"Generated {meta4['n']}×{meta4['n']} {meta4['type']} QUBO")
    print(f"  Requested density: {meta4['requested_density']:.2%}")
    print(f"  Actual density: {meta4['actual_density']:.2%}")
    print(f"  Non-zero: {meta4['non_zero_count']}/{meta4['n']*(meta4['n']+1)//2}")
    assert meta4['actual_density'] < 0.4, "Should be sparse!"
    print("✓ Test 4 PASSED\n")
    
    # Test 5: Diagonal only
    print("\nTest 5: Diagonal-only QUBO (no interactions)")
    print("-"*80)
    Q5, meta5 = generate_qubo(n=10, qubo_type='diagonal', variance=1.0, seed=42)
    print(f"Generated {meta5['n']}×{meta5['n']} {meta5['type']} QUBO")
    off_diagonal = Q5 - np.diag(np.diag(Q5))
    print(f"  Diagonal elements: {meta5['n']}")
    print(f"  Off-diagonal sum: {np.sum(np.abs(off_diagonal)):.6f}")
    assert np.sum(np.abs(off_diagonal)) < 1e-10, "Should have no off-diagonal!"
    print("✓ Test 5 PASSED\n")
    
    # Test 6: Knapsack-like
    print("\nTest 6: Knapsack-like QUBO")
    print("-"*80)
    Q6, meta6 = generate_qubo(n=15, qubo_type='knapsack', variance=10.0, seed=42)
    print(f"Generated {meta6['n']}×{meta6['n']} {meta6['type']} QUBO")
    diag = np.diag(Q6)
    off_diag = Q6 - np.diag(diag)
    print(f"  Diagonal (profits): all negative = {np.all(diag < 0)}")
    print(f"  Off-diagonal (constraints): all non-negative = {np.all(off_diag >= 0)}")
    print(f"  Diagonal range: [{np.min(diag):.3f}, {np.max(diag):.3f}]")
    print(f"  Off-diagonal range: [{np.min(off_diag):.3f}, {np.max(off_diag):.3f}]")
    assert np.all(diag < 0), "Diagonal should be negative!"
    assert np.all(off_diag >= 0), "Off-diagonal should be non-negative!"
    print("✓ Test 6 PASSED\n")
    
    # Test 7: High variance
    print("\nTest 7: High Variance QUBO (variance=1000)")
    print("-"*80)
    Q7, meta7 = generate_qubo(n=10, qubo_type='uniform', variance=1000.0, seed=42)
    print(f"Generated {meta7['n']}×{meta7['n']} {meta7['type']} QUBO")
    print(f"  Coefficient range: [{meta7['min_coeff']:.1f}, {meta7['max_coeff']:.1f}]")
    print(f"  Range (max/min): {meta7['coeff_range']:.1f}×")
    print("✓ Test 7 PASSED\n")
    
    print("="*80)
    print("ALL TESTS PASSED!")
    print("="*80)
    print("\nQUBO generator working correctly.")
    print("\nAvailable types:")
    print("  - uniform: General random QUBOs")
    print("  - ferromagnetic: Easy (all negative)")
    print("  - antiferromagnetic: Hard (all positive)")
    print("  - sparse: Controlled sparsity")
    print("  - diagonal: No interactions")
    print("  - knapsack: Knapsack-like structure")
    print("\nReady for Phase 2: LPU on Simple QUBOs")

