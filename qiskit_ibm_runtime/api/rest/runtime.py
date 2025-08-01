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

"""Runtime REST adapter."""

import logging
from datetime import datetime
from typing import Dict, Any, List, Union, Optional
import json

from qiskit_ibm_runtime.api.rest.base import RestAdapterBase
from qiskit_ibm_runtime.api.rest.program_job import ProgramJob
from qiskit_ibm_runtime.utils import local_to_utc
from .runtime_session import RuntimeSession

from ...utils import RuntimeEncoder
from .cloud_backend import CloudBackend

logger = logging.getLogger(__name__)


class Runtime(RestAdapterBase):
    """Rest adapter for Runtime base endpoints."""

    URL_MAP = {
        "programs": "/programs",
        "jobs": "/jobs",
        "backends": "/backends",
        "cloud_instance": "/instance",
        "cloud_usage": "/instances/usage",
    }

    def program_job(self, job_id: str) -> "ProgramJob":
        """Return an adapter for the job.

        Args:
            job_id: Job ID.

        Returns:
            The program job adapter.
        """
        return ProgramJob(self.session, job_id)

    def runtime_session(self, session_id: str = None) -> "RuntimeSession":
        """Return an adapter for the session.

        Args:
            session_id: Job ID of the first job in a session.

        Returns:
            The session adapter.
        """
        return RuntimeSession(self.session, session_id)

    def program_run(
        self,
        program_id: str,
        backend_name: Optional[str],
        params: Dict,
        image: Optional[str] = None,
        log_level: Optional[str] = None,
        session_id: Optional[str] = None,
        job_tags: Optional[List[str]] = None,
        max_execution_time: Optional[int] = None,
        start_session: Optional[bool] = False,
        session_time: Optional[int] = None,
        private: Optional[bool] = False,
    ) -> Dict:
        """Execute the program.

        Args:
            program_id: Program ID.
            backend_name: Name of the backend.
            params: Program parameters.
            image: Runtime image.
            log_level: Log level to use.
            session_id: ID of the first job in a runtime session.
            job_tags: Tags to be assigned to the job.
            max_execution_time: Maximum execution time in seconds.
            start_session: Set to True to explicitly start a runtime session. Defaults to False.
            session_time: Length of session in seconds.
            private: Marks job as private.

        Returns:
            JSON response.
        """
        url = self.get_url("jobs")
        payload: Dict[str, Any] = {
            "program_id": program_id,
            "params": params,
        }
        if image:
            payload["runtime"] = image
        if log_level:
            payload["log_level"] = log_level
        if backend_name:
            payload["backend"] = backend_name
        if session_id:
            payload["session_id"] = session_id
        if job_tags:
            payload["tags"] = job_tags
        if max_execution_time:
            payload["cost"] = max_execution_time
        if start_session:
            payload["start_session"] = start_session
            payload["session_time"] = session_time
        if private:
            payload["private"] = True
        data = json.dumps(payload, cls=RuntimeEncoder)
        return self.session.post(
            url, data=data, timeout=900, headers=self._HEADER_JSON_CONTENT
        ).json()

    def jobs_get(
        self,
        limit: int = None,
        skip: int = None,
        backend_name: str = None,
        pending: bool = None,
        program_id: str = None,
        job_tags: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        descending: bool = True,
    ) -> Dict:
        """Get a list of job data.

        Args:
            limit: Number of results to return.
            skip: Number of results to skip.
            backend_name: Name of the backend to retrieve jobs from.
            pending: Returns 'QUEUED' and 'RUNNING' jobs if True,
                returns 'DONE', 'CANCELLED' and 'ERROR' jobs if False.
            program_id: Filter by Program ID.
            job_tags: Filter by tags assigned to jobs. Matched jobs are associated with all tags.
            session_id: Job ID of the first job in a runtime session.
            created_after: Filter by the given start date, in local time. This is used to
                find jobs whose creation dates are after (greater than or equal to) this
                local date/time.
            created_before: Filter by the given end date, in local time. This is used to
                find jobs whose creation dates are before (less than or equal to) this
                local date/time.
            descending: If ``True``, return the jobs in descending order of the job
                creation date (i.e. newest first) until the limit is reached.

        Returns:
            JSON response.
        """
        url = self.get_url("jobs")
        payload: Dict[str, Union[int, str, List[str]]] = {}
        payload["exclude_params"] = False
        if limit:
            payload["limit"] = limit
        if skip:
            payload["offset"] = skip
        if backend_name:
            payload["backend"] = backend_name
        if pending is not None:
            payload["pending"] = "true" if pending else "false"
        if program_id:
            payload["program"] = program_id
        if job_tags:
            payload["tags"] = job_tags
        if session_id:
            payload["session_id"] = session_id
        if created_after:
            payload["created_after"] = local_to_utc(created_after).isoformat()
        if created_before:
            payload["created_before"] = local_to_utc(created_before).isoformat()
        if descending is False:
            payload["sort"] = "ASC"
        return self.session.get(url, params=payload, headers=self._HEADER_JSON_ACCEPT).json()

    def backend(self, backend_name: str) -> CloudBackend:
        """Return an adapter for the IBM backend.

        Args:
            backend_name: Name of the backend.

        Returns:
            The backend adapter.
        """
        return CloudBackend(self.session, backend_name)

    def backends(
        self,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Return a list of IBM backends.

        Args:
            timeout: Number of seconds to wait for the request.

        Returns:
            JSON response.
        """
        url = self.get_url("backends")
        return self.session.get(url, timeout=timeout, headers=self._HEADER_JSON_ACCEPT).json()

    def cloud_usage(self) -> Dict[str, Any]:
        """Return cloud instance usage information.

        Returns:
            JSON response.
        """
        url = self.get_url("cloud_usage")
        return self.session.get(url, headers=self._HEADER_JSON_ACCEPT).json()
