####################################################################################################
# This example creates a Coupling matrix problem and solves it using the LPU over LightSolver's Platform.
# The `solve_coupling_matrix_lpu` function is used with the following parameters:
# - ```matrixData```: A 2D array representing the coupmat problem.
# - ```num_runs ```: The required number or calculation runs, default 1.
####################################################################################################

import numpy
import os
from laser_mind_client import LaserMind

import matplotlib.pyplot as plt

pathToTokenFile = os.path.join(os.path.dirname(__file__), "lightsolver-token.txt")

# Generate a coupling matrix
size5 = 5
coupling_matrix = 0.5 * numpy.eye( size5 ,dtype=numpy.complex64)
coupling = (1-0.5)/(2)
for i in range(size5 - 1):
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
assert 'problem_image' in res['data']['solutions'][0]
assert 'exposure_time' in res['data']


problem_image = res['data']['solutions'][0]['problem_image']
problem_image_arr = numpy.asarray(problem_image)          # make it a NumPy array
print("shape:", problem_image_arr.shape)

# exposure_time from the system, can be changed in parameter
print("exposure_time: " , res['data']['exposure_time'])

plt.figure()
plt.imshow(problem_image_arr[1, :, :]) # first batch, first channel
plt.axis('off')
plt.show()

print(f"Test PASSED, response is: \n{res}")
