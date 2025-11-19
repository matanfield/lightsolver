####################################################################################################
# Knapsack to QUBO using pyqubo library
# Install: pip install pyqubo dwave-neal
# Run with Python 3.9: .venv-py39/bin/python knapsack_to_qubo_pyqubo.py
####################################################################################################

from pyqubo import Array
import neal
import numpy as np

# Your knapsack problem
values = [10, 13, 18, 32]
weights = [11, 15, 20, 35]
capacity = 47
n = len(values)

# Create binary decision variables
x = Array.create('x', shape=n, vartype='BINARY')

# Objective: maximize value (minimize negative)
H_obj = -sum(values[i] * x[i] for i in range(n))

# Constraint: total weight ≤ capacity
weight_sum = sum(weights[i] * x[i] for i in range(n))
H_constraint = (weight_sum - capacity)**2

# Penalty strength (rule of thumb: max_value / max_weight)
alpha = max(values) / max(weights)

# Combined Hamiltonian
H = H_obj + alpha * H_constraint

# Compile to QUBO
model = H.compile()
qubo, offset = model.to_qubo()

# Print QUBO for your LPU
print("QUBO matrix (for LPU):")
Q_matrix = np.zeros((n, n))
for (i_str, j_str), val in qubo.items():
    i = int(i_str.split('[')[1].split(']')[0])
    j = int(j_str.split('[')[1].split(']')[0])
    Q_matrix[i, j] = val

print(Q_matrix)
print(f"\nOffset: {offset}")

# Solve with simulated annealing (to verify)
sampler = neal.SimulatedAnnealingSampler()
sampleset = sampler.sample_qubo(qubo, num_reads=100)
decoded = model.decode_sampleset(sampleset)
best = min(decoded, key=lambda x: x.energy)

# Display solution
selected = [i for i in range(n) if best.sample[f'x[{i}]'] == 1]
print(f"\nBest solution: items {selected}")
print(f"Total value: {sum(values[i] for i in selected)}")
print(f"Total weight: {sum(weights[i] for i in selected)}")
print(f"Capacity: {capacity}")

