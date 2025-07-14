import time
from typing import List, Optional

from tensorlake.functions_sdk.functions import (
    FunctionCallResult,
    GraphInvocationContext,
    TensorlakeFunctionWrapper,
)
from tensorlake.functions_sdk.graph_definition import ComputeGraphMetadata
from tensorlake.functions_sdk.invocation_state.invocation_state import InvocationState

from ...blob_store.blob_store import BLOBStore
from ...events import (
    TaskAllocationEventDetails,
    log_event_task_allocations_finished,
    log_event_task_allocations_started,
)
from ...logger import FunctionExecutorLogger
from ...proto.function_executor_pb2 import RunTaskRequest, RunTaskResponse
from .function_inputs_loader import FunctionInputs, FunctionInputsLoader
from .response_helper import ResponseHelper


class Handler:
    def __init__(
        self,
        request: RunTaskRequest,
        invocation_state: InvocationState,
        function_wrapper: TensorlakeFunctionWrapper,
        graph_metadata: ComputeGraphMetadata,
        blob_store: BLOBStore,
        logger: FunctionExecutorLogger,
    ):
        self._request: RunTaskRequest = request
        self._invocation_state: InvocationState = invocation_state
        self._logger = logger.bind(
            module=__name__,
            invocation_id=request.graph_invocation_id,
            task_id=request.task_id,
            allocation_id=request.allocation_id,
        )
        self._function_wrapper: TensorlakeFunctionWrapper = function_wrapper
        self._input_loader = FunctionInputsLoader(request, blob_store, self._logger)
        self._response_helper = ResponseHelper(
            request=request,
            graph_metadata=graph_metadata,
            blob_store=blob_store,
            logger=self._logger,
        )

    def run(self) -> RunTaskResponse:
        """Runs the task.

        Raises an exception if our own code failed, customer function failure doesn't result in any exception.
        """
        event_details: List[TaskAllocationEventDetails] = [
            TaskAllocationEventDetails(
                namespace=self._request.namespace,
                graph_name=self._request.graph_name,
                graph_version=self._request.graph_version,
                function_name=self._request.function_name,
                allocation_id=self._request.allocation_id,
                task_id=self._request.task_id,
                graph_invocation_id=self._request.graph_invocation_id,
            )
        ]
        log_event_task_allocations_started(event_details)
        try:
            return self._run()
        finally:
            log_event_task_allocations_finished(event_details)

    def _run(self) -> RunTaskResponse:
        inputs: FunctionInputs = self._input_loader.load()
        fe_log_start: int = self._logger.end()
        result: Optional[FunctionCallResult] = None

        try:
            result = self._run_func(inputs)
        except BaseException as e:
            return self._response_helper.from_function_exception(
                exception=e,
                fe_log_start=fe_log_start,
                metrics=None,
            )

        return self._response_helper.from_function_call(
            result=result, fe_log_start=fe_log_start
        )

    def _run_func(self, inputs: FunctionInputs) -> FunctionCallResult:
        self._logger.info("running function")
        start_time = time.monotonic()

        try:
            ctx: GraphInvocationContext = GraphInvocationContext(
                invocation_id=self._request.graph_invocation_id,
                graph_name=self._request.graph_name,
                graph_version=self._request.graph_version,
                invocation_state=self._invocation_state,
            )
            return self._function_wrapper.invoke_fn_ser(
                ctx, inputs.input, inputs.init_value
            )
        finally:
            self._logger.info(
                "function finished",
                duration_sec=f"{time.monotonic() - start_time:.3f}",
            )
