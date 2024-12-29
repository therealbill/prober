import pytest
from unittest.mock import patch, Mock, MagicMock
import ssl
import socket
from prober.probes.security_probe import (
    HTTPSCertificateProbe,
    SMTPCertificateProbe,
)


@pytest.fixture
def security_config():
    return {
        "collection_interval": 300,
        "server_hostname": "mail.example.com",
        "https_port": 443,
        "smtp_port": 587,
    }


class TestHTTPSCertificateProbe:
    @patch("prober.probes.security_probe.CertificateProbe._create_ssl_context")
    @patch("socket.create_connection")
    def test_valid_certificate(self, mock_socket, mock_ssl_context, security_config):
        # Mock socket connection
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        # Mock SSL context and wrapped socket
        mock_context = Mock()
        mock_ssl_context.return_value = mock_context
        mock_ssl_sock = MagicMock()
        mock_context.wrap_socket.return_value = mock_ssl_sock

        # Create the mock certificate data
        cert_data = {
            "subject": ((("commonName", "mail.example.com"),),)
        }
        
        # Set up the mock chain properly
        mock_ssl_sock.getpeercert.return_value = cert_data
        mock_ssl_sock.__enter__.return_value = mock_ssl_sock
        mock_ssl_sock.getpeercert = Mock(return_value=cert_data)
        mock_ssl_sock.__exit__.return_value = None

        probe = HTTPSCertificateProbe(security_config)
        result = probe._execute_check()

        assert result is True
        mock_socket.assert_called_once_with(
            (security_config["server_hostname"], security_config["https_port"]),
            timeout=5,
        )
        mock_context.wrap_socket.assert_called_once_with(
            mock_sock, server_hostname=security_config["server_hostname"]
        )

    @patch("ssl.create_default_context")
    @patch("socket.create_connection")
    def test_certificate_verification_failed(
        self, mock_socket, mock_ssl_context, security_config
    ):
        # Mock socket connection
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        # Mock SSL context and error
        mock_context = Mock()
        mock_ssl_context.return_value = mock_context
        mock_context.wrap_socket.side_effect = ssl.SSLCertVerificationError()

        probe = HTTPSCertificateProbe(security_config)
        result = probe._execute_check()

        assert result is False

    @patch("ssl.create_default_context")
    @patch("socket.create_connection")
    def test_connection_error(self, mock_socket, mock_ssl_context, security_config):
        mock_socket.side_effect = socket.error()

        probe = HTTPSCertificateProbe(security_config)
        result = probe._execute_check()

        assert result is False

    def test_missing_config(self):
        with pytest.raises(ValueError):
            HTTPSCertificateProbe({})


class TestSMTPCertificateProbe:
    @patch("prober.probes.security_probe.CertificateProbe._create_ssl_context")
    @patch("socket.create_connection")
    @patch("smtplib.SMTP")
    def test_valid_certificate(self, mock_socket, mock_ssl_context, security_config):
        # Mock socket connection
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        # Mock SSL context and wrapped socket
        mock_context = Mock()
        mock_ssl_context.return_value = mock_context
        mock_ssl_sock = MagicMock()
        mock_context.wrap_socket.return_value = mock_ssl_sock

        # Mock certificate verification
        mock_ssl_sock.getpeercert.return_value = {
            "subject": ((("commonName", "mail.example.com"),),)
        }

        # Mock context manager
        mock_ssl_sock.__enter__.return_value = mock_ssl_sock
        mock_ssl_sock.__exit__.return_value = None

        probe = SMTPCertificateProbe(security_config)
        result = probe._execute_check()

        assert result is True
        mock_socket.assert_called_once_with(
            (security_config["server_hostname"], security_config["smtp_port"]),
            timeout=5,
        )
        mock_context.wrap_socket.assert_called_once_with(
            mock_sock, server_hostname=security_config["server_hostname"]
        )

    @patch("ssl.create_default_context")
    @patch("socket.create_connection")
    def test_certificate_verification_failed(
        self, mock_socket, mock_ssl_context, security_config
    ):
        # Mock socket connection
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        # Mock SSL context and error
        mock_context = Mock()
        mock_ssl_context.return_value = mock_context
        mock_context.wrap_socket.side_effect = ssl.SSLCertVerificationError()

        probe = SMTPCertificateProbe(security_config)
        result = probe._execute_check()

        assert result is False

    @patch("ssl.create_default_context")
    @patch("socket.create_connection")
    def test_connection_error(self, mock_socket, mock_ssl_context, security_config):
        mock_socket.side_effect = socket.error()

        probe = SMTPCertificateProbe(security_config)
        result = probe._execute_check()

        assert result is False

    def test_missing_config(self):
        with pytest.raises(ValueError):
            SMTPCertificateProbe({})
