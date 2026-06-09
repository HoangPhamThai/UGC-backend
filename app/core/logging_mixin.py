"""
Logging mixin for use cases and repositories.
"""

import logging
from typing import Optional


class LoggerMixin:
    """Mixin class that provides logging capabilities."""

    @property
    def logger(self) -> logging.Logger:
        """Get logger instance for the class."""
        return logging.getLogger(
            self.__class__.__module__ + "." + self.__class__.__name__
        )

    def log_info(self, message: str, *args, **kwargs) -> None:
        """Log an info message."""
        self.logger.info(message, *args, **kwargs)

    def log_error(self, message: str, *args, **kwargs) -> None:
        """Log an error message."""
        self.logger.error(message, *args, **kwargs)

    def log_warning(self, message: str, *args, **kwargs) -> None:
        """Log a warning message."""
        self.logger.warning(message, *args, **kwargs)

    def log_debug(self, message: str, *args, **kwargs) -> None:
        """Log a debug message."""
        self.logger.debug(message, *args, **kwargs)

    def log_exception(
        self, message: str, *args, exc_info: Optional[bool] = True, **kwargs
    ) -> None:
        """Log an exception."""
        self.logger.error(message, *args, exc_info=exc_info, **kwargs)
