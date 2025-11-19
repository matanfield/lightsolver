import numpy
from laser_mind_client import LaserMind
import os

pathToTokenFile = os.path.join(os.path.dirname(__file__), "lightsolver-token.txt")

size = 6
coupling_matrix6 = 0.5 * numpy.eye(size, dtype=numpy.complex64)
coupling = (1-0.5)/2
for i in range(size - 1):
    coupling_matrix6[i, i + 1] = coupling
    coupling_matrix6[i + 1, i] = coupling

size = 1000
coupling_matrix1000 = 0.5 * numpy.eye(size, dtype=numpy.complex64)
for i in range(size - 1):
    coupling_matrix1000[i, i + 1] = coupling
    coupling_matrix1000[i + 1, i] = coupling


def test_solve_coupmat_sanity_sim_lpu():
    # matrix in range, but not allowed for default user
    lsClient = LaserMind(pathToRefreshTokenFile=pathToTokenFile)
    res = lsClient.solve_coupling_matrix_sim_lpu(matrix_data=coupling_matrix6, num_runs=3, num_iterations=10, rounds_per_record=5)
    print(res)

    assert 'data' in res
    assert 'result' in res['data']
    assert 'start_states' in res['data']['result']
    assert 'final_states' in res['data']['result']
    assert 'record_states' in res['data']['result']
    assert 'record_gains' in res['data']['result']
    print("Test PASSED")


def test_solve_coupmat_sanity_1000_sim_lpu():
    lsClient = LaserMind(pathToRefreshTokenFile=pathToTokenFile)
    res = lsClient.solve_coupling_matrix_sim_lpu(matrix_data=coupling_matrix1000, num_runs=1, num_iterations=100, rounds_per_record=10)
    print(res)

    assert 'data' in res
    assert 'result' in res['data']
    assert 'start_states' in res['data']['result']
    assert 'final_states' in res['data']['result']
    assert 'record_states' in res['data']['result']
    assert 'record_gains' in res['data']['result']


def test_solve_coupmat_sanity_sim_lpu_start_state():
    lsClient = LaserMind(pathToRefreshTokenFile=pathToTokenFile)
    start_states = [[1.0000000e+00+0.0000000e+00j, 3.1520671e-05-6.6747067e-05j,
                     3.2637545e-04+1.3825409e-05j, 6.6705397e-04+5.1987998e-04j,
                     -1.7934688e-04-9.9081466e-05j, -7.9448699e-05+2.8152767e-04j],
                    [1.0000000e+00+0.0000000e+00j, -1.3137888e-05-8.1989256e-06j,
                     4.2760934e-04+7.6702039e-04j, -3.0936502e-04+3.0431763e-04j,
                     -4.6269799e-04-6.0939678e-04j, 4.1850499e-04+4.3996374e-04j],
                    [1.0000000e+00+0.0000000e+00j, 3.3563105e-04+2.8073095e-04j,
                     5.0876173e-04+2.1346097e-04j, -6.1887660e-04+6.3852035e-04j,
                     -2.2033586e-04+6.9595524e-04j, 3.9103298e-04+8.9563327e-05j]]

    # Convert it
    start_states_array = numpy.array(start_states, dtype=numpy.complex64)

    res = lsClient.solve_coupling_matrix_sim_lpu(matrix_data=coupling_matrix6, initial_states_vector=start_states_array, num_iterations=10, rounds_per_record=5)
    print(res)

    assert 'data' in res
    assert 'result' in res['data']
    assert 'start_states' in res['data']['result']
    assert 'final_states' in res['data']['result']
    assert 'record_states' in res['data']['result']
    assert 'record_gains' in res['data']['result']


def test_solve_coupmat_sanity_sim_lpu_gain_info():
    # matrix in range, but not allowed for default user
    lsClient = LaserMind(pathToRefreshTokenFile=pathToTokenFile)
    res = lsClient.solve_coupling_matrix_sim_lpu(matrix_data=coupling_matrix6,
                                               num_runs=1,
                                               num_iterations=2,
                                               rounds_per_record=1,
                                               gain_info_initial_gain=1.9,
                                               gain_info_pump_max=3,
                                               gain_info_pump_tau=700.0,
                                               gain_info_pump_treshold=1.8,
                                               gain_info_amplification_saturation=1.0)
    print(res)

    assert 'data' in res
    assert 'result' in res['data']
    assert 'start_states' in res['data']['result']
    assert 'final_states' in res['data']['result']
    assert 'record_states' in res['data']['result']
    assert 'record_gains' in res['data']['result']

if __name__ == "__main__":
    # todo split into separate files per test
    test_solve_coupmat_sanity_sim_lpu()