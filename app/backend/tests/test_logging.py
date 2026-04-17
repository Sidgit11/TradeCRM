"""Tests for the logging configuration."""
import logging

import pytest

from app.logging_config import get_logger, setup_logging


class TestLoggingConfig:
    def test_get_logger_returns_named_logger(self):
        logger = get_logger("test.module")
        assert logger.name == "tradecrm.test.module"

    def test_get_logger_returns_logger_instance(self):
        logger = get_logger("foo")
        assert isinstance(logger, logging.Logger)

    def test_setup_logging_sets_root_level(self):
        setup_logging("WARNING")
        root = logging.getLogger()
        assert root.level == logging.WARNING
        setup_logging("INFO")

    def test_different_modules_get_different_loggers(self):
        logger_a = get_logger("module_a")
        logger_b = get_logger("module_b")
        assert logger_a.name != logger_b.name
