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

    @patch("prober.app.start_http_server")  # Updated patch path
    def test_metrics_server_start(self, mock_start_server, app_config):
        app = EmailProbeApp(app_config)
        app.start()

        mock_start_server.assert_called_once_with(app_config["metrics_export_port"])

    def test_probe_counter_initialization(self, app_config):
        app = EmailProbeApp(app_config)

        assert isinstance(app.probe_counter, Counter)
        assert app.probe_counter._name == "email_probe_success_count"
        assert "success" in app.probe_counter._labelnames
        assert "probe" in app.probe_counter._labelnames

    def test_start_all_probes(self, app_config):
        app = EmailProbeApp(app_config)

        # Mock all probe start methods
        for probe in app.probes:
            probe.start_probe = Mock()

        app.start()

        # Verify all probes were started
        for probe in app.probes:
            probe.start_probe.assert_called_once()

    def test_stop_all_probes(self, app_config):
        app = EmailProbeApp(app_config)

        # Mock all probe stop methods
        for probe in app.probes:
            probe.stop_probe = Mock()
            
        app.start()
        app.stop()
        

        # Verify all probes were stopped
        for probe in app.probes:
            probe.stop_probe.assert_called_once()
