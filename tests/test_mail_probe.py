import pytest
from unittest.mock import call, patch, Mock, MagicMock
import socket
import ssl
import smtplib
from prober.probes.mail_probe import AuthenticatedSMTPSendProbe, UnauthenticatedSMTPProbe


@pytest.fixture
def mail_config():
    return {
        "collection_interval": 300,
        "server_hostname": "mail.example.com",
        "smtp_port": 587,
        "smtp_username": "test@example.com",
        "smtp_password": "password123",
    }


@pytest.fixture
def unauth_mail_config():
    return {
        "collection_interval": 300,
        "server_hostname": "mail.example.com",
        "smtp_port": 25,  # Default to port 25 for testing
        "from_address": "test@example.com",
        "to_address": "recipient@example.com",
    }


class TestSMTPSendProbe:
    @patch("smtplib.SMTP")
    def test_smtp_connection_success(self, mock_smtp: Mock, mail_config):
        # Mock SMTP connection
        mock_conn = Mock()
        mock_smtp.return_value = mock_conn

        probe = AuthenticatedSMTPSendProbe(mail_config)
        result = probe._execute_check()

        assert result is True
        mock_smtp.assert_called_once_with(
            mail_config["server_hostname"], mail_config["smtp_port"], timeout=30
        )
        mock_conn.ehlo.assert_has_calls([call(), call()])  # Called before and after STARTTLS
        mock_conn.has_extn.assert_called_once_with('STARTTLS')
        mock_conn.starttls.assert_called_once()
        mock_conn.login.assert_called_once_with(
            mail_config["smtp_username"], mail_config["smtp_password"]
        )
        mock_conn.quit.assert_called_once()

    @patch("smtplib.SMTP")
    def test_smtp_connection_failure(self, mock_smtp, mail_config):
        mock_smtp.side_effect = socket.error()

        probe = AuthenticatedSMTPSendProbe(mail_config)
        result = probe._execute_check()

        assert result is False

    @patch("smtplib.SMTP")
    def test_smtp_no_starttls_support(self, mock_smtp, mail_config):
        # Mock SMTP connection but no STARTTLS support
        mock_conn = Mock()
        mock_smtp.return_value = mock_conn
        mock_conn.has_extn.return_value = False

        probe = AuthenticatedSMTPSendProbe(mail_config)
        result = probe._execute_check()

        assert result is False
        mock_conn.ehlo.assert_called_once()
        mock_conn.has_extn.assert_called_once_with('STARTTLS')
        mock_conn.starttls.assert_not_called()
        mock_conn.quit.assert_called_once()

    @patch("smtplib.SMTP")
    def test_smtp_starttls_failure(self, mock_smtp, mail_config):
        # Mock SMTP connection but fail on STARTTLS
        mock_conn = Mock()
        mock_smtp.return_value = mock_conn
        mock_conn.has_extn.return_value = True
        mock_conn.starttls.side_effect = smtplib.SMTPException()

        probe = AuthenticatedSMTPSendProbe(mail_config)
        result = probe._execute_check()

        assert result is False
        mock_conn.ehlo.assert_called_once()
        mock_conn.has_extn.assert_called_once_with('STARTTLS')
        mock_conn.starttls.assert_called_once()
        mock_conn.quit.assert_called_once()

    @patch("smtplib.SMTP")
    def test_smtp_auth_failure(self, mock_smtp, mail_config):
        # Mock SMTP connection but fail on login
        mock_conn = Mock()
        mock_smtp.return_value = mock_conn
        mock_conn.has_extn.return_value = True
        mock_conn.login.side_effect = smtplib.SMTPAuthenticationError(
            535, b"Authentication failed"
        )

        probe = AuthenticatedSMTPSendProbe(mail_config)
        result = probe._execute_check()

        assert result is False
        mock_conn.ehlo.assert_has_calls([call(),call()])
        mock_conn.has_extn.assert_called_once_with('STARTTLS')
        mock_conn.starttls.assert_called_once()
        mock_conn.quit.assert_called_once()

    @patch("smtplib.SMTP")
    def test_smtp_general_auth_error(self, mock_smtp, mail_config):
        # Test general SMTP authentication error
        mock_conn = Mock()
        mock_smtp.return_value = mock_conn
        mock_conn.has_extn.return_value = True
        mock_conn.login.side_effect = smtplib.SMTPException("General auth error")

        probe = AuthenticatedSMTPSendProbe(mail_config)
        result = probe._execute_check()

        assert result is False
        mock_conn.ehlo.assert_has_calls([call(),call()])
        mock_conn.has_extn.assert_called_once_with('STARTTLS')
        mock_conn.starttls.assert_called_once()
        mock_conn.quit.assert_called_once()

    def test_missing_config(self):
        with pytest.raises(ValueError):
            AuthenticatedSMTPSendProbe({})

        with pytest.raises(ValueError):
            AuthenticatedSMTPSendProbe({"server_hostname": "mail.example.com", "smtp_port": 587})

        with pytest.raises(ValueError):
            AuthenticatedSMTPSendProbe(
                {
                    "server_hostname": "mail.example.com",
                    "smtp_port": 587,
                    "smtp_username": "test@example.com",
                }
            )


class TestUnauthenticatedSMTPProbe:
    @patch("smtplib.SMTP")
    def test_smtp_port25_success(self, mock_smtp, unauth_mail_config):
        # Mock SMTP connection
        mock_conn = Mock()
        mock_smtp.return_value = mock_conn

        probe = UnauthenticatedSMTPProbe(unauth_mail_config)
        result = probe._execute_check()

        assert result is True
        mock_smtp.assert_called_once_with(
            unauth_mail_config["server_hostname"],
            unauth_mail_config["smtp_port"],
            timeout=30,
        )
        # Should not attempt STARTTLS on port 25
        mock_conn.starttls.assert_not_called()
        mock_conn.sendmail.assert_called_once()
        mock_conn.quit.assert_called_once()

    @patch("smtplib.SMTP")
    def test_smtp_port587_success(self, mock_smtp, unauth_mail_config):
        # Test port 587 which should attempt STARTTLS
        unauth_mail_config["smtp_port"] = 587
        mock_conn = Mock()
        mock_smtp.return_value = mock_conn

        probe = UnauthenticatedSMTPProbe(unauth_mail_config)
        result = probe._execute_check()

        assert result is True
        mock_smtp.assert_called_once_with(
            unauth_mail_config["server_hostname"], 587, timeout=30
        )
        mock_conn.starttls.assert_called_once()
        mock_conn.sendmail.assert_called_once()
        mock_conn.quit.assert_called_once()

    @patch("smtplib.SMTP")
    def test_smtp_starttls_failure_continues(self, mock_smtp, unauth_mail_config):
        # Test that probe continues even if STARTTLS fails on port 587
        unauth_mail_config["smtp_port"] = 587
        mock_conn = Mock()
        mock_smtp.return_value = mock_conn
        mock_conn.starttls.side_effect = smtplib.SMTPException()

        probe = UnauthenticatedSMTPProbe(unauth_mail_config)
        result = probe._execute_check()

        assert result is True  # Should still succeed as STARTTLS is optional
        mock_conn.starttls.assert_called_once()
        mock_conn.sendmail.assert_called_once()
        mock_conn.quit.assert_called_once()

    @patch("smtplib.SMTP")
    def test_smtp_recipients_refused_success(self, mock_smtp, unauth_mail_config):
        # Test that probe considers it success even if recipients are refused
        mock_conn = Mock()
        mock_smtp.return_value = mock_conn
        mock_conn.sendmail.side_effect = smtplib.SMTPRecipientsRefused({})

        probe = UnauthenticatedSMTPProbe(unauth_mail_config)
        result = probe._execute_check()

        assert result is True  # Should succeed as we're testing submission capability
        mock_conn.sendmail.assert_called_once()
        mock_conn.quit.assert_called_once()

    @patch("smtplib.SMTP")
    def test_smtp_connection_failure(self, mock_smtp, unauth_mail_config):
        mock_smtp.side_effect = socket.error()

        probe = UnauthenticatedSMTPProbe(unauth_mail_config)
        result = probe._execute_check()

        assert result is False

    @patch("smtplib.SMTP")
    def test_smtp_send_failure(self, mock_smtp, unauth_mail_config):
        # Test failure on sendmail (other than recipients refused)
        mock_conn = Mock()
        mock_smtp.return_value = mock_conn
        mock_conn.sendmail.side_effect = smtplib.SMTPException()

        probe = UnauthenticatedSMTPProbe(unauth_mail_config)
        result = probe._execute_check()

        assert result is False
        mock_conn.sendmail.assert_called_once()
        mock_conn.quit.assert_called_once()

    def test_missing_config(self):
        with pytest.raises(ValueError):
            UnauthenticatedSMTPProbe({})

        with pytest.raises(ValueError):
            UnauthenticatedSMTPProbe({"server_hostname": "mail.example.com"})

        # Should not raise error if only required fields are present
        probe = UnauthenticatedSMTPProbe(
            {"server_hostname": "mail.example.com", "smtp_port": 25}
        )
        assert probe.from_address == "test@example.com"  # Should use default
        assert probe.to_address == "test@example.com"  # Should use default
