import time
import pytest
from unittest.mock import patch, Mock, call
import threading
from prometheus_client import Counter, REGISTRY
from prober.app import EmailProbeApp
from prober.probes.dns_probe import DNSMXDomainProbe, DNSMXIPProbe
from prober.probes.connectivity_probe import (
    IPPingProbe,
    HTTPPortProbe,
    HTTPSPortProbe,
    MailPortProbe,
    SMTPPortProbe,
)
from prober.probes.security_probe import (
    HTTPSCertificateProbe,
    SMTPCertificateProbe,
)
from prober.probes.mail_probe import AuthenticatedSMTPSendProbe, UnauthenticatedSMTPProbe


@pytest.fixture
def app_config():
    return {
        "collection_interval": 300,
        "server_ip": "192.168.1.1",
        "server_hostname": "mail.example.com",
        "mx_domain": "example.com",
        "expected_ip": "192.168.1.1",  # Added for DNSMXIPProbe
        "http_port": 80,
        "https_port": 443,
        "mail_port": 25,
        "smtp_port": 587,
        "smtp_username": "test@example.com",
        "smtp_password": "password123",
        "metrics_export_port": 9101,
        "circuit_breaker_failure_threshold": 5,
        "circuit_breaker_recovery_timeout": 60,
    }


@pytest.fixture(autouse=True)
def clear_prometheus_registry():
    """Clear Prometheus registry before each test"""
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        REGISTRY.unregister(collector)


class TestEmailProbeApp:
    def test_probe_initialization(self, app_config):
        app = EmailProbeApp(app_config)

        # Verify all probes are initialized
        assert any(isinstance(p, DNSMXDomainProbe) for p in app.probes)
        assert any(isinstance(p, DNSMXIPProbe) for p in app.probes)
        assert any(isinstance(p, IPPingProbe) for p in app.probes)
        # assert any(isinstance(p, HTTPPortProbe) for p in app.probes)
        assert any(isinstance(p, HTTPSPortProbe) for p in app.probes)
        assert any(isinstance(p, MailPortProbe) for p in app.probes)
        assert any(isinstance(p, SMTPPortProbe) for p in app.probes)
        assert any(isinstance(p, HTTPSCertificateProbe) for p in app.probes)
        # assert any(isinstance(p, SMTPCertificateProbe) for p in app.probes)
        # assert any(isinstance(p, AuthenticatedSMTPSendProbe) for p in app.probes)
        assert any(isinstance(p, UnauthenticatedSMTPProbe) for p in app.probes)

    def test_missing_config(self):
        with pytest.raises(ValueError):
            EmailProbeApp({})

    @patch("prober.app.HTTPServer")
    def test_http_server_start(self, mock_http_server, app_config):
        app = EmailProbeApp(app_config)
        app.start()

        # Verify HTTPServer was created with correct port
        mock_http_server.assert_called_once()
        args = mock_http_server.call_args[0]
        assert args[0] == ('', app_config["metrics_export_port"])  # Server address
        
        app.stop()

    def test_probe_initialization(self, app_config):
        """Test that probes are properly initialized with circuit breakers."""
        app = EmailProbeApp(app_config)

        # Verify all probes have circuit breakers
        for probe in app.probes:
            assert hasattr(probe, 'circuit_breaker')
            assert probe.circuit_breaker.fail_max == app_config["circuit_breaker_failure_threshold"]
            assert probe.circuit_breaker.reset_timeout == app_config["circuit_breaker_recovery_timeout"]

    @patch("prober.app.HTTPServer")
    def test_start_all_probes(self, mock_http_server, app_config):
        app = EmailProbeApp(app_config)

        # Mock all probe start methods
        for probe in app.probes:
            probe.start_probe = Mock()

        app.start()

        # Verify all probes were started
        for probe in app.probes:
            probe.start_probe.assert_called_once()
            
        app.stop()

    @patch("prober.app.HTTPServer")
    def test_stop_all_probes(self, mock_http_server, app_config):
        app = EmailProbeApp(app_config)

        # Mock all probe stop methods
        for probe in app.probes:
            probe.stop_probe = Mock()
            
        app.start()
        app.stop()

        # Verify all probes were stopped
        for probe in app.probes:
            probe.stop_probe.assert_called_once()
