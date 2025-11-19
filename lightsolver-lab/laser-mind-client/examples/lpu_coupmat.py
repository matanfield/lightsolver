####################################################################################################
# This example creates a Coupling matrix problem and solves it using the LPU over LightSolver's Platform.
# The `solve_coupling_matrix_lpu` function is used with the following parameters:
# - ```matrixData```: A 2D array representing the coupmat problem.
# - ```num_runs ```: The required number or calculation runs, default 1.
####################################################################################################

import numpy
import os
from laser_mind_client import LaserMind

pathToTokenFile = os.path.join(os.path.dirname(__file__), "lightsolver-token.txt")

# Generate a coupling matrix
size = 15
coupling_matrix = 0.5 * numpy.eye(size, dtype=numpy.complex64)
coupling = (1-0.5)/2
for i in range(size - 1):
    coupling_matrix[i,i+1] = coupling
    coupling_matrix[i+1,i] = coupling

# Connect to the LightSolver Cloud
lsClient = LaserMind(pathToRefreshTokenFile=pathToTokenFile)

# Request a LPU solution to the CoupMat problem
res = lsClient.solve_coupling_matrix_lpu(matrixData = coupling_matrix)

# Verify response format
assert 'command' in res, "Missing 'command' field"
assert 'data' in res, "Missing 'data' field"
assert 'solutions' in res['data'], "Missing 'solutions' field"

print(f"Test PASSED, response is: \n{res}")
