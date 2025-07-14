# This module logs important Function Executor events to stdout.
# These events are used later during automatic Function Executor stdout/stderr
# stream processing so they have a strict format.
import datetime
import json
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class InitializationEventDetails:
    namespace: str
    graph_name: str
    graph_version: str
    function_name: str


def log_event_initialization_started(details: InitializationEventDetails) -> None:
    # Using standardized tags, see https://github.com/tensorlakeai/indexify/blob/main/docs/tags.md.
    _log_event(
        {
            "event": "function_executor_initialization_started",
            "namespace": details.namespace,
            "graph": details.graph_name,
            "graph_version": details.graph_version,
            "fn": details.function_name,
        }
    )


def log_event_initialization_finished(
    details: InitializationEventDetails, success: bool
) -> None:
    # Using standardized tags, see https://github.com/tensorlakeai/indexify/blob/main/docs/tags.md.
    _log_event(
        {
            "event": "function_executor_initialization_finished",
            "success": success,
            "namespace": details.namespace,
            "graph": details.graph_name,
            "graph_version": details.graph_version,
            "fn": details.function_name,
        }
    )


@dataclass
class TaskAllocationEventDetails:
    namespace: str
    graph_name: str
    graph_version: str
    function_name: str
    allocation_id: str
    task_id: str
    graph_invocation_id: str


def log_event_task_allocations_started(
    details: List[TaskAllocationEventDetails],
) -> None:
    # Using standardized tags, see https://github.com/tensorlakeai/indexify/blob/main/docs/tags.md.
    _log_event(
        {
            "event": "task_allocations_started",
            "allocations": [
                {
                    "namespace": alloc_info.namespace,
                    "graph": alloc_info.graph_name,
                    "graph_version": alloc_info.graph_version,
                    "fn": alloc_info.function_name,
                    "allocation_id": alloc_info.allocation_id,
                    "task_id": alloc_info.task_id,
                    "graph_invocation_id": alloc_info.graph_invocation_id,
                }
                for alloc_info in details
            ],
        }
    )


def log_event_task_allocations_finished(
    details: List[TaskAllocationEventDetails],
) -> None:
    _log_event(
        {
            "event": "task_allocations_finished",
            "allocations": [
                {
                    "namespace": alloc_info.namespace,
                    "graph": alloc_info.graph_name,
                    "graph_version": alloc_info.graph_version,
                    "fn": alloc_info.function_name,
                    "allocation_id": alloc_info.allocation_id,
                    "task_id": alloc_info.task_id,
                    "graph_invocation_id": alloc_info.graph_invocation_id,
                }
                for alloc_info in details
            ],
        }
    )


# Suffix used to filter Function Executor events in the stdout/stderr stream
# by stream processors.
_EVENT_SUFFIX = "tensorlake_function_executor_event:"


def _log_event(event: Dict[str, Any]) -> None:
    event["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
    print(_EVENT_SUFFIX, json.dumps(event), flush=True)
