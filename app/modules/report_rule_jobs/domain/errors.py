class RuleJobError(Exception):
    """Base for rule-analysis-job errors."""


class RuleJobNotFoundError(RuleJobError):
    def __init__(self, message: str = "Rule job not found") -> None:
        super().__init__(message)
