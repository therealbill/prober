import pytest
from unittest.mock import patch, Mock, call
import socket
import subprocess
import platform
from prober.probes.connectivity_probe import (
    IPPingProbe,
    HTTPPortProbe,
    HTTPSPortProbe,
    MailPortProbe,
    SMTPPortProbe,
)


@pytest.fixture
def connectivity_config():
    return {
        "collection_interval": 300,
        "server_ip": "192.168.1.1",
        "server_hostname": "mail.example.com",
        "http_port": 80,
        "https_port": 443,
        "mail_port": 25,
        "smtp_port": 587,
    }


class TestIPPingProbe:
    @patch("platform.system")
    @patch("subprocess.run")
    def test_ping_success(self, mock_run, mock_system, connectivity_config):
        # Mock platform.system to return 'Windows'
        mock_system.return_value = "Windows"

        # Create expected command
        expected_cmd = [
            "ping",
            "-n",
            "1",
            "-w",
            "1000",
            connectivity_config["server_ip"],
        ]

        # Mock successful ping
        mock_run.return_value = subprocess.CompletedProcess(
            args=expected_cmd, returncode=0, stdout=b"", stderr=b""
        )

        probe = IPPingProbe(connectivity_config)
        result = probe._execute_check()

        assert result is True
        mock_run.assert_called_once_with(
            expected_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    @patch("platform.system")
    @patch("subprocess.run")
    def test_ping_failure(self, mock_run, mock_system, connectivity_config):
        # Mock platform.system to return 'Windows'
        mock_system.return_value = "Windows"

        # Create expected command
        expected_cmd = [
            "ping",
            "-n",
            "1",
            "-w",
            "1000",
            connectivity_config["server_ip"],
        ]

        # Mock failed ping
        mock_run.return_value = subprocess.CompletedProcess(
            args=expected_cmd, returncode=1, stdout=b"", stderr=b""
        )

        probe = IPPingProbe(connectivity_config)
        result = probe._execute_check()

        assert result is False
        mock_run.assert_called_once_with(
            expected_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    @patch("platform.system")
    @patch("subprocess.run")
    def test_ping_error(self, mock_run, mock_system, connectivity_config):
        # Mock platform.system to return 'Windows'
        mock_system.return_value = "Windows"

        # Create expected command
        expected_cmd = [
            "ping",
            "-n",
            "1",
            "-w",
            "1000",
            connectivity_config["server_ip"],
        ]

        # Mock subprocess error
        mock_run.side_effect = subprocess.SubprocessError()

        probe = IPPingProbe(connectivity_config)
        result = probe._execute_check()

        assert result is False
        mock_run.assert_called_once_with(
            expected_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    def test_missing_config(self):
        with pytest.raises(ValueError):
            IPPingProbe({})


class BasePortProbeTest:
    """Abstract base class for port probe tests"""

    # This will be set by subclasses
    probe_class = None

    @pytest.fixture
    def mock_socket(self):
        with patch("socket.socket") as mock:
            yield mock

    def test_port_connection_success(self, mock_socket, connectivity_config):
        if not self.probe_class:
            pytest.skip("Abstract base class")

        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        probe = self.probe_class(connectivity_config)
        result = probe._execute_check()

        assert result is True
        mock_sock.connect.assert_called_once()
        mock_sock.close.assert_called_once()

    def test_port_connection_failure(self, mock_socket, connectivity_config):
        if not self.probe_class:
            pytest.skip("Abstract base class")

        mock_sock = Mock()
        mock_sock.connect.side_effect = socket.error()
        mock_socket.return_value = mock_sock

        probe = self.probe_class(connectivity_config)
        result = probe._execute_check()

        assert result is False
        mock_sock.connect.assert_called_once()
        mock_sock.close.assert_called_once()

    def test_missing_config(self):
        if not self.probe_class:
            pytest.skip("Abstract base class")

        with pytest.raises(ValueError):
            self.probe_class({})


class TestHTTPPortProbe(BasePortProbeTest):
    probe_class = HTTPPortProbe

    def test_correct_port_used(self, mock_socket, connectivity_config):
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        probe = self.probe_class(connectivity_config)
        probe._execute_check()

        mock_sock.connect.assert_called_once_with(
            (connectivity_config["server_hostname"], connectivity_config["http_port"])
        )


class TestHTTPSPortProbe(BasePortProbeTest):
    probe_class = HTTPSPortProbe

    def test_correct_port_used(self, mock_socket, connectivity_config):
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        probe = self.probe_class(connectivity_config)
        probe._execute_check()

        mock_sock.connect.assert_called_once_with(
            (connectivity_config["server_hostname"], connectivity_config["https_port"])
        )


class TestMailPortProbe(BasePortProbeTest):
    probe_class = MailPortProbe

    def test_correct_port_used(self, mock_socket, connectivity_config):
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        probe = self.probe_class(connectivity_config)
        probe._execute_check()

        mock_sock.connect.assert_called_once_with(
            (connectivity_config["server_hostname"], connectivity_config["mail_port"])
        )


class TestSMTPPortProbe(BasePortProbeTest):
    probe_class = SMTPPortProbe

    def test_correct_port_used(self, mock_socket, connectivity_config):
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        probe = self.probe_class(connectivity_config)
        probe._execute_check()

        mock_sock.connect.assert_called_once_with(
            (connectivity_config["server_hostname"], connectivity_config["smtp_port"])
        )
