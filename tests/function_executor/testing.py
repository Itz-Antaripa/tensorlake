import os
import subprocess
import tempfile
import unittest
from typing import Any, Dict, List, Optional

import grpc

from tensorlake.function_executor.proto.function_executor_pb2 import (
    BLOBChunk,
    ReadOnlyBLOB,
    RunTaskRequest,
    RunTaskResponse,
    SerializedObjectEncoding,
    SerializedObjectInsideBLOB,
    SerializedObjectManifest,
    WriteOnlyBlob,
)
from tensorlake.function_executor.proto.function_executor_pb2_grpc import (
    FunctionExecutorStub,
)
from tensorlake.function_executor.proto.server_configuration import GRPC_SERVER_OPTIONS
from tensorlake.functions_sdk.object_serializer import CloudPickleSerializer

# Default Executor range is 50000:51000.
# Use a value outside of this range to not conflict with other tests.
DEFAULT_FUNCTION_EXECUTOR_PORT: int = 60000


class FunctionExecutorProcessContextManager:
    def __init__(
        self,
        port: int = DEFAULT_FUNCTION_EXECUTOR_PORT,
        extra_args: List[str] = [],
        extra_env: Dict[str, str] = {},
        capture_std_outputs: bool = False,
    ):
        self.port = port
        self._args = [
            "function-executor",
            "--address",
            f"localhost:{port}",
            "--executor-id",
            "test-executor",
            "--function-executor-id",
            "test-function-executor",
        ]
        self._args.extend(extra_args)
        self._extra_env = extra_env
        self._capture_std_outputs = capture_std_outputs
        self._process: Optional[subprocess.Popen] = None
        self._stdout: Optional[str] = None
        self._stderr: Optional[str] = None

    def __enter__(self) -> "FunctionExecutorProcessContextManager":
        kwargs = {}
        if self._extra_env is not None:
            kwargs["env"] = os.environ.copy()
            kwargs["env"].update(self._extra_env)
        if self._capture_std_outputs:
            kwargs["stdout"] = subprocess.PIPE
            kwargs["stderr"] = subprocess.PIPE
        self._process = subprocess.Popen(self._args, **kwargs)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._process:
            self._process.terminate()
            if self._capture_std_outputs:
                self._stdout = self._process.stdout.read().decode("utf-8")
                self._stderr = self._process.stderr.read().decode("utf-8")
            self._process.__exit__(exc_type, exc_value, traceback)

    def read_stdout(self) -> Optional[str]:
        # Only call this after FE exits.
        return self._stdout

    def read_stderr(self) -> Optional[str]:
        # Only call this after FE exits.
        return self._stderr


def rpc_channel(context_manager: FunctionExecutorProcessContextManager) -> grpc.Channel:
    # The GRPC_SERVER_OPTIONS include the maximum message size which we need to set in the client channel.
    channel: grpc.Channel = grpc.insecure_channel(
        f"localhost:{context_manager.port}",
        options=GRPC_SERVER_OPTIONS,
    )
    try:
        SERVER_STARTUP_TIMEOUT_SEC = 5
        # This is not asyncio.Future but grpc.Future. It has a different interface.
        grpc.channel_ready_future(channel).result(timeout=SERVER_STARTUP_TIMEOUT_SEC)
        return channel
    except Exception as e:
        channel.close()
        raise Exception(
            f"Failed to connect to the gRPC server within {SERVER_STARTUP_TIMEOUT_SEC} seconds"
        ) from e


def run_task(
    stub: FunctionExecutorStub,
    function_name: str,
    input: Any,
    function_outputs_blob: WriteOnlyBlob,
    timeout_sec: Optional[int] = None,
) -> RunTaskResponse:
    function_input_blob: ReadOnlyBLOB = tmp_local_file_ro_blob()
    function_input_path: str = function_input_blob.uri.replace("file://", "", 1)
    function_input_data: bytes = CloudPickleSerializer.serialize(input)
    with open(function_input_path, "wb") as f:
        f.write(function_input_data)

    return stub.run_task(
        RunTaskRequest(
            namespace="test",
            graph_name="test",
            graph_version="1",
            function_name=function_name,
            graph_invocation_id="123",
            task_id="test-task",
            allocation_id="test-allocation",
            function_input_blob=function_input_blob,
            function_input=SerializedObjectInsideBLOB(
                manifest=SerializedObjectManifest(
                    encoding=SerializedObjectEncoding.SERIALIZED_OBJECT_ENCODING_BINARY_PICKLE,
                    encoding_version=0,
                    size=len(function_input_data),
                ),
                offset=0,
            ),
            function_outputs_blob=function_outputs_blob,
        ),
        timeout=timeout_sec,
    )


def deserialized_function_output(
    test_case: unittest.TestCase,
    function_outputs: List[SerializedObjectInsideBLOB],
    function_outputs_blob: WriteOnlyBlob,
) -> List[Any]:
    outputs: List[Any] = []
    for output in function_outputs:
        test_case.assertEqual(
            output.manifest.encoding,
            SerializedObjectEncoding.SERIALIZED_OBJECT_ENCODING_BINARY_PICKLE,
        )
        data: bytes = read_local_rw_blob_bytes(
            function_outputs_blob, output.offset, output.manifest.size
        )
        outputs.append(CloudPickleSerializer.deserialize(data))
    return outputs


def tmp_local_file_ro_blob() -> ReadOnlyBLOB:
    """Returns a temporary local file blob."""
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.close()
    return ReadOnlyBLOB(
        uri=f"file://{os.path.abspath(temp_file.name)}",
    )


def read_local_ro_blob_str(blob: ReadOnlyBLOB) -> str:
    """Reads a local blob and returns its content as a string."""
    file_path: str = blob.uri.replace("file://", "", 1)
    with open(file_path, "r") as f:
        return f.read()


# TODO: Use multiple chunks
def tmp_local_file_rw_blob() -> WriteOnlyBlob:
    """Returns a temporary local file blob for writing."""
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.close()
    return WriteOnlyBlob(
        chunks=[
            BLOBChunk(
                uri=f"file://{os.path.abspath(temp_file.name)}", size=5 * 1024 * 1024
            )
        ],
    )


# TODO: Use multiple chunks
def read_local_rw_blob_bytes(blob: WriteOnlyBlob, offset: int, size: int) -> bytes:
    """Reads a local blob and returns its content as bytes."""
    file_path: str = blob.chunks[0].uri.replace("file://", "", 1)
    with open(file_path, "rb") as f:
        f.seek(offset)
        return f.read(size)
