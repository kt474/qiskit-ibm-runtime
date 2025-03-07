# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2018.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


"""Backend Configuration Classes."""
import datetime
import re
import copy
import numbers
from typing import Dict, List, Any, Iterable, Tuple, Union, TypeVar, Type
from collections import defaultdict

from qiskit.exceptions import QiskitError
from qiskit.pulse.channels import (
    AcquireChannel,
    Channel,
    ControlChannel,
    DriveChannel,
    MeasureChannel,
)

from .exceptions import BackendConfigurationError

GateConfigT = TypeVar("GateConfigT", bound="GateConfig")
UchannelLOT = TypeVar("UchannelLOT", bound="UchannelLO")  # pylint: disable=[invalid-name]
QasmBackendConfigurationT = TypeVar("QasmBackendConfigurationT", bound="QasmBackendConfiguration")


class GateConfig:
    """Class representing a Gate Configuration

    Attributes:
        name: the gate name as it will be referred to in OpenQASM.
        parameters: variable names for the gate parameters (if any).
        qasm_def: definition of this gate in terms of OpenQASM 2 primitives U
                  and CX.
    """

    def __init__(
        self,
        name: str,
        parameters: List[str],
        qasm_def: str,
        coupling_map: list = None,
        latency_map: list = None,
        conditional: bool = None,
        description: str = None,
    ):
        """Initialize a GateConfig object

        Args:
            name (str): the gate name as it will be referred to in OpenQASM.
            parameters (list): variable names for the gate parameters (if any)
                               as a list of strings.
            qasm_def (str): definition of this gate in terms of OpenQASM 2 primitives U and CX.
            coupling_map (list): An optional coupling map for the gate. In
                the form of a list of lists of integers representing the qubit
                groupings which are coupled by this gate.
            latency_map (list): An optional map of latency for the gate. In the
                the form of a list of lists of integers of either 0 or 1
                representing an array of dimension
                len(coupling_map) X n_registers that specifies the register
                latency (1: fast, 0: slow) conditional operations on the gate
            conditional (bool): Optionally specify whether this gate supports
                conditional operations (true/false). If this is not specified,
                then the gate inherits the conditional property of the backend.
            description (str): Description of the gate operation
        """

        self.name = name
        self.parameters = parameters
        self.qasm_def = qasm_def
        # coupling_map with length 0 is invalid
        if coupling_map:
            self.coupling_map = coupling_map
        # latency_map with length 0 is invalid
        if latency_map:
            self.latency_map = latency_map
        if conditional is not None:
            self.conditional = conditional
        if description is not None:
            self.description = description

    @classmethod
    def from_dict(cls: Type[GateConfigT], data: Dict[str, Any]) -> GateConfigT:
        """Create a new GateConfig object from a dictionary.

        Args:
            data (dict): A dictionary representing the GateConfig to create.
                         It will be in the same format as output by
                         :func:`to_dict`.

        Returns:
            GateConfig: The GateConfig from the input dictionary.
        """
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary format representation of the GateConfig.

        Returns:
            dict: The dictionary form of the GateConfig.
        """
        out_dict: Dict[str, Any] = {
            "name": self.name,
            "parameters": self.parameters,
            "qasm_def": self.qasm_def,
        }
        if hasattr(self, "coupling_map"):
            out_dict["coupling_map"] = self.coupling_map
        if hasattr(self, "latency_map"):
            out_dict["latency_map"] = self.latency_map
        if hasattr(self, "conditional"):
            out_dict["conditional"] = self.conditional
        if hasattr(self, "description"):
            out_dict["description"] = self.description
        return out_dict

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, GateConfig):
            if self.to_dict() == other.to_dict():
                return True
        return False

    def __repr__(self) -> str:
        out_str = f"GateConfig({self.name}, {self.parameters}, {self.qasm_def}"
        for i in ["coupling_map", "latency_map", "conditional", "description"]:
            if hasattr(self, i):
                out_str += ", " + repr(getattr(self, i))
        out_str += ")"
        return out_str


class UchannelLO:
    """Class representing a U Channel LO

    Attributes:
        q: Qubit that scale corresponds too.
        scale: Scale factor for qubit frequency.
    """

    def __init__(self, q: int, scale: complex) -> None:
        """Initialize a UchannelLOSchema object

        Args:
            q (int): Qubit that scale corresponds too. Must be >= 0.
            scale (complex): Scale factor for qubit frequency.

        Raises:
            QiskitError: If q is < 0
        """
        if q < 0:
            raise QiskitError("q must be >=0")
        self.q = q
        self.scale = scale

    @classmethod
    def from_dict(cls: Type[UchannelLOT], data: Dict[str, Any]) -> UchannelLOT:
        """Create a new UchannelLO object from a dictionary.

        Args:
            data (dict): A dictionary representing the UChannelLO to
                create. It will be in the same format as output by
                :func:`to_dict`.

        Returns:
            UchannelLO: The UchannelLO from the input dictionary.
        """
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary format representation of the UChannelLO.

        Returns:
            dict: The dictionary form of the UChannelLO.
        """
        out_dict: Dict[str, Any] = {
            "q": self.q,
            "scale": self.scale,
        }
        return out_dict

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, UchannelLO):
            if self.to_dict() == other.to_dict():
                return True
        return False

    def __repr__(self) -> str:
        return f"UchannelLO({self.q}, {self.scale})"


class QasmBackendConfiguration:
    """Class representing an OpenQASM 2.0 Backend Configuration.

    Attributes:
        backend_name: backend name.
        backend_version: backend version in the form X.Y.Z.
        n_qubits: number of qubits.
        basis_gates: list of basis gates names on the backend.
        gates: list of basis gates on the backend.
        local: backend is local or remote.
        simulator: backend is a simulator.
        conditional: backend supports conditional operations.
        open_pulse: backend supports open pulse.
        memory: backend supports memory.
        max_shots: maximum number of shots supported.
    """

    _data: Dict[Any, Any] = {}

    def __init__(
        self,
        backend_name: str,
        backend_version: str,
        n_qubits: int,
        basis_gates: list,
        gates: list,
        local: bool,
        simulator: bool,
        conditional: bool,
        open_pulse: bool,
        memory: bool,
        max_shots: int,
        coupling_map: list,
        supported_instructions: List[str] = None,
        dynamic_reprate_enabled: bool = False,
        rep_delay_range: List[float] = None,
        default_rep_delay: float = None,
        max_experiments: int = None,
        sample_name: str = None,
        n_registers: int = None,
        register_map: list = None,
        configurable: bool = None,
        credits_required: bool = None,
        online_date: datetime.datetime = None,
        display_name: str = None,
        description: str = None,
        tags: list = None,
        dt: float = None,
        dtm: float = None,
        processor_type: dict = None,
        parametric_pulses: list = None,
        **kwargs: Any,
    ):
        """Initialize a QasmBackendConfiguration Object

        Args:
            backend_name (str): The backend name
            backend_version (str): The backend version in the form X.Y.Z
            n_qubits (int): the number of qubits for the backend
            basis_gates (list): The list of strings for the basis gates of the
                backends
            gates (list): The list of GateConfig objects for the basis gates of
                the backend
            local (bool): True if the backend is local or False if remote
            simulator (bool): True if the backend is a simulator
            conditional (bool): True if the backend supports conditional
                operations
            open_pulse (bool): True if the backend supports OpenPulse
            memory (bool): True if the backend supports memory
            max_shots (int): The maximum number of shots allowed on the backend
            coupling_map (list): The coupling map for the device
            supported_instructions (List[str]): Instructions supported by the backend.
            dynamic_reprate_enabled (bool): whether delay between programs can be set dynamically
                (ie via ``rep_delay``). Defaults to False.
            rep_delay_range (List[float]): 2d list defining supported range of repetition
                delays for backend in μs. First entry is lower end of the range, second entry is
                higher end of the range. Optional, but will be specified when
                ``dynamic_reprate_enabled=True``.
            default_rep_delay (float): Value of ``rep_delay`` if not specified by user and
                ``dynamic_reprate_enabled=True``.
            max_experiments (int): The maximum number of experiments per job
            sample_name (str): Sample name for the backend
            n_registers (int): Number of register slots available for feedback
                (if conditional is True)
            register_map (list): An array of dimension n_qubits X
                n_registers that specifies whether a qubit can store a
                measurement in a certain register slot.
            configurable (bool): True if the backend is configurable, if the
                backend is a simulator
            credits_required (bool): True if backend requires credits to run a
                job.
            online_date (datetime.datetime): The date that the device went online
            display_name (str): Alternate name field for the backend
            description (str): A description for the backend
            tags (list): A list of string tags to describe the backend
            dt (float): Qubit drive channel timestep in nanoseconds.
            dtm (float): Measurement drive channel timestep in nanoseconds.
            processor_type (dict): Processor type for this backend. A dictionary of the
                form ``{"family": <str>, "revision": <str>, segment: <str>}`` such as
                ``{"family": "Canary", "revision": "1.0", segment: "A"}``.

                - family: Processor family of this backend.
                - revision: Revision version of this processor.
                - segment: Segment this processor belongs to within a larger chip.
            parametric_pulses (list): A list of pulse shapes which are supported on the backend.
                For example: ``['gaussian', 'constant']``

            **kwargs: optional fields
        """
        self._data = {}

        self.backend_name = backend_name
        self.backend_version = backend_version
        self.n_qubits = n_qubits
        self.basis_gates = basis_gates
        self.gates = gates
        self.local = local
        self.simulator = simulator
        self.conditional = conditional
        self.open_pulse = open_pulse
        self.memory = memory
        self.max_shots = max_shots
        self.coupling_map = coupling_map
        if supported_instructions:
            self.supported_instructions = supported_instructions

        self.dynamic_reprate_enabled = dynamic_reprate_enabled
        if rep_delay_range:
            self.rep_delay_range = [_rd * 1e-6 for _rd in rep_delay_range]  # convert to sec
        if default_rep_delay is not None:
            self.default_rep_delay = default_rep_delay * 1e-6  # convert to sec

        # max_experiments must be >=1
        if max_experiments:
            self.max_experiments = max_experiments
        if sample_name is not None:
            self.sample_name = sample_name
        # n_registers must be >=1
        if n_registers:
            self.n_registers = 1
        # register_map must have at least 1 entry
        if register_map:
            self.register_map = register_map
        if configurable is not None:
            self.configurable = configurable
        if credits_required is not None:
            self.credits_required = credits_required
        if online_date is not None:
            self.online_date = online_date
        if display_name is not None:
            self.display_name = display_name
        if description is not None:
            self.description = description
        if tags is not None:
            self.tags = tags
        # Add pulse properties here because some backends do not
        # fit within the Qasm / Pulse backend partitioning in Qiskit
        if dt is not None:
            self.dt = dt * 1e-9
        if dtm is not None:
            self.dtm = dtm * 1e-9
        if processor_type is not None:
            self.processor_type = processor_type
        if parametric_pulses is not None:
            self.parametric_pulses = parametric_pulses

        # convert lo range from GHz to Hz
        if "qubit_lo_range" in kwargs:
            kwargs["qubit_lo_range"] = [
                [min_range * 1e9, max_range * 1e9]
                for (min_range, max_range) in kwargs["qubit_lo_range"]
            ]

        if "meas_lo_range" in kwargs:
            kwargs["meas_lo_range"] = [
                [min_range * 1e9, max_range * 1e9]
                for (min_range, max_range) in kwargs["meas_lo_range"]
            ]

        # convert rep_times from μs to sec
        if "rep_times" in kwargs:
            kwargs["rep_times"] = [_rt * 1e-6 for _rt in kwargs["rep_times"]]

        self._data.update(kwargs)

    def __getattr__(self, name: str) -> Any:
        try:
            return self._data[name]
        except KeyError as ex:
            raise AttributeError(f"Attribute {name} is not defined") from ex

    @classmethod
    def from_dict(
        cls: Type[QasmBackendConfigurationT], data: Dict[str, Any]
    ) -> QasmBackendConfigurationT:
        """Create a new GateConfig object from a dictionary.

        Args:
            data (dict): A dictionary representing the GateConfig to create.
                         It will be in the same format as output by
                         :func:`to_dict`.
        Returns:
            GateConfig: The GateConfig from the input dictionary.
        """
        in_data: Dict[str, Any] = copy.copy(data)
        gates = [GateConfig.from_dict(x) for x in in_data.pop("gates")]
        in_data["gates"] = gates
        return cls(**in_data)

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary format representation of the GateConfig.

        Returns:
            dict: The dictionary form of the GateConfig.
        """
        out_dict: Dict[str, Any] = {
            "backend_name": self.backend_name,
            "backend_version": self.backend_version,
            "n_qubits": self.n_qubits,
            "basis_gates": self.basis_gates,
            "gates": [x.to_dict() for x in self.gates],
            "local": self.local,
            "simulator": self.simulator,
            "conditional": self.conditional,
            "open_pulse": self.open_pulse,
            "memory": self.memory,
            "max_shots": self.max_shots,
            "coupling_map": self.coupling_map,
            "dynamic_reprate_enabled": self.dynamic_reprate_enabled,
        }

        if hasattr(self, "supported_instructions"):
            out_dict["supported_instructions"] = self.supported_instructions

        if hasattr(self, "rep_delay_range"):
            out_dict["rep_delay_range"] = [_rd * 1e6 for _rd in self.rep_delay_range]
        if hasattr(self, "default_rep_delay"):
            out_dict["default_rep_delay"] = self.default_rep_delay * 1e6

        for kwarg in [
            "max_experiments",
            "sample_name",
            "n_registers",
            "register_map",
            "configurable",
            "credits_required",
            "online_date",
            "display_name",
            "description",
            "tags",
            "dt",
            "dtm",
            "processor_type",
            "parametric_pulses",
        ]:
            if hasattr(self, kwarg):
                out_dict[kwarg] = getattr(self, kwarg)

        out_dict.update(self._data)

        if "dt" in out_dict:
            out_dict["dt"] *= 1e9
        if "dtm" in out_dict:
            out_dict["dtm"] *= 1e9

        # Use GHz in dict
        if "qubit_lo_range" in out_dict:
            out_dict["qubit_lo_range"] = [
                [min_range * 1e-9, max_range * 1e-9]
                for (min_range, max_range) in out_dict["qubit_lo_range"]
            ]

        if "meas_lo_range" in out_dict:
            out_dict["meas_lo_range"] = [
                [min_range * 1e-9, max_range * 1e-9]
                for (min_range, max_range) in out_dict["meas_lo_range"]
            ]

        return out_dict

    @property
    def num_qubits(self) -> int:
        """Returns the number of qubits.

        In future, `n_qubits` should be replaced in favor of `num_qubits` for consistent use
        throughout Qiskit. Until this is properly refactored, this property serves as intermediate
        solution.
        """
        return self.n_qubits

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, QasmBackendConfiguration):
            if self.to_dict() == other.to_dict():
                return True
        return False

    def __contains__(self, item: str) -> bool:
        return item in self.__dict__


class BackendConfiguration(QasmBackendConfiguration):
    """Backwards compat shim representing an abstract backend configuration."""

    pass


class PulseBackendConfiguration(QasmBackendConfiguration):
    """Static configuration state for an OpenPulse enabled backend. This contains information
    about the set up of the device which can be useful for building Pulse programs.
    """

    def __init__(
        self,
        backend_name: str,
        backend_version: str,
        n_qubits: int,
        basis_gates: List[str],
        gates: list,
        local: bool,
        simulator: bool,
        conditional: bool,
        open_pulse: bool,
        memory: bool,
        max_shots: int,
        coupling_map: list,
        n_uchannels: int,
        u_channel_lo: List[List[UchannelLO]],
        meas_levels: List[int],
        qubit_lo_range: List[List[float]],
        meas_lo_range: List[List[float]],
        dt: float,
        dtm: float,
        rep_times: List[float],
        meas_kernels: List[str],
        discriminators: List[str],
        hamiltonian: Dict[str, Any] = None,
        channel_bandwidth: list = None,
        acquisition_latency: list = None,
        conditional_latency: list = None,
        meas_map: list = None,
        max_experiments: int = None,
        sample_name: str = None,
        n_registers: int = None,
        register_map: list = None,
        configurable: bool = None,
        credits_required: bool = None,
        online_date: datetime.datetime = None,
        display_name: str = None,
        description: str = None,
        tags: list = None,
        channels: Dict[set, Any] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize a backend configuration that contains all the extra configuration that is made
        available for OpenPulse backends.

        Args:
            backend_name: backend name.
            backend_version: backend version in the form X.Y.Z.
            n_qubits: number of qubits.
            basis_gates: list of basis gates names on the backend.
            gates: list of basis gates on the backend.
            local: backend is local or remote.
            simulator: backend is a simulator.
            conditional: backend supports conditional operations.
            open_pulse: backend supports open pulse.
            memory: backend supports memory.
            max_shots: maximum number of shots supported.
            coupling_map (list): The coupling map for the device
            n_uchannels: Number of u-channels.
            u_channel_lo: U-channel relationship on device los.
            meas_levels: Supported measurement levels.
            qubit_lo_range: Qubit lo ranges for each qubit with form (min, max) in GHz.
            meas_lo_range: Measurement lo ranges for each qubit with form (min, max) in GHz.
            dt: Qubit drive channel timestep in nanoseconds.
            dtm: Measurement drive channel timestep in nanoseconds.
            rep_times: Supported repetition times (program execution time) for backend in μs.
            meas_kernels: Supported measurement kernels.
            discriminators: Supported discriminators.
            hamiltonian: An optional dictionary with fields characterizing the system hamiltonian.
            channel_bandwidth (list): Bandwidth of all channels
                (qubit, measurement, and U)
            acquisition_latency (list): Array of dimension
                n_qubits x n_registers. Latency (in units of dt) to write a
                measurement result from qubit n into register slot m.
            conditional_latency (list): Array of dimension n_channels
                [d->u->m] x n_registers. Latency (in units of dt) to do a
                conditional operation on channel n from register slot m
            meas_map (list): Grouping of measurement which are multiplexed
            max_experiments (int): The maximum number of experiments per job
            sample_name (str): Sample name for the backend
            n_registers (int): Number of register slots available for feedback
                (if conditional is True)
            register_map (list): An array of dimension n_qubits X
                n_registers that specifies whether a qubit can store a
                measurement in a certain register slot.
            configurable (bool): True if the backend is configurable, if the
                backend is a simulator
            credits_required (bool): True if backend requires credits to run a
                job.
            online_date (datetime.datetime): The date that the device went online
            display_name (str): Alternate name field for the backend
            description (str): A description for the backend
            tags (list): A list of string tags to describe the backend
            channels: An optional dictionary containing information of each channel -- their
                purpose, type, and qubits operated on.
            **kwargs: Optional fields.
        """
        self.n_uchannels = n_uchannels
        self.u_channel_lo = u_channel_lo
        self.meas_levels = meas_levels

        # convert from GHz to Hz
        self.qubit_lo_range = [
            [min_range * 1e9, max_range * 1e9] for (min_range, max_range) in qubit_lo_range
        ]
        self.meas_lo_range = [
            [min_range * 1e9, max_range * 1e9] for (min_range, max_range) in meas_lo_range
        ]

        self.meas_kernels = meas_kernels
        self.discriminators = discriminators
        self.hamiltonian = hamiltonian
        if hamiltonian is not None:
            self.hamiltonian = dict(hamiltonian)
            self.hamiltonian["vars"] = {
                k: v * 1e9 if isinstance(v, numbers.Number) else v  # type: ignore[operator]
                for k, v in self.hamiltonian["vars"].items()
            }

        self.rep_times = [_rt * 1e-6 for _rt in rep_times]  # convert to sec

        self.dt = dt * 1e-9
        self.dtm = dtm * 1e-9

        if channels is not None:
            self.channels = channels

            (
                self._qubit_channel_map,
                self._channel_qubit_map,
                self._control_channels,
            ) = self._parse_channels(channels=channels)
        else:
            self._control_channels = defaultdict(list)

        if channel_bandwidth is not None:
            self.channel_bandwidth = [
                [min_range * 1e9, max_range * 1e9] for (min_range, max_range) in channel_bandwidth
            ]
        if acquisition_latency is not None:
            self.acquisition_latency = acquisition_latency
        if conditional_latency is not None:
            self.conditional_latency = conditional_latency
        if meas_map is not None:
            self.meas_map = meas_map
        super().__init__(
            backend_name=backend_name,
            backend_version=backend_version,
            n_qubits=n_qubits,
            basis_gates=basis_gates,
            gates=gates,
            local=local,
            simulator=simulator,
            conditional=conditional,
            open_pulse=open_pulse,
            memory=memory,
            max_shots=max_shots,
            coupling_map=coupling_map,
            max_experiments=max_experiments,
            sample_name=sample_name,
            n_registers=n_registers,
            register_map=register_map,
            configurable=configurable,
            credits_required=credits_required,
            online_date=online_date,
            display_name=display_name,
            description=description,
            tags=tags,
            **kwargs,
        )

    @classmethod
    def from_dict(
        cls: Type[QasmBackendConfigurationT], data: Dict[str, Any]
    ) -> QasmBackendConfigurationT:
        """Create a new GateConfig object from a dictionary.

        Args:
            data (dict): A dictionary representing the GateConfig to create.
                It will be in the same format as output by :func:`to_dict`.

        Returns:
            GateConfig: The GateConfig from the input dictionary.
        """
        in_data = copy.copy(data)
        gates = [GateConfig.from_dict(x) for x in in_data.pop("gates")]
        in_data["gates"] = gates
        input_uchannels = in_data.pop("u_channel_lo")
        u_channels = []
        for channel in input_uchannels:
            u_channels.append([UchannelLO.from_dict(x) for x in channel])
        in_data["u_channel_lo"] = u_channels
        return cls(**in_data)

    def to_dict(self) -> dict:
        """Return a dictionary format representation of the GateConfig.

        Returns:
            dict: The dictionary form of the GateConfig.
        """
        out_dict = super().to_dict()
        u_channel_lo = []
        for x in self.u_channel_lo:
            channel = []
            for y in x:
                channel.append(y.to_dict())
            u_channel_lo.append(channel)
        out_dict.update(
            {
                "n_uchannels": self.n_uchannels,
                "u_channel_lo": u_channel_lo,
                "meas_levels": self.meas_levels,
                "qubit_lo_range": self.qubit_lo_range,
                "meas_lo_range": self.meas_lo_range,
                "meas_kernels": self.meas_kernels,
                "discriminators": self.discriminators,
                "rep_times": self.rep_times,
                "dt": self.dt,
                "dtm": self.dtm,
            }
        )

        if hasattr(self, "channel_bandwidth"):
            out_dict["channel_bandwidth"] = self.channel_bandwidth
        if hasattr(self, "meas_map"):
            out_dict["meas_map"] = self.meas_map
        if hasattr(self, "acquisition_latency"):
            out_dict["acquisition_latency"] = self.acquisition_latency
        if hasattr(self, "conditional_latency"):
            out_dict["conditional_latency"] = self.conditional_latency
        if "channels" in out_dict:
            out_dict.pop("_qubit_channel_map")
            out_dict.pop("_channel_qubit_map")
            out_dict.pop("_control_channels")

        # Use GHz in dict
        if self.qubit_lo_range:
            out_dict["qubit_lo_range"] = [
                [min_range * 1e-9, max_range * 1e-9]
                for (min_range, max_range) in self.qubit_lo_range
            ]

        if self.meas_lo_range:
            out_dict["meas_lo_range"] = [
                [min_range * 1e-9, max_range * 1e-9]
                for (min_range, max_range) in self.meas_lo_range
            ]

        if self.rep_times:
            out_dict["rep_times"] = [_rt * 1e6 for _rt in self.rep_times]

        out_dict["dt"] *= 1e9
        out_dict["dtm"] *= 1e9

        if hasattr(self, "channel_bandwidth"):
            out_dict["channel_bandwidth"] = [
                [min_range * 1e-9, max_range * 1e-9]
                for (min_range, max_range) in self.channel_bandwidth
            ]

        if self.hamiltonian:
            hamiltonian = copy.deepcopy(self.hamiltonian)
            hamiltonian["vars"] = {
                k: v * 1e-9 if isinstance(v, numbers.Number) else v  # type: ignore[operator]
                for k, v in hamiltonian["vars"].items()
            }
            out_dict["hamiltonian"] = hamiltonian

        if hasattr(self, "channels"):
            out_dict["channels"] = self.channels

        return out_dict

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, QasmBackendConfiguration):
            if self.to_dict() == other.to_dict():
                return True
        return False

    @property
    def sample_rate(self) -> float:
        """Sample rate of the signal channels in Hz (1/dt)."""
        return 1.0 / self.dt

    @property
    def control_channels(self) -> Dict[Tuple[int, ...], List]:
        """Return the control channels"""
        return self._control_channels

    def drive(self, qubit: int) -> DriveChannel:
        """
        Return the drive channel for the given qubit.

        Raises:
            BackendConfigurationError: If the qubit is not a part of the system.

        Returns:
            Qubit drive channel.
        """
        if not 0 <= qubit < self.n_qubits:
            raise BackendConfigurationError(f"Invalid index for {qubit}-qubit system.")
        return DriveChannel(qubit)

    def measure(self, qubit: int) -> MeasureChannel:
        """
        Return the measure stimulus channel for the given qubit.

        Raises:
            BackendConfigurationError: If the qubit is not a part of the system.
        Returns:
            Qubit measurement stimulus line.
        """
        if not 0 <= qubit < self.n_qubits:
            raise BackendConfigurationError(f"Invalid index for {qubit}-qubit system.")
        return MeasureChannel(qubit)

    def acquire(self, qubit: int) -> AcquireChannel:
        """
        Return the acquisition channel for the given qubit.

        Raises:
            BackendConfigurationError: If the qubit is not a part of the system.
        Returns:
            Qubit measurement acquisition line.
        """
        if not 0 <= qubit < self.n_qubits:
            raise BackendConfigurationError(f"Invalid index for {qubit}-qubit systems.")
        return AcquireChannel(qubit)

    def control(self, qubits: Iterable[int] = None) -> List[ControlChannel]:
        """
        Return the secondary drive channel for the given qubit -- typically utilized for
        controlling multiqubit interactions. This channel is derived from other channels.

        Args:
            qubits: Tuple or list of qubits of the form `(control_qubit, target_qubit)`.

        Raises:
            BackendConfigurationError: If the ``qubits`` is not a part of the system or if
                the backend does not provide `channels` information in its configuration.

        Returns:
            List of control channels.
        """
        try:
            if isinstance(qubits, list):
                qubits = tuple(qubits)
            return self._control_channels[qubits]
        except KeyError as ex:
            raise BackendConfigurationError(
                f"Couldn't find the ControlChannel operating on qubits {qubits} on "
                f"{self.n_qubits}-qubit system. The ControlChannel information is retrieved "
                "from the backend."
            ) from ex
        except AttributeError as ex:
            raise BackendConfigurationError(
                f"This backend - '{self.backend_name}' does not provide channel information."
            ) from ex

    def get_channel_qubits(self, channel: Channel) -> List[int]:
        """
        Return a list of indices for qubits which are operated on directly by the given ``channel``.

        Raises:
            BackendConfigurationError: If ``channel`` is not a found or if
                the backend does not provide `channels` information in its configuration.

        Returns:
            List of qubits operated on my the given ``channel``.
        """
        try:
            return self._channel_qubit_map[channel]
        except KeyError as ex:
            raise BackendConfigurationError(f"Couldn't find the Channel - {channel}") from ex
        except AttributeError as ex:
            raise BackendConfigurationError(
                f"This backend - '{self.backend_name}' does not provide channel information."
            ) from ex

    def get_qubit_channels(self, qubit: Union[int, Iterable[int]]) -> List[Channel]:
        r"""Return a list of channels which operate on the given ``qubit``.

        Raises:
            BackendConfigurationError: If ``qubit`` is not a found or if
                the backend does not provide `channels` information in its configuration.

        Returns:
            List of ``Channel``\s operated on my the given ``qubit``.
        """
        channels = set()
        try:
            if isinstance(qubit, int):
                for key, value in self._qubit_channel_map.items():
                    if qubit in key:
                        channels.update(value)
                if len(channels) == 0:
                    raise KeyError
            elif isinstance(qubit, list):
                qubit = tuple(qubit)
                channels.update(self._qubit_channel_map[qubit])
            elif isinstance(qubit, tuple):
                channels.update(self._qubit_channel_map[qubit])
            return list(channels)
        except KeyError as ex:
            raise BackendConfigurationError(f"Couldn't find the qubit - {qubit}") from ex
        except AttributeError as ex:
            raise BackendConfigurationError(
                f"This backend - '{self.backend_name}' does not provide channel information."
            ) from ex

    def describe(self, channel: ControlChannel) -> Dict[DriveChannel, complex]:
        """
        Return a basic description of the channel dependency. Derived channels are given weights
        which describe how their frames are linked to other frames.
        For instance, the backend could be configured with this setting::

            u_channel_lo = [
                [UchannelLO(q=0, scale=1. + 0.j)],
                [UchannelLO(q=0, scale=-1. + 0.j), UchannelLO(q=1, scale=1. + 0.j)]
            ]

        Then, this method can be used as follows::

            backend.configuration().describe(ControlChannel(1))
                {DriveChannel(0): -1, DriveChannel(1): 1}

        Args:
            channel: The derived channel to describe.
        Raises:
            BackendConfigurationError: If channel is not a ControlChannel.
        Returns:
            Control channel derivations.
        """
        if not isinstance(channel, ControlChannel):
            raise BackendConfigurationError("Can only describe ControlChannels.")
        result = {}
        for u_chan_lo in self.u_channel_lo[channel.index]:
            result[DriveChannel(u_chan_lo.q)] = u_chan_lo.scale
        return result

    def _parse_channels(self, channels: dict) -> tuple:
        r"""
        Generates a dictionaries of ``Channel``\s, and tuple of qubit(s) they operate on.

        Args:
            channels: An optional dictionary containing information of each channel -- their
                purpose, type, and qubits operated on.

        Returns:
            qubit_channel_map: Dictionary mapping tuple of qubit(s) to list of ``Channel``\s.
            channel_qubit_map: Dictionary mapping ``Channel`` to list of qubit(s).
            control_channels: Dictionary mapping tuple of qubit(s), to list of
                ``ControlChannel``\s.
        """
        qubit_channel_map = defaultdict(list)
        channel_qubit_map = defaultdict(list)
        control_channels = defaultdict(list)
        channels_dict = {
            DriveChannel.prefix: DriveChannel,
            ControlChannel.prefix: ControlChannel,
            MeasureChannel.prefix: MeasureChannel,
            "acquire": AcquireChannel,
        }
        for channel, config in channels.items():
            channel_prefix, index = self._get_channel_prefix_index(channel)  # type: ignore[misc]
            channel_type = channels_dict[channel_prefix]  # type: ignore[has-type]
            qubits = tuple(config["operates"]["qubits"])
            if channel_prefix in channels_dict:  # type: ignore[has-type]
                qubit_channel_map[qubits].append(channel_type(index))  # type: ignore[has-type]
                channel_qubit_map[(channel_type(index))].extend(list(qubits))  # type: ignore[has-type]
                if channel_prefix == ControlChannel.prefix:  # type: ignore[has-type]
                    control_channels[qubits].append(channel_type(index))  # type: ignore[has-type]
        return dict(qubit_channel_map), dict(channel_qubit_map), dict(control_channels)

    def _get_channel_prefix_index(self, channel: str) -> str:
        """Return channel prefix and index from the given ``channel``.

        Args:
            channel: Name of channel.

        Raises:
            BackendConfigurationError: If invalid channel name is found.

        Return:
            Channel name and index. For example, if ``channel=acquire0``, this method
            returns ``acquire`` and ``0``.
        """
        channel_prefix = re.match(r"(?P<channel>[a-z]+)(?P<index>[0-9]+)", channel)
        try:
            return (
                channel_prefix.group("channel"),
                int(channel_prefix.group("index")),
            )  # type: ignore[return-value]
        except AttributeError as ex:
            raise BackendConfigurationError(f"Invalid channel name - '{channel}' found.") from ex
