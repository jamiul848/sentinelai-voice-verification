"""Sentinel Voice - Database Exceptions Module.

Defines custom, safe database exceptions without exposing credentials,
internal table topology, or database engine trace details.
"""


class DatabaseError(Exception):
    """Base exception for all database-related operations."""

    def __init__(self, message: str = "A database error occurred.") -> None:
        super().__init__(message)
        self.message = message


class EntityNotFoundError(DatabaseError):
    """Raised when a queried entity does not exist in the database."""

    def __init__(self, entity_name: str, identifier: str) -> None:
        message = f"{entity_name} with identifier '{identifier}' was not found."
        super().__init__(message)
        self.entity_name = entity_name
        self.identifier = identifier


class DuplicateEntityError(DatabaseError):
    """Raised when an insertion violates a unique constraint."""

    def __init__(self, entity_name: str, field_name: str, value: str) -> None:
        message = f"{entity_name} with {field_name}='{value}' already exists."
        super().__init__(message)
        self.entity_name = entity_name
        self.field_name = field_name
        self.value = value


class DatabaseConnectionError(DatabaseError):
    """Raised when connecting to the database server fails."""

    def __init__(self, message: str = "Failed to establish a database connection.") -> None:
        super().__init__(message)


class DatabaseTransactionError(DatabaseError):
    """Raised when a transactional commit or rollback fails."""

    def __init__(self, message: str = "Database transaction failed.") -> None:
        super().__init__(message)

