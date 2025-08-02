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
    config = {
        "collection_interval": 300,
        "circuit_breaker_failure_threshold": 5,
        "circuit_breaker_recovery_timeout": 60,
        "backoff_base_interval": 300,
        "backoff_max_interval": 3600,
        "backoff_multiplier": 2.0,
        "backoff_max_failures": 5,
        "enable_error_categorization": True,
        "enable_enhanced_logging": True,
        "resource_check_enabled": True,
        "resource_memory_warning_mb": 256,
        "resource_thread_warning_count": 50,
    }

    class TestProbe(Probe):
        def _execute_check(self) -> bool:
            return True

    probe = TestProbe(config)
    assert probe.collection_interval == 300
    assert probe.total_failures == 0
    assert probe.consecutive_failures == 0


def test_probe_execute_abstract():
    """Test that execute method must be implemented"""

    class IncompleteProbe(Probe):
        pass

    with pytest.raises(TypeError):
        IncompleteProbe({})


def test_probe_failure_tracking():
    """Test that failures are tracked correctly"""
    config = {
        "collection_interval": 300,
        "circuit_breaker_failure_threshold": 5,
        "circuit_breaker_recovery_timeout": 60,
        "backoff_base_interval": 300,
        "backoff_max_interval": 3600,
        "backoff_multiplier": 2.0,
        "backoff_max_failures": 5,
        "enable_error_categorization": True,
        "enable_enhanced_logging": True,
        "resource_check_enabled": True,
        "resource_memory_warning_mb": 256,
        "resource_thread_warning_count": 50,
    }

    class FailingProbe(Probe):
        def _execute_check(self) -> bool:
            return False

    probe = FailingProbe(config)
    result = probe.execute()
    assert result is False
    assert probe.total_failures == 1
    assert probe.consecutive_failures == 1


def test_probe_success_no_failure_increment():
    """Test that successful executions don't increment failure count"""
    config = {
        "collection_interval": 300,
        "circuit_breaker_failure_threshold": 5,
        "circuit_breaker_recovery_timeout": 60,
        "backoff_base_interval": 300,
        "backoff_max_interval": 3600,
        "backoff_multiplier": 2.0,
        "backoff_max_failures": 5,
        "enable_error_categorization": True,
        "enable_enhanced_logging": True,
        "resource_check_enabled": True,
        "resource_memory_warning_mb": 256,
        "resource_thread_warning_count": 50,
    }

    class SuccessProbe(Probe):
        def _execute_check(self) -> bool:
            return True

    probe = SuccessProbe(config)
    result = probe.execute()
    assert result is True
    assert probe.total_failures == 0
    assert probe.consecutive_failures == 0


@patch("prober.probe.logger")
def test_probe_logs_failure(mock_logger):
    """Test that failures are logged"""
    config = {
        "collection_interval": 300,
        "circuit_breaker_failure_threshold": 5,
        "circuit_breaker_recovery_timeout": 60,
        "backoff_base_interval": 300,
        "backoff_max_interval": 3600,
        "backoff_multiplier": 2.0,
        "backoff_max_failures": 5,
        "enable_error_categorization": True,
        "enable_enhanced_logging": True,
        "resource_check_enabled": True,
        "resource_memory_warning_mb": 256,
        "resource_thread_warning_count": 50,
    }

    class FailingProbe(Probe):
        def _execute_check(self) -> bool:
            return False

    probe = FailingProbe(config)
    probe.execute()
    mock_logger.warning.assert_called_once()


def test_probe_start_creates_thread():
    """Test that start_probe creates a thread"""
    config = {
        "collection_interval": 300,
        "circuit_breaker_failure_threshold": 5,
        "circuit_breaker_recovery_timeout": 60,
        "backoff_base_interval": 300,
        "backoff_max_interval": 3600,
        "backoff_multiplier": 2.0,
        "backoff_max_failures": 5,
        "enable_error_categorization": True,
        "enable_enhanced_logging": True,
        "resource_check_enabled": True,
        "resource_memory_warning_mb": 256,
        "resource_thread_warning_count": 50,
    }

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
    config = {
        "collection_interval": 0.1,  # Small interval for testing
        "circuit_breaker_failure_threshold": 5,
        "circuit_breaker_recovery_timeout": 60,
        "backoff_base_interval": 0.1,
        "backoff_max_interval": 3600,
        "backoff_multiplier": 2.0,
        "backoff_max_failures": 5,
        "enable_error_categorization": True,
        "enable_enhanced_logging": True,
        "resource_check_enabled": True,
        "resource_memory_warning_mb": 256,
        "resource_thread_warning_count": 50,
    }
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
    config = {
        "collection_interval": 300,
        "circuit_breaker_failure_threshold": 5,
        "circuit_breaker_recovery_timeout": 60,
        "backoff_base_interval": 300,
        "backoff_max_interval": 3600,
        "backoff_multiplier": 2.0,
        "backoff_max_failures": 5,
        "enable_error_categorization": True,
        "enable_enhanced_logging": True,
        "resource_check_enabled": True,
        "resource_memory_warning_mb": 256,
        "resource_thread_warning_count": 50,
    }

    class ErrorProbe(Probe):
        def _execute_check(self) -> bool:
            raise Exception("Test error")

    probe = ErrorProbe(config)
    with patch("prober.probe.logger") as mock_logger:
        result = probe.execute()
        assert result is False
        assert probe.total_failures == 1
        mock_logger.error.assert_called_once()


def test_consecutive_failure_reset_on_success():
    """Test that consecutive failures are reset on success"""
    config = {
        "collection_interval": 300,
        "circuit_breaker_failure_threshold": 5,
        "circuit_breaker_recovery_timeout": 60,
        "backoff_base_interval": 300,
        "backoff_max_interval": 3600,
        "backoff_multiplier": 2.0,
        "backoff_max_failures": 5,
        "enable_error_categorization": True,
        "enable_enhanced_logging": True,
        "resource_check_enabled": True,
        "resource_memory_warning_mb": 256,
        "resource_thread_warning_count": 50,
    }

    call_count = 0
    class AlternatingProbe(Probe):
        def _execute_check(self) -> bool:
            nonlocal call_count
            call_count += 1
            return call_count > 2  # First 2 calls fail, then succeed

    probe = AlternatingProbe(config)
    
    # First failure
    result = probe.execute()
    assert result is False
    assert probe.consecutive_failures == 1
    
    # Second failure
    result = probe.execute()
    assert result is False
    assert probe.consecutive_failures == 2
    
    # Success - should reset consecutive failures
    result = probe.execute()
    assert result is True
    assert probe.consecutive_failures == 0


def test_backoff_calculation():
    """Test exponential backoff calculation"""
    config = {
        "collection_interval": 300,
        "circuit_breaker_failure_threshold": 5,
        "circuit_breaker_recovery_timeout": 60,
        "backoff_base_interval": 100,
        "backoff_max_interval": 1000,
        "backoff_multiplier": 2.0,
        "backoff_max_failures": 3,
    }

    class TestProbe(Probe):
        def _execute_check(self) -> bool:
            return True

    probe = TestProbe(config)
    
    # No failures - should return normal interval
    assert probe._calculate_backoff_interval() == 300
    
    # 1 failure: 100 * 2^1 = 200 (plus jitter)
    probe.consecutive_failures = 1
    interval = probe._calculate_backoff_interval()
    assert 160 <= interval <= 240  # 200 ± 20%
    
    # 2 failures: 100 * 2^2 = 400 (plus jitter)
    probe.consecutive_failures = 2
    interval = probe._calculate_backoff_interval()
    assert 320 <= interval <= 480  # 400 ± 20%
    
    # 3 failures: 100 * 2^3 = 800 (plus jitter)
    probe.consecutive_failures = 3
    interval = probe._calculate_backoff_interval()
    assert 640 <= interval <= 960  # 800 ± 20%
    
    # 5 failures - should cap at max_failures (3)
    probe.consecutive_failures = 5
    interval = probe._calculate_backoff_interval()
    assert 640 <= interval <= 960  # Still 800 ± 20%


def test_backoff_max_interval_cap():
    """Test that backoff is capped at max_interval"""
    config = {
        "collection_interval": 300,
        "circuit_breaker_failure_threshold": 5,
        "circuit_breaker_recovery_timeout": 60,
        "backoff_base_interval": 100,
        "backoff_max_interval": 500,  # Lower max
        "backoff_multiplier": 2.0,
        "backoff_max_failures": 5,
        "enable_error_categorization": True,
        "enable_enhanced_logging": True,
        "resource_check_enabled": True,
        "resource_memory_warning_mb": 256,
        "resource_thread_warning_count": 50,
    }

    class TestProbe(Probe):
        def _execute_check(self) -> bool:
            return True

    probe = TestProbe(config)
    
    # 4 failures would be 100 * 2^4 = 1600, but should cap at 500
    probe.consecutive_failures = 4
    interval = probe._calculate_backoff_interval()
    assert 400 <= interval <= 600  # 500 ± 20%


def test_backoff_minimum_interval():
    """Test that backoff respects minimum interval of 30 seconds"""
    config = {
        "collection_interval": 300,
        "circuit_breaker_failure_threshold": 5,
        "circuit_breaker_recovery_timeout": 60,
        "backoff_base_interval": 10,  # Very low base
        "backoff_max_interval": 3600,
        "backoff_multiplier": 1.1,  # Small multiplier
        "backoff_max_failures": 5,
        "enable_error_categorization": True,
        "enable_enhanced_logging": True,
        "resource_check_enabled": True,
        "resource_memory_warning_mb": 256,
        "resource_thread_warning_count": 50,
    }

    class TestProbe(Probe):
        def _execute_check(self) -> bool:
            return True

    probe = TestProbe(config)
    
    # Even with 1 failure, should not go below 30 seconds
    probe.consecutive_failures = 1
    interval = probe._calculate_backoff_interval()
    assert interval >= 30.0


def test_error_categorization():
    """Test error categorization functionality"""
    config = {
        "collection_interval": 300,
        "circuit_breaker_failure_threshold": 5,
        "circuit_breaker_recovery_timeout": 60,
        "backoff_base_interval": 300,
        "backoff_max_interval": 3600,
        "backoff_multiplier": 2.0,
        "backoff_max_failures": 5,
        "enable_error_categorization": True,
        "enable_enhanced_logging": True,
        "resource_check_enabled": True,
        "resource_memory_warning_mb": 256,
        "resource_thread_warning_count": 50,
    }

    class TestProbe(Probe):
        def _execute_check(self) -> bool:
            return True

    probe = TestProbe(config)
    
    # Test network error categorization
    import socket
    network_error = socket.error("Connection refused")
    assert probe._categorize_error(network_error) == "network"
    
    # Test timeout error categorization
    timeout_error = socket.timeout("Operation timed out")
    assert probe._categorize_error(timeout_error) == "timeout"
    
    # Test SSL error categorization
    import ssl
    ssl_error = ssl.SSLError("Certificate verification failed")
    assert probe._categorize_error(ssl_error) == "cert"
    
    # Test authentication error categorization
    auth_error = Exception("Authentication failed")
    assert probe._categorize_error(auth_error) == "auth"
    
    # Test unknown error categorization
    unknown_error = ValueError("Some random error")
    assert probe._categorize_error(unknown_error) == "unknown"


def test_error_categorization_disabled():
    """Test that error categorization can be disabled"""
    config = {
        "collection_interval": 300,
        "circuit_breaker_failure_threshold": 5,
        "circuit_breaker_recovery_timeout": 60,
        "backoff_base_interval": 300,
        "backoff_max_interval": 3600,
        "backoff_multiplier": 2.0,
        "backoff_max_failures": 5,
        "enable_error_categorization": False,
        "enable_enhanced_logging": True,
    }

    class TestProbe(Probe):
        def _execute_check(self) -> bool:
            return True

    probe = TestProbe(config)
    
    # Should return "unknown" when categorization is disabled
    import socket
    network_error = socket.error("Connection refused")
    assert probe._categorize_error(network_error) == "unknown"


def test_dns_error_categorization():
    """Test DNS error categorization"""
    config = {
        "collection_interval": 300,
        "circuit_breaker_failure_threshold": 5,
        "circuit_breaker_recovery_timeout": 60,
        "backoff_base_interval": 300,
        "backoff_max_interval": 3600,
        "backoff_multiplier": 2.0,
        "backoff_max_failures": 5,
        "enable_error_categorization": True,
        "enable_enhanced_logging": True,
        "resource_check_enabled": True,
        "resource_memory_warning_mb": 256,
        "resource_thread_warning_count": 50,
    }

    class TestProbe(Probe):
        def _execute_check(self) -> bool:
            return True

    probe = TestProbe(config)
    
    # Test DNS error categorization
    import dns.exception
    dns_error = dns.exception.DNSException("DNS lookup failed")
    assert probe._categorize_error(dns_error) == "dns"
