import pytest
from abc import ABC, abstractmethod
from unittest.mock import Mock, patch
import threading
import time
from prober.probe import Probe


def test_probe_is_abstract():
    """Test that Probe class cannot be instantiated directly"""
    with pytest.raises(TypeError):
        Probe({})


def test_probe_initialization():
    """Test probe initialization with config"""
    config = {"collection_interval": 300}

    class TestProbe(Probe):
        def _execute_check(self) -> bool:
            return True

    probe = TestProbe(config)
    assert probe.collection_interval == 300
    assert probe.total_failures == 0


def test_probe_execute_abstract():
    """Test that execute method must be implemented"""

    class IncompleteProbe(Probe):
        pass

    with pytest.raises(TypeError):
        IncompleteProbe({})


def test_probe_failure_tracking():
    """Test that failures are tracked correctly"""
    config = {"collection_interval": 300}

    class FailingProbe(Probe):
        def _execute_check(self) -> bool:
            return False

    probe = FailingProbe(config)
    result = probe.execute()
    assert result is False
    assert probe.total_failures == 1


def test_probe_success_no_failure_increment():
    """Test that successful executions don't increment failure count"""
    config = {"collection_interval": 300}

    class SuccessProbe(Probe):
        def _execute_check(self) -> bool:
            return True

    probe = SuccessProbe(config)
    result = probe.execute()
    assert result is True
    assert probe.total_failures == 0


@patch("prober.probe.logger")
def test_probe_logs_failure(mock_logger):
    """Test that failures are logged"""
    config = {"collection_interval": 300}

    class FailingProbe(Probe):
        def _execute_check(self) -> bool:
            return False

    probe = FailingProbe(config)
    probe.execute()
    mock_logger.warning.assert_called_once()


def test_probe_start_creates_thread():
    """Test that start_probe creates a thread"""
    config = {"collection_interval": 300}

    class TestProbe(Probe):
        def _execute_check(self) -> bool:
            return True

    probe = TestProbe(config)
    probe.start_probe()

    assert hasattr(probe, "_thread")
    assert isinstance(probe._thread, threading.Thread)
    assert probe._thread.is_alive()

    # Cleanup
    probe._running = False
    probe._thread.join(timeout=1)


def test_probe_respects_collection_interval():
    """Test that probe respects collection interval"""
    config = {"collection_interval": 0.1}  # Small interval for testing
    execute_count = 0

    class TestProbe(Probe):
        def _execute_check(self) -> bool:
            nonlocal execute_count
            execute_count += 1
            return True

    probe = TestProbe(config)
    probe.start_probe()

    # Wait for a bit more than one interval
    time.sleep(0.15)
    probe._running = False
    probe._thread.join(timeout=1)

    # Should have executed at least once
    assert execute_count >= 1


def test_probe_exception_handling():
    """Test that exceptions in execute are caught and logged"""
    config = {"collection_interval": 300}

    class ErrorProbe(Probe):
        def _execute_check(self) -> bool:
            raise Exception("Test error")

    probe = ErrorProbe(config)
    with patch("prober.probe.logger") as mock_logger:
        result = probe.execute()
        assert result is False
        assert probe.total_failures == 1
        mock_logger.error.assert_called_once()
