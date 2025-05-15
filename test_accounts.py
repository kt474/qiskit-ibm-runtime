from qiskit_ibm_runtime import QiskitRuntimeService
import time
from my_info import CRN, API_KEY, IQP_KEY


def service_a():
    print("Saving account")
    QiskitRuntimeService.save_account(channel="ibm_cloud", token=API_KEY, overwrite=True)
    print("Instantiating service")
    service = QiskitRuntimeService(channel="ibm_cloud", instance=CRN)
    return service


def service_b():
    print("Saving account")
    QiskitRuntimeService.save_account(
        channel="ibm_cloud", token=API_KEY, instance=CRN, overwrite=True
    )
    print("Instantiating service")
    service = QiskitRuntimeService(channel="ibm_cloud")
    return service


def service_c():
    print("Saving account")
    QiskitRuntimeService.save_account(channel="ibm_cloud", token=API_KEY, overwrite=True)
    print("Instantiating service")
    service = QiskitRuntimeService(channel="ibm_cloud")
    return service


def service_d():
    print("Saving account")
    t0 = time.time()
    QiskitRuntimeService.save_account(channel="ibm_quantum_platform", token=API_KEY, overwrite=True)
    print(f"Done saving account in {time.time()-t0} seconds")
    print("Instantiating service")
    t0 = time.time()
    service = QiskitRuntimeService(channel="ibm_quantum_platform")
    print(f"Done instantiating service in {time.time()-t0} seconds")
    return service


def service_e():
    print("Saving account")
    t0 = time.time()
    QiskitRuntimeService.save_account(channel="ibm_quantum", token=IQP_KEY, overwrite=True)
    print(f"Done saving account in {time.time()-t0} seconds")
    print("Instantiating service")
    t0 = time.time()
    service = QiskitRuntimeService(channel="ibm_quantum")
    print(f"Done instantiating service in {time.time()-t0} seconds")
    return service


def run_checks(check_service):
    print("Getting instances")
    t0 = time.time()
    print(check_service.instances())
    print(f"Done getting instances in {time.time()-t0} seconds")

    get_one(check_service, "test_eagle_us-east")
    get_all(check_service)


def get_one(check_service, backend_name):
    print("Getting one backend")
    t1 = time.time()
    backend = check_service.backend(backend_name)
    print(f"Done getting one backend in {time.time()-t1} seconds")
    print(backend)


def get_all(check_service):
    print("Getting backends")
    t0 = time.time()
    backends = check_service.backends()
    print(f"Done getting {len(backends)} backends in {time.time()-t0} seconds")
    # print(backends)


# print("TEST A")
# run_checks(service_a())
# print("TEST B")
# run_checks(service_b())
# print("TEST C")
# run_checks(service_c())
print("TEST D")
run_checks(service_d())
print("TEST E")
run_checks(service_e())
