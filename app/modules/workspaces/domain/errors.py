class WorkspaceError(Exception):
    """Base class for all workspace-domain errors."""


class WorkspaceNotFoundError(WorkspaceError):
    """Workspace does not exist, or caller may not see it. Maps to 404."""

    def __init__(self, message: str = "Workspace not found") -> None:
        super().__init__(message)


class ArticleNotFoundError(WorkspaceError):
    """Article does not exist, is not in the requested workspace, or out of caller's scope. Maps to 404."""

    def __init__(self, message: str = "Article not found") -> None:
        super().__init__(message)


class WorkspaceNameTakenError(WorkspaceError):
    """Owner already has a workspace with this name (case-insensitive). Maps to 409."""

    def __init__(self, message: str = "Workspace name already in use") -> None:
        super().__init__(message)


class ArticleStateConflictError(WorkspaceError):
    """Article is not in a state that allows this operation. Maps to 409."""

    def __init__(self, message: str = "Article is not in a valid state for this operation") -> None:
        super().__init__(message)


class QcMisconfiguredError(WorkspaceError):
    """A QC user reached workspaces code with no qc_product. Data-integrity error. Maps to 500."""

    def __init__(self, message: str = "QC user has no qc_product assigned") -> None:
        super().__init__(message)
