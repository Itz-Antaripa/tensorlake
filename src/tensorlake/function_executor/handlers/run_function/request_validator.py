from ...proto.function_executor_pb2 import RunTaskRequest
from ...proto.message_validator import MessageValidator


class RequestValidator:
    def __init__(self, request: RunTaskRequest):
        self._request = request
        self._message_validator = MessageValidator(request)

    def check(self):
        """Validates the request.

        Raises: ValueError: If the request is invalid.
        """
        (
            self._message_validator.required_field("namespace")
            .required_field("graph_name")
            .required_field("graph_version")
            .required_field("function_name")
            .required_field("graph_invocation_id")
            .required_field("task_id")
            .required_field("allocation_id")
            .required_read_only_blob("function_input_blob")
            .required_serialized_object_inside_blob("function_input")
            .optional_read_only_blob("function_init_value_blob")
            .optional_serialized_object_inside_blob("function_init_value")
            .required_write_only_blob("function_outputs_blob")
        )
