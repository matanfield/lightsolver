import numpy as np
from laser_mind_client import LaserMind
from lightsolver_lib import *
import os

# Example: Constructing the coupling matrix for the QUBO problem

# Define QUBO coefficients
Q = np.array([[ -4,   4,   0,   0,   0],
              [  4,  -8,   4,   0,   0],
              [  0,   4, -12,   4,   4],
              [  0,   0,   4,  -4,   0],
              [  0,   0,   4,   0,  -4]])
offset_QUBO = 8

# The corresponding Ising matrix:
I, offset_Ising = probmat_qubo_to_ising(Q, offset_QUBO)

print('Ising matrix:')
print(I)
print('Ising offset: ', offset_Ising)

coupling_matrix = coupling_matrix_xy(I, XYmodelParams())

print('Coupling Matrix:')
print(coupling_matrix)

# Make sure that the sum of the absolute value of each row < 1:
row_sums = np.abs(coupling_matrix).sum(axis=0)
is_smaller_than_one = (row_sums < 1).all()
print('sums are smaller than one:', is_smaller_than_one)

pathToTokenFile = os.path.join(os.path.dirname(__file__), "lightsolver-token.txt")
lsClient = LaserMind(pathToRefreshTokenFile=pathToTokenFile)
result = lsClient.solve_coupling_matrix_sim_lpu(matrix_data=coupling_matrix.astype(np.complex64), num_runs=10, num_iterations=1000, rounds_per_record=1)

start_states = result['data']['result']['start_states']     # dims: num_runs x num_lasers
final_states = result['data']['result']['final_states']     # dims: num_runs x num_lasers
final_gains = result['data']['result']['final_gains']       # dims: num_runs x num_lasers
record_states = result['data']['result']['record_states']   # dims: num_records x num_runs x num_lasers
record_gains = result['data']['result']['record_gains']     # dims: num_records x num_runs x num_lasers

# Grabbing just one of the runs, for all lasers, every iteration:
outWave = record_states[:, 0, :]    # iterations x lasers (since rounds_per_record = 1)

# Generating animation:
generateAnimation(outWave, save=False)

# Search for the best state:
best_state, best_energy = best_energy_search_xy(outWave[:, 0, -1], I)

# Transform Ising best state to QUBO best state:
QUBO_best_state = (best_state + 1) / 2

print('QUBO best state: ', QUBO_best_state)