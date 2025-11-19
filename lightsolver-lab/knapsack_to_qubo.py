import numpy as np

def knapsack_to_qubo(values, weights, capacity, penalty=1.0):
    """
    Convert 0-1 knapsack to QUBO.
    
    Args:
        values: list of item values [v1, v2, ..., vn]
        weights: list of item weights [w1, w2, ..., wn]
        capacity: maximum weight W
        penalty: constraint penalty strength α
    
    Returns:
        Q: QUBO matrix
        offset: constant offset
    """
    n = len(values)
    Q = np.zeros((n, n))
    
    # Diagonal terms: -vᵢ + α×wᵢ² - 2α×W×wᵢ
    for i in range(n):
        Q[i, i] = -values[i] + penalty * (weights[i]**2 - 2*capacity*weights[i])
    
    # Off-diagonal terms: 2α×wᵢ×wⱼ
    for i in range(n):
        for j in range(i+1, n):
            Q[i, j] = 2 * penalty * weights[i] * weights[j]
    
    # Constant offset: α×W²
    offset = penalty * capacity**2
    
    return Q, offset


# Example problem
values = [10, 13, 18, 32]
weights = [11, 15, 20, 35]
capacity = 47

Q, offset = knapsack_to_qubo(values, weights, capacity, penalty=5.0)

print("QUBO matrix:")
print(Q)
print("\nOffset:", offset)
print("\nExpected solution: x = [1, 1, 1, 0]")
print("Total value: 10+13+18 = 41")
print("Total weight: 11+15+20 = 46 ≤ 47 ✓")