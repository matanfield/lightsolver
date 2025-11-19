import os
import logging
import time
import numpy
import requests

from ls_api_clients import LSAPIClient
from ls_packers import float_array_as_int
from ls_packers import numpy_array_to_triu_flat
from laser_mind_client_meta import MessageKeys

def serialize_complex_array(arr: numpy.ndarray):
    """
    Serialize a complex numpy array into a dict with real and imag parts.
    """
    if not numpy.iscomplexobj(arr):
        raise ValueError("Array must be complex type.")

    return {
        "real": arr.real.tolist(),
        "imag": arr.imag.tolist()
}


def deserialize_complex_array(data: dict) -> numpy.ndarray:
    """
    Takes a dictionary with 'real' and 'imag' keys and returns a numpy.complex64 array.
    """
    real = numpy.array(data['real'], dtype=numpy.float32)
    imag = numpy.array(data['imag'], dtype=numpy.float32)
    return real + 1j * imag

def deserialize_complex_matrix(raw_data: dict) -> numpy.ndarray:
    """
    Takes a dictionary with 'real' and 'imag' keys and returns a numpy.complex64 matrix.
    """

    reconstructed = numpy.array(raw_data['real']) + 1j * numpy.array(raw_data['imag'])
    try:
        raw_matrix = reconstructed.reshape(raw_data['size'],raw_data['size'])
    except Exception as e:
        logging.error(f"Complex matrix  reconstruction failed for size {raw_data['size']} : {str(e)}")
        raise e
    return raw_matrix

logging.basicConfig(
    filename="laser-mind.log",
    level=logging.INFO,
    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')

def symmetrize(matrix):
        """
        Symmetrizes a given matrix in numpy array form
        """
        if (matrix == matrix.T).all():
        # do nothing if the matrix is already symmetric
            return matrix
        result = (matrix + matrix.T) * 0.5
        return result

class LaserMind:
    """
    ## A client for accessing LightSolver's computaion capabilities via web services.
    """
    POLL_MAX_RETRIES = 100000
    POLL_DELAY_SECS = 0.5

    def __init__(self,
                 userToken=None,
                 pathToRefreshTokenFile=None,
                 logToConsole=True):
        refresh_token = None
        if pathToRefreshTokenFile:
            if os.path.exists(pathToRefreshTokenFile):
                with open(pathToRefreshTokenFile) as file:
                    refresh_token = file.read()
            else:
                raise Exception("The pathToRefreshTokenFile parameter is expected to point to a valid file.")

        try:
            logging.info('LightSolver connection init started')
            self.apiClient = LSAPIClient(usertoken = userToken, refresh_token = refresh_token, logToConsole = logToConsole)
            logging.info('LightSolver connection init finished')
        except requests.exceptions.ConnectionError as e:
            raise Exception("!!!!! No access to LightSolver Cloud. !!!!!")
        except Exception as e:
                raise  e

    def get_solution_by_id(self, solutionId, timestamp):
        """
        Retrieve a previously requested solution from the LightSolver cloud.

        - `solutionId` : the solution id received when requesting a solution.
        - `timestamp` : the timestamp received when requesting a solution.
        """
        result = self.apiClient.SendResultRequest(solutionId, timestamp)
        return result

    def get_solution_sync(self, requestInfo):
        """
        Waits for a solution to be available and downloads it.

        - `requestInfo` : a dictionary containing 'id' and 'reqTime' keys needed for retrieving the solution.
        """
        for try_num in range(1, self.POLL_MAX_RETRIES):
            result = self.get_solution_by_id(requestInfo['id'], requestInfo['reqTime'])
            if result != None:
                result["receivedTime"] = requestInfo["receivedTime"]
                logging.info(f"got solution for {requestInfo}, try #{try_num}")
                return result
            time.sleep((self.POLL_DELAY_SECS))

        logging.warning(f"got timeout for {requestInfo}")
        raise FileNotFoundError(f"Exceeded max retries when attempting to find {requestInfo['id']}")

    def make_command_input(self, matrixData = None, edgeList = None, timeout = 10):
        """
        Creates the message payload for a request input.
        """
        commandInput = {}

        if matrixData is not None:
            varCount = len(matrixData)
            if varCount > 10000 or varCount < 10:
                raise(ValueError("The total number of variables must be between 10-10000"))
            if type(matrixData) == numpy.ndarray:
                matrixData = symmetrize(matrixData)
                if matrixData.dtype == numpy.float32 or matrixData.dtype == numpy.float64:
                    triuFlat = float_array_as_int(numpy_array_to_triu_flat(matrixData))
                    commandInput[MessageKeys.FLOAT_DATA_AS_INT] = True
                else:
                    triuFlat = numpy_array_to_triu_flat(matrixData)
            else:
                validationArr = [len(matrixData[i]) != varCount for i in range(varCount)]
                if numpy.array(validationArr).any():
                    raise(ValueError("The input must be a square matrix"))
                triuFlat = numpy_array_to_triu_flat(symmetrize(numpy.array(matrixData)))
            commandInput[MessageKeys.QUBO_MATRIX] = triuFlat.tolist()
        elif edgeList is not None:
            if type(edgeList) == numpy.ndarray:
                varCount = numpy.max(edgeList[:,0:2])
                edgeList = edgeList.tolist()
            else:
                varCount = numpy.max(numpy.array(edgeList)[:,0:2])
            if varCount > 10000 or varCount < 10:
                raise(ValueError("The total number of variables must be between 10-10000"))
            commandInput[MessageKeys.QUBO_EDGE_LIST] = edgeList
        else:
            raise Exception("You must provide either a QUBO matrix or a QUBO edge list")

        commandInput[MessageKeys.ALGO_RUN_TIMEOUT] = timeout
        return commandInput, int(varCount)

    def upload_qubo_input(self, matrixData = None, edgeList = None, timeout = 10, inputPath = None):
        """
        Uploads the given input to the lightsolver cloud for later processing.

        - `matrixData` : (optional) The matrix data of the target problem, must be a symmetric matrix. if given, the edge list in the vortex parameters is ignored.
        - `edgeList` : (optional) The edge list describing Ising matrix of the target problem. if the matrixData parameter is given, this parameter is ignored.
        - `timeout` : (optional) the running timeout, in seconds for the algorithm, must be in the range 0.001 - 60 (default: 10).
        - `inputPath` : (optional) The the path to a pre-uploaded input file if not given a random string is used returned.

        Returns a dictionary with the 'data' key being a dictionary representing the solution using the following keys:
        - `iid` : The id of the uploaded file.
        - `varCount` : The amount number of variables of the problem.

        """
        try:
            commandInput, varCount = self.make_command_input(matrixData, edgeList, timeout)

            iid = self.apiClient.upload_command_input(commandInput, inputPath)
            return iid, varCount
        except requests.exceptions.ConnectionError as e:
            raise Exception("!!!!! No access to LightSolver Cloud. !!!!!")
        except Exception as e:
                raise  e

    def solve_qubo(self, matrixData = None, edgeList = None, inputPath = None, timeout = 10, waitForSolution = True):
        """
        Solves a qubo problem using the optimized algorithm.

        - `matrixData` : (optional) The matrix data of the target problem, must be a symmetric matrix. if given, the edge list in the vortex parameters is ignored.
        - `edgeList` : (optional) The edge list describing Ising matrix of the target problem. if the matrixData parameter is given, this parameter is ignored.
        - `inputPath` : (optional) The the path to a pre-uploaded input file, the upload can be done using the upload_qubo_input() method of this class.
        - `timeout` : (optional) the running timeout, in seconds for the algorithm, must be in the range 0.001 - 60 (default: 10).
        - `waitForSolution` : (optional) When set to True it waits for the solution, else returns with retrieval info (default: True).

        Returns a dictionary with the 'data' key being a dictionary representing the solution using the following keys:
        - `objval` : The objective value.
        - `solution` : The optimal solution found.
        """
        command_name = MessageKeys.QUBO_COMMAND_NAME
        if inputPath == None:
            iid, varCount = self.upload_qubo_input(matrixData, edgeList, timeout)
        else:
            iid = inputPath
            varCount = 10000

        requestInput = {
            MessageKeys.QUBO_INPUT_PATH : iid,
            MessageKeys.ALGO_RUN_TIMEOUT : timeout,
            MessageKeys.VAR_COUNT_KEY : varCount
            }
        try:
            response = self.apiClient.SendCommandRequest(command_name, requestInput)
            logging.info(f"got response {response}")
            if not waitForSolution:
                return response
            result = self.get_solution_sync(response)
            return result
        except requests.exceptions.ConnectionError as e:
            raise Exception("!!!!! No access to LightSolver Cloud. !!!!!")
        except Exception as e:
                raise  e


    def get_account_details(self):
        requestInput = {}
        try:
            response = self.apiClient.SendCommandRequest("get_account_details", requestInput)
        except requests.exceptions.ConnectionError as e:
            raise  Exception("!!!!! No access to LightSolver Cloud, WEB server !!!!!")
        except Exception as e:
            raise  e
        logging.info(f"got response {response}")
        return response


    def solve_qubo_lpu(self, matrixData = None, edgeList = None, waitForSolution = True, inputPath = None, num_runs = 1 ):
        if inputPath == None:
            iid, varCount = self.upload_lpu_qubo_input(matrix_data = matrixData, edge_list = edgeList)
        else:
            iid = inputPath
            varCount = 100

        requestInput = {
            MessageKeys.QUBO_INPUT_PATH : iid,
            MessageKeys.VAR_COUNT_KEY : varCount,
            MessageKeys.LPU_NUM_RUNS : num_runs
            }

        try:
            response = self.apiClient.SendCommandRequest("LPUSolver_QUBOFull", requestInput)
        except requests.exceptions.ConnectionError as e:
            raise  Exception("!!!!! No access to LightSolver Cloud, WEB server !!!!!")
        except Exception as e:
            raise  e

        logging.info(f"got response {response}")
        if not waitForSolution:
            return response

        try:
            result = self.get_solution_sync(response)
            return result
        except requests.exceptions.ConnectionError   as e:
            raise  Exception("!!!!! No access to LightSolver Cloud, SOLUTION server !!!!!")
        except Exception as e:
            raise  e


    def solve_coupling_matrix_lpu(self,
                                  matrixData = None,
                                  edgeList = None,
                                  waitForSolution = True,
                                  inputPath = None,
                                  num_runs = 1,
                                  average_over = 1,
                                  exposure_time= None,
                                  num_neighbors = 1,
                                  effective_coupmat_translation_accuracy = 10.0,
                                  effective_coupmat_translation_time = 0.0
                                  ):
        if inputPath == None:
            iid, varCount = self.upload_lpu_coupmat_input(matrix_data= matrixData, edge_list = edgeList)
        else:
            iid = inputPath
            varCount = 100

        requestInput = {
            MessageKeys.QUBO_INPUT_PATH : iid,
            MessageKeys.VAR_COUNT_KEY : varCount,
            MessageKeys.LPU_NUM_RUNS : num_runs,
            MessageKeys.LPU_AVERAGE_OVER : average_over,
            MessageKeys.LPU_COUPMAT_NUM_NEIGHBORS : num_neighbors,
            MessageKeys.LPU_COUPMAT_ETA : effective_coupmat_translation_accuracy,
            MessageKeys.LPU_COUPMAT_ETT : effective_coupmat_translation_time
            }

        if exposure_time:
             requestInput[MessageKeys.LPU_COUPMAT_EXPOSURE_MUS] =  int(exposure_time)

        try:
            response = self.apiClient.SendCommandRequest("LPUSolver_Coupmat", requestInput)
        except requests.exceptions.ConnectionError as e:
            raise  Exception("!!!!! No access to LightSolver Cloud, WEB server !!!!!")
        except Exception as e:
            raise  e

        logging.info(f"got response {response}")
        if not waitForSolution:
            return response

        try:
            result = self.get_solution_sync(response)
            if "effective_coupmat" in result['data']:
                result['data']['effective_coupmat'] = deserialize_complex_matrix(result['data']['effective_coupmat'])
            return result
        except requests.exceptions.ConnectionError   as e:
            raise  Exception("!!!!! No access to LightSolver Cloud, SOLUTION server !!!!!")
        except Exception as e:
            raise  e


    def upload_lpu_qubo_input(self, matrix_data = None, edge_list = None, input_path = None):
        command_input = {}
        if matrix_data is not None:
            var_count = len(matrix_data)

            if type(matrix_data) == numpy.ndarray:
                matrix_data = symmetrize(matrix_data)
                if matrix_data.dtype == numpy.float32 or matrix_data.dtype == numpy.float64:
                    triu_flat = float_array_as_int(numpy_array_to_triu_flat(matrix_data))
                    command_input[MessageKeys.FLOAT_DATA_AS_INT] = True
                else:
                    triu_flat = numpy_array_to_triu_flat(matrix_data)
            else:
                validationArr = [len(matrix_data[i]) != var_count for i in range(var_count)]
                if numpy.array(validationArr).any():
                    raise(ValueError("The input must be a square matrix"))
                triu_flat = numpy_array_to_triu_flat(symmetrize(numpy.array(matrix_data)))
            command_input[MessageKeys.QUBO_MATRIX] = triu_flat.tolist()

        elif edge_list is not None:
            if type(edge_list) == numpy.ndarray:
                var_count = numpy.max(edge_list[:,0:2])
                edge_list = edge_list.tolist()
            else:
                var_count = numpy.max(numpy.array(edge_list)[:,0:2])
            command_input[MessageKeys.QUBO_EDGE_LIST] = edge_list

        else:
            raise (ValueError("You must provide either a QUBO matrix or a QUBO edge list"))

        try:
            iid = self.apiClient.upload_command_input(command_input, input_path)
            return iid, int(var_count)
        except requests.exceptions.ConnectionError as e:
            raise  Exception("!!!!! No access to LightSolver Cloud, URL PROVIDER server !!!!!")
        except Exception as e:
            raise  e


    def upload_lpu_coupmat_input(self, matrix_data = None, edge_list = None, input_path = None):
        command_input = {}
        if matrix_data is not None:
            var_count = len(matrix_data)
            if type(matrix_data) == numpy.ndarray:
                if matrix_data.dtype == numpy.complex64:
                    a = matrix_data.flatten()
                    # Combine real and imaginary parts for serialization
                    real_part = a.real.tolist()
                    imag_part = a.imag.tolist()
                    combined = {'real': real_part, 'imag': imag_part,'size':var_count}
                    command_input[MessageKeys.COUPMAT_MATRIX] = combined

                else:
                        raise(TypeError("The input must complex64 type"))
            else:
                raise(TypeError("The input must be a numpy array"))
        elif edge_list is not None:
            raise (TypeError("Edge List not supported as coup_matrix input"))

        try:
            iid = self.apiClient.upload_command_input(command_input, input_path)
            return iid, int(var_count)

        except requests.exceptions.ConnectionError as e:
            raise  Exception("!!!!! No access to LightSolver Cloud, URL PROVIDER server !!!!!")
        except Exception as e:
            raise  e


    def solve_coupling_matrix_sim_lpu(self,
                                      matrix_data  = None,
                                      initial_states_seed = -1,
                                      initial_states_vector = None,
                                      num_runs = 1,
                                      num_iterations = 10000,
                                      rounds_per_record  = 100,
                                      timeout  = 5,
                                      waitForSolution = True,
                                      gain_info_initial_gain = 1.8 ,
                                      gain_info_pump_max = 3 ,
                                      gain_info_pump_tau = 100.0 ,
                                      gain_info_pump_treshold = 1.8 ,
                                      gain_info_amplification_saturation = 1.0 ,
                                      inputPath = None):
        if inputPath == None:
            iid, varCount = self.upload_sim_lpu_coupmat_input(  matrix_data,
                                                                initial_states_seed = initial_states_seed,
                                                                initial_states_vector = initial_states_vector,
                                                                num_runs = num_runs,
                                                                num_iterations = num_iterations,
                                                                rounds_per_record = rounds_per_record,
                                                                timeout  = timeout,
                                                                gain_info_initial_gain = gain_info_initial_gain,
                                                                gain_info_pump_max = gain_info_pump_max ,
                                                                gain_info_pump_tau = gain_info_pump_tau,
                                                                gain_info_pump_treshold = gain_info_pump_treshold ,
                                                                gain_info_amplification_saturation = gain_info_amplification_saturation  )
        else:
            iid = inputPath
            varCount = 100

        requestInput = {
            MessageKeys.QUBO_INPUT_PATH : iid,
            MessageKeys.VAR_COUNT_KEY : varCount,
            MessageKeys.LPU_NUM_RUNS : num_runs
            }

        try:
            response = self.apiClient.SendCommandRequest("SIMLPUSolver_Coupmat", requestInput)
        except requests.exceptions.ConnectionError as e:
            raise  Exception("!!!!! No access to LightSolver Cloud, WEB server !!!!!")
        except Exception as e:
            raise  e

        logging.info(f"got response {response}")
        if not waitForSolution:
            return response

        try:
            result = self.get_solution_sync(response)
            # Reconstruct arrays

            result['data']['result']['start_states'] = deserialize_complex_array(result['data']['result']['start_states'])
            result['data']['result']['final_states'] = deserialize_complex_array(result['data']['result']['final_states'])
            result['data']['result']['record_states'] = deserialize_complex_array(result['data']['result']['record_states'])

            # The other arrays that are purely real (final_gains, record_gains) can be read normally
            result['data']['result']['final_gains'] = numpy.array(result['data']['result']['final_gains'], dtype=numpy.float32)
            result['data']['result']['record_gains'] = numpy.array(result['data']['result']['record_gains'], dtype=numpy.float32)

            return result
        except requests.exceptions.ConnectionError   as e:
            raise  Exception("!!!!! No access to LightSolver Cloud, SOLUTION server !!!!!")
        except Exception as e:
            raise  e


    def upload_sim_lpu_coupmat_input(self,
                                      matrix_data  = None,
                                      initial_states_seed = -1,
                                      initial_states_vector = None,
                                      num_runs = 1,
                                      num_iterations = 10000,
                                      rounds_per_record  = 100,
                                      timeout  = 5,
                                      gain_info_initial_gain = 1.8 ,
                                      gain_info_pump_max = 3 ,
                                      gain_info_pump_tau = 100.0 ,
                                      gain_info_pump_treshold = 1.8 ,
                                      gain_info_amplification_saturation = 1.0 ,
                                      input_path = None):
        command_input = {}

        if matrix_data is not None:
            var_count = len(matrix_data)
            if type(matrix_data) == numpy.ndarray:
                if matrix_data.dtype == numpy.complex64:
                    combined =  serialize_complex_array (matrix_data)
                    command_input[MessageKeys.COUPMAT_MATRIX] = combined

                else:
                        raise(TypeError("The input must complex64 type"))
            else:
                raise(TypeError("The input must be a numpy array"))
        else:
            raise(TypeError("The input matrix must be not empty"))

        if initial_states_vector is not None:
            if initial_states_vector is not None and num_runs != 1 :
                raise ValueError("initial_states_vector already consist number or runs:{initial_states_vector.shape}")
            if not isinstance(initial_states_vector, numpy.ndarray):
                raise ValueError("initial_states_vector must be a numpy array")

            for i, arr in enumerate(initial_states_vector):
                if not isinstance(arr, numpy.ndarray):
                    raise ValueError(f"Element {i} of initial_states_vector  is not a numpy array")
                if arr.dtype != numpy.complex64:
                    raise ValueError(f"Element {i} of initial_states_vector is not of dtype numpy.complex64")
                if arr.shape[0] != var_count:
                    raise ValueError(f"Element {i} of initial_states_vector does not have size of {var_count}")
            z = initial_states_vector.shape[0]
            zz = initial_states_vector.shape[1]
            b = initial_states_vector.shape

            command_input["initial_states"] = serialize_complex_array (initial_states_vector)

        if initial_states_vector is not None and initial_states_seed >= 0 :
            raise(TypeError("The input must provide only one of seed or vector"))
        command_input["initial_states_seed"] = initial_states_seed

        if initial_states_vector is not None and num_runs > 1:
            raise(TypeError("For SIM LPU: same initial state vector, run multiple times, will return exactly the same result every time."))

        if num_runs < 1 or num_runs > 10000:
            raise(TypeError("The num_runs:{num_runs} in input must be in range 1-10K"))
        command_input[MessageKeys.LPU_NUM_RUNS] = num_runs

        if num_iterations < 1 or num_iterations > 200000:
            raise(TypeError("The num_iterations:{num_iterations} in  input must be in range 1-200K"))
        command_input["num_iterations"] = num_iterations

        if timeout < 1 or timeout > 200000:
            raise(TypeError("The timeout:{timeout} in  input must be in range 1-14400 seconds"))
        command_input["timeout"] = timeout

        if rounds_per_record < 1 or rounds_per_record > num_iterations:
            raise(TypeError("The rounds_per_record :{rounds_per_record} in  input must be in range from 1 to num_iterations:{num_iterations}:"))
        command_input["rounds_per_record"] = rounds_per_record

        if gain_info_initial_gain < 0 :
            raise(TypeError("The gain_info_initial_gain:{gain_info_initial_gain} in  input must be in range 0-inf "))
        command_input["gain_info_initial_gain"] = gain_info_initial_gain

        if gain_info_pump_max < 0:
            raise(TypeError("The gain_info_pump_max:{gain_info_pump_max} in  input must be in range 0-inf"))
        command_input["gain_info_pump_max"] = gain_info_pump_max

        if gain_info_pump_tau < 0:
            raise(TypeError("The gain_info_pump_tau:{gain_info_pump_tau} in  input must be in range 0-inf"))
        command_input["gain_info_pump_tau"] = gain_info_pump_tau

        if gain_info_pump_treshold < 0:
            raise(TypeError("The gain_info_pump_treshold:{gain_info_pump_treshold} in  input must be in range 0-inf"))
        command_input["gain_info_pump_treshold"] = gain_info_pump_treshold

        if gain_info_amplification_saturation <= 0:
            raise(TypeError("The gain_info_amplification_saturation:{gain_info_amplification_saturation} in  input must be in range 0-inf"))
        command_input["gain_info_amplification_saturation"] = gain_info_amplification_saturation

        try:
            iid = self.apiClient.upload_command_input(command_input, input_path)
            return iid, int(var_count)

        except requests.exceptions.ConnectionError as e:
            raise  Exception("!!!!! No access to LightSolver Cloud, URL PROVIDER server !!!!!")
        except Exception as e:
            raise  e
