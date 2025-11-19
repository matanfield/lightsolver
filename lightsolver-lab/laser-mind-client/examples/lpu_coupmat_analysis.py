import numpy as np
import os
import matplotlib.pyplot as plt
from laser_mind_client import LaserMind
from lightsolver_lib import *


# Ising matrix:
I = np.array([[0., 1., 0., 0., 0.],
              [1., 0., 1., 0., 0.],
              [0., 1., 0., 1., 1.],
              [0., 0., 1., 0., 0.],
              [0., 0., 1., 0., 0.]])

coupling_matrix = coupling_matrix_xy(I, XYModelParams())         # parameters of self-coupling and coupling amplitude
                                                                 # can be set via XYmodelParams()

# Choosing how to embed a 5 laser problem onto a 15 lasers system
emedded_coupling_matrix = embed_coupmat(coupling_matrix)

print('Shape of embedded coupling matrix: ', emedded_coupling_matrix.shape)

# Initialize the client
pathToTokenFile = os.path.join(os.path.dirname(__file__), "lightsolver-token.txt") # ADD PERSONAL TOKEN HERE
lsClient = LaserMind(pathToRefreshTokenFile=pathToTokenFile)

# Solve on the LPU:
nRuns = 5       # number of times to repeat the same probelm on the LPU
result_lpu = lsClient.solve_coupling_matrix_lpu(matrixData = emedded_coupling_matrix, num_runs = nRuns)

# Getting the data for n-th run:
n = 0      # looking at run 0, for all lasers
solution = result_lpu['data']['solutions'][n]
images = np.asarray(solution['problem_image'])
phase_problem = np.asarray(solution['phase_problem'])
phase_reference = np.asarray(solution['phase_reference'])
snr_problem = solution['snr_problem']
contrast_problem = solution['contrast_problem']
contrast_reference = solution['contrast_reference']
energy_problem = solution['energy_problem']
energy_reference = solution['energy_reference']

N = I.shape[0]
phase_diffs_LPU = np.angle(np.exp(1j * phase_problem[:N]) * \
                      np.exp(-1j* phase_reference[:N])).reshape(1, N)   # subtracting reference from problem

# looking at the laser's fringes, for all lasers participating in the problem:
fig, ax = plt.subplots(nrows=1, ncols=N, figsize=(15, 5))
for i in range(I.shape[0]):
    im = ax[i].imshow(images[i, :, :])
    ax[i].axis('off')
    ax[i].set_title(f'{i}')
fig.colorbar(im, ax=ax.ravel().tolist(), orientation='vertical', shrink=0.8)
plt.show(block=False)

result_lpu = lsClient.solve_coupling_matrix_lpu(matrixData=emedded_coupling_matrix, num_runs=nRuns, exposure_time=100)

# Analyze the solution from LPU
energy, solution = analyze_sol_XY(I, phase_diffs_LPU)  # notice that matrix 'I' is sent to the function (the original Ising problem, NOT the coupling_matrix!)

print('The minimal energy found by the LPU: ', energy)
print('The corresponding state is: ', solution)