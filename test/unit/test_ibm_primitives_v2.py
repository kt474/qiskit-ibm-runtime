# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for primitive classes."""

from dataclasses import asdict
from unittest.mock import MagicMock, patch

from ddt import data, ddt
import numpy as np

from qiskit import transpile
from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import real_amplitudes
from qiskit.quantum_info import SparsePauliOp

from qiskit_ibm_runtime import Session, Batch
from qiskit_ibm_runtime.utils.default_session import _DEFAULT_SESSION
from qiskit_ibm_runtime import EstimatorV2, SamplerV2
from qiskit_ibm_runtime.estimator import Estimator as IBMBaseEstimator
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.exceptions import IBMInputValueError

from ..ibm_test_case import IBMTestCase
from ..utils import (
    dict_paritally_equal,
    flat_dict_partially_equal,
    dict_keys_equal,
    create_faulty_backend,
    combine,
    get_primitive_inputs,
    get_mocked_backend,
    bell,
    get_mocked_session,
    get_mocked_batch,
)


@ddt
class TestPrimitivesV2(IBMTestCase):
    """Class for testing the Sampler and Estimator classes."""

    @classmethod
    def setUpClass(cls):
        cls.circ = bell()
        cls.obs = SparsePauliOp.from_list([("IZ", 1)])
        return super().setUpClass()

    def tearDown(self) -> None:
        super().tearDown()
        _DEFAULT_SESSION.set(None)

    @data(EstimatorV2, SamplerV2)
    def test_dict_options(self, primitive):
        """Test passing a dictionary as options."""
        options_vars = [
            {},
            {
                "max_execution_time": 100,
                "execution": {"init_qubits": True},
            },
            {"default_shots": 1000},
        ]
        backend = get_mocked_backend()
        for options in options_vars:
            inst = primitive(mode=backend, options=options)
            self.assertTrue(dict_paritally_equal(asdict(inst.options), options))

    @combine(
        primitive=[EstimatorV2, SamplerV2],
        env_var=[
            {"log_level": "DEBUG"},
            {"job_tags": ["foo", "bar"]},
        ],
    )
    def test_runtime_options(self, primitive, env_var):
        """Test RuntimeOptions specified as primitive options."""
        backend = get_mocked_backend()
        options = primitive._options_class(environment=env_var)
        inst = primitive(mode=backend, options=options)
        inst.run(**get_primitive_inputs(inst, backend=backend))
        run_options = backend.service._run.call_args.kwargs["options"]
        for key, val in env_var.items():
            self.assertEqual(run_options[key], val)

    @combine(
        primitive=[EstimatorV2, SamplerV2],
        opts=[
            {"experimental": {"image": "foo:bar"}},
            {"experimental": {"image": "foo:bar"}, "environment": {"log_level": "INFO"}},
        ],
    )
    def test_image(self, primitive, opts):
        """Test passing an image to options."""
        backend = get_mocked_backend()
        options = primitive._options_class(**opts)
        inst = primitive(mode=backend, options=options)
        inst.run(**get_primitive_inputs(inst))
        run_options = backend.service._run.call_args.kwargs["options"]
        input_params = backend.service._run.call_args.kwargs["inputs"]
        expected = list(opts.values())[0]
        for key, val in expected.items():
            self.assertEqual(run_options[key], val)
            self.assertNotIn(key, input_params)
            self.assertNotIn(key, input_params["options"])
            self.assertNotIn(key, input_params["options"].get("experimental", {}))

    @data(EstimatorV2, SamplerV2)
    def test_options_copied(self, primitive):
        """Test modifying original options does not affect primitives."""
        backend = get_mocked_backend()
        options = primitive._options_class()
        options.max_execution_time = 100
        inst = primitive(mode=backend, options=options)
        options.max_execution_time = 200
        self.assertEqual(inst.options.max_execution_time, 100)

    @data(EstimatorV2, SamplerV2)
    def test_init_with_backend_str(self, primitive):
        """Test initializing a primitive with a backend name."""
        backend_name = "ibm_gotham"
        mock_backend = get_mocked_backend(name=backend_name)
        mock_service_inst = mock_backend.service

        class MockQRTService:
            """Mock class used to create a new QiskitRuntimeService."""

            def __new__(cls, *args, **kwargs):  # pylint: disable=unused-argument
                return mock_service_inst

        with patch("qiskit_ibm_runtime.base_primitive.QiskitRuntimeService", new=MockQRTService):
            inst = primitive(mode=mock_backend)
            self.assertIsNone(inst.mode)
            inst.run(**get_primitive_inputs(inst))
            mock_service_inst._run.assert_called_once()
            runtime_options = mock_service_inst._run.call_args.kwargs["options"]
            self.assertEqual(runtime_options["backend"], mock_backend)

            mock_service_inst.reset_mock()
            str_mode_inst = primitive(mode=mock_backend)
            self.assertIsNone(str_mode_inst.mode)
            inst.run(**get_primitive_inputs(str_mode_inst))
            mock_service_inst._run.assert_called_once()
            runtime_options = mock_service_inst._run.call_args.kwargs["options"]
            self.assertEqual(runtime_options["backend"], mock_backend)

    @data(EstimatorV2, SamplerV2)
    def test_init_with_backend_instance(self, primitive):
        """Test initializing a primitive with a backend instance."""
        backend = get_mocked_backend()
        service = backend.service

        service.reset_mock()
        inst = primitive(mode=backend)
        self.assertIsNone(inst.mode)
        inst.run(**get_primitive_inputs(inst))
        service._run.assert_called_once()
        runtime_options = service._run.call_args.kwargs["options"]
        self.assertEqual(runtime_options["backend"], backend)

    @data(EstimatorV2, SamplerV2)
    def test_init_with_backend_session(self, primitive):
        """Test initializing a primitive with both backend and session."""
        backend_name = "ibm_gotham"
        session = get_mocked_session(get_mocked_backend(backend_name))

        session.reset_mock()
        inst = primitive(mode=session)
        self.assertIsNotNone(inst.mode)
        inst.run(**get_primitive_inputs(inst))
        session._run.assert_called_once()

    @data(EstimatorV2, SamplerV2)
    def test_default_session_context_manager(self, primitive):
        """Test getting default session within context manager."""
        backend_name = "ibm_gotham"
        backend = get_mocked_backend(name=backend_name)

        with Session(backend=backend) as session:
            inst = primitive()
            self.assertEqual(inst.mode, session)
            self.assertEqual(inst.mode.backend(), backend_name)

    @data(EstimatorV2, SamplerV2)
    def test_default_session_cm_new_backend(self, primitive):
        """Test using a different backend within context manager."""
        session_backend = get_mocked_backend("ibm_metropolis")
        backend = get_mocked_backend()

        with Session(backend=session_backend):
            with self.assertRaises(ValueError):
                _ = primitive(mode=backend)

    @data(EstimatorV2, SamplerV2)
    def test_no_session(self, primitive):
        """Test running without session."""
        backend = get_mocked_backend()
        service = backend.service
        inst = primitive(backend)
        inst.run(**get_primitive_inputs(inst))
        self.assertIsNone(inst.mode)
        service._run.assert_called_once()
        kwargs_list = service._run.call_args.kwargs
        self.assertNotIn("session_id", kwargs_list)
        self.assertNotIn("start_session", kwargs_list)

    @data(SamplerV2, EstimatorV2)
    def test_init_with_mode_as_backend(self, primitive):
        """Test initializing a primitive with mode as a Backend."""
        backend = get_mocked_backend()
        service = backend.service

        inst = primitive(mode=backend)
        self.assertIsNotNone(inst)
        inst.run(**get_primitive_inputs(inst))
        service._run.assert_called_once()
        runtime_options = service._run.call_args.kwargs["options"]
        self.assertEqual(runtime_options["backend"], backend)

    @data(SamplerV2, EstimatorV2)
    def test_init_with_mode_as_session(self, primitive):
        """Test initializing a primitive with mode as Session."""
        backend = get_mocked_backend()
        session = get_mocked_session(backend)
        session.reset_mock()
        session._backend = backend

        inst = primitive(mode=session)
        self.assertIsNotNone(inst.mode)
        inst.run(**get_primitive_inputs(inst, backend=backend))
        self.assertEqual(inst.mode, session)
        session._run.assert_called_once()
        self.assertEqual(session._backend, backend)

    @data(SamplerV2, EstimatorV2)
    def test_init_with_mode_as_batch(self, primitive):
        """Test initializing a primitive with mode as a Batch"""
        backend = get_mocked_backend()
        batch = get_mocked_batch(backend)
        batch.reset_mock()
        batch._backend = backend

        inst = primitive(mode=batch)
        self.assertIsNotNone(inst.mode)
        inst.run(**get_primitive_inputs(inst, backend=backend))
        self.assertEqual(batch._backend, backend)

    @data(EstimatorV2, SamplerV2)
    def test_parameters_single_circuit(self, primitive):
        """Test parameters for a single cirucit."""

        circ = real_amplitudes(num_qubits=2, reps=1)
        backend = get_mocked_backend()
        circ = transpile(circ, backend=backend)

        param_vals = [
            # 1 set of parameter values
            [1, 2, 3, 4],
            [np.pi] * circ.num_parameters,
            np.random.uniform(size=(4,)),
            {param: [2.0] for param in circ.parameters},
            # N sets of parameter values
            [[1, 2, 3, 4]] * 2,
            np.random.random((2, 4)),
            np.linspace(0, 1, 24).reshape((2, 3, 4)),
            {param: [1, 2, 3] for param in circ.parameters},
            {param: np.linspace(0, 1, 5) for param in circ.parameters},
            {tuple(circ.parameters): np.random.random((2, 3, 4))},
            {
                tuple(circ.parameters[:2]): np.random.random((2, 1, 2)),
                tuple(circ.parameters[2:4]): np.random.random((2, 1, 2)),
            },
        ]

        inst = primitive(mode=get_mocked_backend())
        for val in param_vals:
            with self.subTest(val=val):
                pub = (circ, "ZZIII", val) if isinstance(inst, EstimatorV2) else (circ, val)
                inst.run([pub])

    @data(EstimatorV2, SamplerV2)
    def test_nd_parameters(self, primitive):
        """Test with parameters of different dimensions."""
        circ = real_amplitudes(num_qubits=2, reps=1)
        backend = get_mocked_backend()
        circ = transpile(circ, backend=backend)
        inst = primitive(mode=backend)

        with self.subTest("0-d"):
            param_vals = np.linspace(0, 1, 4)
            barray = {tuple(circ.parameters): param_vals}
            pub = (circ, "ZZIII", barray) if isinstance(inst, EstimatorV2) else (circ, barray)
            inst.run([pub])

        with self.subTest("n-d"):
            barray = {tuple(circ.parameters): np.random.random((2, 3, 4))}
            pub = (circ, "ZZIII", barray) if isinstance(inst, EstimatorV2) else (circ, barray)
            inst.run([pub])

    @data(EstimatorV2, SamplerV2)
    def test_parameters_multiple_circuits(self, primitive):
        """Test multiple parameters for multiple circuits."""
        backend = get_mocked_backend()
        circuits = [
            transpile(QuantumCircuit(2), backend=backend),
            transpile(real_amplitudes(num_qubits=2, reps=1), backend=backend),
            transpile(real_amplitudes(num_qubits=3, reps=1), backend=backend),
        ]

        param_vals = [
            (
                [],
                np.random.uniform(size=(4,)),
                np.random.uniform(size=(6,)),
            ),
            (
                [],
                np.random.random((2, 4)),
                np.random.random((2, 6)),
            ),
        ]

        inst = primitive(mode=backend)
        for all_params in param_vals:
            with self.subTest(all_params=all_params):
                pubs = []
                for circ, circ_params in zip(circuits, all_params):
                    publet = (
                        (circ, "Z" * backend.num_qubits, circ_params)
                        if isinstance(inst, EstimatorV2)
                        else (circ, circ_params)
                    )
                    pubs.append(publet)
                inst.run(pubs)

    @data(EstimatorV2, SamplerV2)
    def test_run_updated_options(self, primitive):
        """Test run using overwritten options."""
        backend = get_mocked_backend()
        options_vars = [
            (
                {"dynamical_decoupling": {"sequence_type": "XY4"}},
                {"dynamical_decoupling": {"sequence_type": "XY4"}},
            ),
            ({"default_shots": 2000}, {"default_shots": 2000}),
            (
                {"execution": {"init_qubits": True}},
                {"execution": {"init_qubits": True}},
            ),
        ]

        for options, expected in options_vars:
            with self.subTest(options=options):
                inst = primitive(mode=backend)
                inst.options.update(**options)
                inst.run(**get_primitive_inputs(inst))
                inputs = backend.service._run.call_args.kwargs["inputs"]["options"]
                self._assert_dict_partially_equal(inputs, expected)

    @data(EstimatorV2, SamplerV2)
    def test_run_overwrite_runtime_options(self, primitive):
        """Test run using overwritten runtime options."""
        backend = get_mocked_backend()
        options_vars = [
            {"environment": {"log_level": "DEBUG"}},
            {"environment": {"job_tags": ["foo", "bar"]}},
            {"max_execution_time": 600},
            {"environment": {"log_level": "INFO"}, "max_execution_time": 800},
        ]
        for options in options_vars:
            with self.subTest(options=options):
                inst = primitive(mode=backend)
                inst.options.update(**options)
                inst.run(**get_primitive_inputs(inst))
                runtime_options = primitive._options_class._get_runtime_options(options)
                rt_options = backend.service._run.call_args.kwargs["options"]
                self._assert_dict_partially_equal(rt_options, runtime_options)

    @combine(
        primitive=[EstimatorV2, SamplerV2],
        exp_opt=[{"foo": "bar", "execution": {"extra_key": "bar"}}],
    )
    def test_run_experimental_options(self, primitive, exp_opt):
        """Test specifying arbitrary options in run."""
        backend = get_mocked_backend()
        inst = primitive(mode=backend)
        inst.options.experimental = exp_opt
        inst.run(**get_primitive_inputs(inst))
        inputs = backend.service._run.call_args.kwargs["inputs"]["options"]
        self.assertDictEqual(inputs["experimental"], {"foo": "bar"})
        self.assertDictEqual(inputs["execution"], {"extra_key": "bar"})
        self.assertNotIn("extra_key", inputs)

    @combine(
        primitive=[EstimatorV2, SamplerV2],
        exp_opt=[{"foo": "bar", "execution": {"extra_key": "bar"}}],
    )
    def test_run_experimental_options_init(self, primitive, exp_opt):
        """Test specifying arbitrary options in initialization."""
        backend = get_mocked_backend()
        inst = primitive(mode=backend, options={"experimental": exp_opt})
        inst.run(**get_primitive_inputs(inst))
        inputs = backend.service._run.call_args.kwargs["inputs"]["options"]
        self.assertDictEqual(inputs["experimental"], {"foo": "bar"})
        self.assertDictEqual(inputs["execution"], {"extra_key": "bar"})
        self.assertNotIn("extra_key", inputs)

    @data(EstimatorV2, SamplerV2)
    def test_run_unset_options(self, primitive):
        """Test running with unset options."""
        backend = get_mocked_backend()
        inst = primitive(mode=backend)
        inst.run(**get_primitive_inputs(inst))
        inputs = backend.service._run.call_args.kwargs["inputs"]["options"]
        self.assertFalse(inputs)

    @data(EstimatorV2, SamplerV2)
    def test_run_multiple_different_options(self, primitive):
        """Test multiple runs with different options."""
        backend = get_mocked_backend()
        inst = primitive(mode=backend, options={"default_shots": 100})
        inst.run(**get_primitive_inputs(inst))
        inst.options.update(default_shots=200)
        inst.run(**get_primitive_inputs(inst))
        kwargs_list = backend.service._run.call_args_list
        for idx, shots in zip([0, 1], [100, 200]):
            self.assertEqual(kwargs_list[idx][1]["inputs"]["options"]["default_shots"], shots)

    def test_run_same_session(self):
        """Test multiple runs within a session."""
        num_runs = 5
        primitives = [EstimatorV2, SamplerV2]
        session = get_mocked_session()
        for idx in range(num_runs):
            cls = primitives[idx % len(primitives)]
            inst = cls(mode=session)
            inst.run(**get_primitive_inputs(inst))
        self.assertEqual(session._run.call_count, num_runs)

    @combine(
        primitive=[EstimatorV2, SamplerV2],
        new_opts=[
            {"default_shots": 200},
            {"dynamical_decoupling": {"enable": True}, "default_shots": 300},
        ],
    )
    def test_set_options(self, primitive, new_opts):
        """Test set options."""
        opt_cls = primitive._options_class
        options = opt_cls(default_shots=100)
        backend = get_mocked_backend()

        inst = primitive(mode=backend, options=options)
        inst.options.update(**new_opts)
        # Make sure the values are equal.
        inst_options = asdict(inst.options)
        self.assertTrue(
            flat_dict_partially_equal(inst_options, new_opts),
            f"inst_options={inst_options}, new_opt={new_opts}",
        )
        # Make sure the structure didn't change.
        self.assertTrue(
            dict_keys_equal(inst_options, asdict(opt_cls())),
            f"inst_options={inst_options}, original={opt_cls()}",
        )

    @data(EstimatorV2, SamplerV2)
    def test_raise_faulty_qubits(self, primitive):
        """Test faulty qubits is raised."""
        fake_backend = FakeManilaV2()
        num_qubits = fake_backend.configuration().num_qubits
        circ = QuantumCircuit(num_qubits, num_qubits)
        for i in range(num_qubits):
            circ.x(i)
        transpiled = transpile(circ, backend=fake_backend)
        observable = SparsePauliOp("Z" * num_qubits)

        faulty_qubit = 4
        ibm_backend = create_faulty_backend(fake_backend, faulty_qubit=faulty_qubit)
        inst = primitive(mode=ibm_backend)

        if isinstance(inst, IBMBaseEstimator):
            pub = (transpiled, observable)
        else:
            transpiled.measure_all()
            pub = (transpiled,)

        with self.assertRaises(ValueError) as err:
            inst.run(pubs=[pub])
        self.assertIn(f"faulty qubit {faulty_qubit}", str(err.exception))

    @data(EstimatorV2, SamplerV2)
    def test_raise_faulty_qubits_many(self, primitive):
        """Test faulty qubits is raised if one circuit uses it."""
        fake_backend = FakeManilaV2()
        num_qubits = fake_backend.configuration().num_qubits

        circ1 = QuantumCircuit(1, 1)
        circ1.x(0)
        circ2 = QuantumCircuit(num_qubits, num_qubits)
        for i in range(num_qubits):
            circ2.x(i)
        transpiled = transpile([circ1, circ2], backend=fake_backend)
        observable = SparsePauliOp("Z" * num_qubits)

        faulty_qubit = 4
        ibm_backend = create_faulty_backend(fake_backend, faulty_qubit=faulty_qubit)

        inst = primitive(ibm_backend)
        if isinstance(inst, IBMBaseEstimator):
            pubs = [(transpiled[0], observable), (transpiled[1], observable)]
        else:
            for circ in transpiled:
                circ.measure_all()
            pubs = [(transpiled[0],), (transpiled[1],)]

        with self.assertRaises(ValueError) as err:
            inst.run(pubs=pubs)
        self.assertIn(f"faulty qubit {faulty_qubit}", str(err.exception))

    @data(EstimatorV2, SamplerV2)
    def test_raise_faulty_edge(self, primitive):
        """Test faulty edge is raised."""
        fake_backend = FakeManilaV2()
        num_qubits = fake_backend.configuration().num_qubits
        circ = QuantumCircuit(num_qubits, num_qubits)
        for i in range(num_qubits - 2):
            circ.cx(i, i + 1)
        transpiled = transpile(circ, backend=fake_backend, optimization_level=1)
        observable = SparsePauliOp("Z" * num_qubits)

        edge_qubits = [0, 1]
        ibm_backend = create_faulty_backend(fake_backend, faulty_edge=("cx", edge_qubits))

        inst = primitive(ibm_backend)
        if isinstance(inst, IBMBaseEstimator):
            pub = (transpiled, observable)
        else:
            transpiled.measure_all()
            pub = (transpiled,)

        with self.assertRaises(ValueError) as err:
            inst.run(pubs=[pub])
        self.assertIn("cx", str(err.exception))
        self.assertIn(f"faulty edge {tuple(edge_qubits)}", str(err.exception))

    @data(EstimatorV2, SamplerV2)
    def test_faulty_qubit_not_used(self, primitive):
        """Test faulty qubit is not raise if not used."""
        fake_backend = FakeManilaV2()
        circ = QuantumCircuit(2, 2)
        for i in range(2):
            circ.x(i)
        transpiled = transpile(circ, backend=fake_backend, initial_layout=[0, 1])
        observable = SparsePauliOp("Z" * fake_backend.configuration().num_qubits)

        faulty_qubit = 4
        ibm_backend = create_faulty_backend(fake_backend, faulty_qubit=faulty_qubit)
        inst = primitive(ibm_backend)
        if isinstance(inst, IBMBaseEstimator):
            pub = (transpiled, observable)
        else:
            transpiled.measure_active(inplace=True)
            pub = (transpiled,)

        with patch.object(inst, "_run") as mock_run:
            inst.run([pub])
        mock_run.assert_called_once()

    @data(EstimatorV2, SamplerV2)
    def test_faulty_edge_not_used(self, primitive):
        """Test faulty edge is not raised if not used."""
        fake_backend = FakeManilaV2()
        coupling_map = fake_backend.configuration().coupling_map

        circ = QuantumCircuit(2, 2)
        circ.cx(0, 1)

        transpiled = transpile(circ, backend=fake_backend, initial_layout=coupling_map[0])
        observable = SparsePauliOp("Z" * fake_backend.configuration().num_qubits)

        edge_qubits = coupling_map[-1]
        ibm_backend = create_faulty_backend(fake_backend, faulty_edge=("cx", edge_qubits))

        service = MagicMock()
        service.backend.return_value = ibm_backend
        session = Session(backend=fake_backend)

        inst = primitive(mode=session)
        if isinstance(inst, IBMBaseEstimator):
            pub = (transpiled, observable)
        else:
            transpiled.measure_all()
            pub = (transpiled,)

        with patch.object(Session, "_run") as mock_run:
            inst.run([pub])
        mock_run.assert_called_once()

    @data(EstimatorV2, SamplerV2)
    def test_abstract_circuits(self, primitive):
        """Test passing in abstract circuit would fail."""
        backend = get_mocked_backend()
        inst = primitive(mode=backend)
        circ = QuantumCircuit(3, 3)
        circ.cx(0, 2)
        pub = [circ]
        if isinstance(inst, EstimatorV2):
            pub.append(SparsePauliOp("ZZZ"))
        else:
            circ.measure_all()

        with self.assertRaisesRegex(IBMInputValueError, "target hardware"):
            inst.run(pubs=[tuple(pub)])

    @data(EstimatorV2, SamplerV2)
    def test_get_backend_primitive(self, primitive):
        """Test getting the backend used in the primitive."""
        backend = get_mocked_backend()
        inst = primitive(mode=backend)
        self.assertEqual(inst.backend().name, backend.name)

    @combine(primitive=[EstimatorV2, SamplerV2], session=[Session, Batch])
    def test_get_backend_session(self, primitive, session):
        """Test getting the backend used in the primitive when session is used."""
        backend = FakeManilaV2()
        with session(backend=backend):
            inst = primitive()
            self.assertEqual(inst.backend().name, backend.name)

    def _update_dict(self, dict1, dict2):
        for key, val in dict1.items():
            if isinstance(val, dict):
                self._update_dict(val, dict2.pop(key, {}))
            elif key in dict2.keys():
                dict1[key] = dict2.pop(key)

    def _assert_dict_partially_equal(self, dict1, dict2):
        """Assert all keys in dict2 are in dict1 and have same values."""
        self.assertTrue(
            dict_paritally_equal(dict1, dict2),
            f"{dict1} and {dict2} not partially equal.",
        )
