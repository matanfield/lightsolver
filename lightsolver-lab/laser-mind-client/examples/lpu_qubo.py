####################################################################################################
# This example creates a QUBO matrix and solves it using the LPU over LightSolver's platform.
# The `solve_qubo` function is used with the following parameters:
# - `matrixData`: A 2D array representing the QUBO problem.
# - `timeout`: The required time limit for the calculation in seconds.
####################################################################################################

import numpy
import os
from laser_mind_client import LaserMind

pathToTokenFile = os.path.join(os.path.dirname(__file__), "lightsolver-token.txt")

# Create a mock QUBO problem
qubo_problem_data = numpy.random.randint(-1, 2, (10,10))

# Symmetrize our matrix
qubo_problem_data = (qubo_problem_data + qubo_problem_data.T) // 2

# Connect to the LightSolver Cloud
lsClient = LaserMind(pathToRefreshTokenFile=pathToTokenFile)

# Request a LPU solution to the QUBO problem
res = lsClient.solve_qubo_lpu(matrixData = qubo_problem_data)

# Verify response format
assert 'command' in res, "Missing 'command' field"
assert 'data' in res, "Missing 'data' field"
assert 'solutions' in res['data'], "Missing 'solutions' field"

print(f"Test PASSED, response is: \n{res}")
