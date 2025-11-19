# Async solve example using simLPU (async works with any solver)

import numpy
import os
from laser_mind_client_meta import MessageKeys
from laser_mind_client import LaserMind

pathToTokenFile = os.path.join(os.path.dirname(__file__), "lightsolver-token.txt")

# Create coupling matrix
size = 6
coupling_matrix = 0.5 * numpy.eye(size, dtype=numpy.complex64)
coupling = (1-0.5)/2
for i in range(size - 1):
    coupling_matrix[i, i + 1] = coupling
    coupling_matrix[i + 1, i] = coupling

# Connect and start async solve
lsClient = LaserMind(pathToRefreshTokenFile=pathToTokenFile)
requestToken = lsClient.solve_coupling_matrix_sim_lpu(
    matrix_data=coupling_matrix,
    num_runs=3,
    num_iterations=10,
    rounds_per_record=5,
    timeout=5,
    waitForSolution=False
)

# Other code can run here while server processes the request

# Retrieve solution (blocks until ready)
res = lsClient.get_solution_sync(requestToken)

assert 'data' in res, "Test FAILED, response is not in expected format"
assert 'result' in res['data'], "Test FAILED, result not found in response data"
assert 'start_states' in res['data']['result'], "Test FAILED, start_states not found in result"
assert 'final_states' in res['data']['result'], "Test FAILED, final_states not found in result"
assert 'record_states' in res['data']['result'], "Test FAILED, record_states not found in result"
assert 'record_gains' in res['data']['result'], "Test FAILED, record_gains not found in result"

print(f"Test PASSED, response is: \n{res}")
