from typing import Any

from .function_executor_pb2 import (
    BLOBChunk,
    WriteOnlyBlob,
)


class MessageValidator:
    def __init__(self, message: Any):
        self._message = message

    def required_field(self, field_name: str) -> "MessageValidator":
        if not self._message.HasField(field_name):
            raise ValueError(
                f"Field '{field_name}' is required in {type(self._message).__name__}"
            )
        return self

    def required_serialized_object(self, field_name: str) -> "MessageValidator":
        """Validates the SerializedObject.

        Raises: ValueError: If the SerializedObject is invalid or not present."""
        self.required_field(field_name)
        return self.optional_serialized_object(field_name)

    def optional_serialized_object(self, field_name: str) -> "MessageValidator":
        """Validates the SerializedObject.

        Raises: ValueError: If the SerializedObject is invalid."""
        if not self._message.HasField(field_name):
            return self
        (
            MessageValidator(getattr(self._message, field_name))
            .required_serialized_object_manifest("manifest")
            .required_field("data")
        )

        return self

    def required_serialized_object_manifest(
        self, field_name: str
    ) -> "MessageValidator":
        """Validates the SerializedObjectManifest.

        Raises: ValueError: If the SerializedObjectManifest is invalid or not present.
        """
        self.required_field(field_name)
        (
            MessageValidator(getattr(self._message, field_name))
            .required_field("encoding")
            .required_field("encoding_version")
            .required_field("size")
        )

        return self

    def required_read_only_blob(self, field_name: str) -> "MessageValidator":
        """Validates the read-only BLOB.

        Raises: ValueError: If the read-only BLOB is invalid or not present."""
        self.required_field(field_name)
        (MessageValidator(getattr(self._message, field_name)).required_field("uri"))

        return self

    def optional_read_only_blob(self, field_name: str) -> "MessageValidator":
        """Validates the read-only BLOB.

        Raises: ValueError: If the read-only BLOB is invalid."""
        if not self._message.HasField(field_name):
            return self

        return self.required_read_only_blob(field_name)

    def required_serialized_object_inside_blob(
        self, field_name: str
    ) -> "MessageValidator":
        """Validates the SerializedObjectInsideBLOB.

        Raises: ValueError: If the SerializedObjectInsideBLOB is invalid or not present.
        """
        self.required_field(field_name)
        return self.optional_serialized_object_inside_blob(field_name)

    def optional_serialized_object_inside_blob(
        self, field_name: str
    ) -> "MessageValidator":
        """Validates the SerializedObjectInsideBLOB.

        Raises: ValueError: If the SerializedObjectInsideBLOB is invalid."""
        if not self._message.HasField(field_name):
            return self
        (
            MessageValidator(getattr(self._message, field_name))
            .required_serialized_object_manifest("manifest")
            .required_field("offset")
        )

        return self

    def required_write_only_blob(self, field_name: str) -> "MessageValidator":
        """Validates the write-only BLOB.

        Raises: ValueError: If the write-only BLOB is invalid or not present."""
        self.required_field(field_name)
        blob: WriteOnlyBlob = getattr(self._message, field_name)
        if len(blob.chunks) < 1:
            raise ValueError(
                f"WriteOnlyBlob '{field_name}' must have at least one chunk"
            )
        for chunk in blob.chunks:
            self._validate_blob_chunk(chunk)
        return self

    def _validate_blob_chunk(self, blob_chunk: BLOBChunk) -> "MessageValidator":
        """Validates the BLOB chunk.

        Raises: ValueError: If the BLOB chunk is invalid or not present."""
        (MessageValidator(blob_chunk).required_field("uri").required_field("size"))

        return self
