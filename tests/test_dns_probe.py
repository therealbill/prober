import pytest
from unittest.mock import patch, Mock
import dns.resolver
from prober.probes.dns_probe import DNSMXDomainProbe, DNSMXIPProbe


@pytest.fixture
def dns_config():
    return {
        "collection_interval": 300,
        "mx_domain": "example.com",
        "expected_ip": "192.168.1.1",
    }


class TestDNSMXDomainProbe:
    @patch("dns.resolver.resolve")
    def test_mx_record_exists(self, mock_resolve, dns_config):
        # Mock MX record response
        mock_mx = Mock()
        mock_mx.exchange = dns.name.from_text("mail.example.com.")
        mock_resolve.return_value = [mock_mx]

        probe = DNSMXDomainProbe(dns_config)
        result = probe._execute_check()

        assert result is True
        mock_resolve.assert_called_once_with("example.com", "MX")

    @patch("dns.resolver.resolve")
    def test_mx_record_missing(self, mock_resolve, dns_config):
        # Simulate no MX records found
        mock_resolve.side_effect = dns.resolver.NXDOMAIN

        probe = DNSMXDomainProbe(dns_config)
        result = probe._execute_check()

        assert result is False
        mock_resolve.assert_called_once_with("example.com", "MX")

    @patch("dns.resolver.resolve")
    def test_dns_error(self, mock_resolve, dns_config):
        # Simulate DNS error
        mock_resolve.side_effect = dns.resolver.NoNameservers

        probe = DNSMXDomainProbe(dns_config)
        result = probe._execute_check()

        assert result is False
        mock_resolve.assert_called_once_with("example.com", "MX")


class TestDNSMXIPProbe:
    @patch("dns.resolver.resolve")
    def test_mx_ip_matches(self, mock_resolve, dns_config):
        # Mock MX and A record responses
        mock_mx = Mock()
        mock_mx.exchange = dns.name.from_text("mail.example.com.")
        mock_resolve.side_effect = [
            [mock_mx],  # MX query response
            ["192.168.1.1"],  # A query response
        ]

        probe = DNSMXIPProbe(dns_config)
        result = probe._execute_check()

        assert result is True
        assert mock_resolve.call_count == 2

    @patch("dns.resolver.resolve")
    def test_mx_ip_mismatch(self, mock_resolve, dns_config):
        # Mock MX and wrong A record responses
        mock_mx = Mock()
        mock_mx.exchange = dns.name.from_text("mail.example.com.")
        mock_resolve.side_effect = [
            [mock_mx],  # MX query response
            ["192.168.1.2"],  # Different IP
        ]

        probe = DNSMXIPProbe(dns_config)
        result = probe._execute_check()

        assert result is False
        assert mock_resolve.call_count == 2

    @patch("dns.resolver.resolve")
    def test_mx_record_missing(self, mock_resolve, dns_config):
        # Simulate no MX records
        mock_resolve.side_effect = dns.resolver.NXDOMAIN

        probe = DNSMXIPProbe(dns_config)
        result = probe._execute_check()

        assert result is False
        mock_resolve.assert_called_once_with("example.com", "MX")

    @patch("dns.resolver.resolve")
    def test_a_record_missing(self, mock_resolve, dns_config):
        # Mock MX record but missing A record
        mock_mx = Mock()
        mock_mx.exchange = dns.name.from_text("mail.example.com.")
        mock_resolve.side_effect = [
            [mock_mx],  # MX query response
            dns.resolver.NXDOMAIN,  # No A record
        ]

        probe = DNSMXIPProbe(dns_config)
        result = probe._execute_check()

        assert result is False
        assert mock_resolve.call_count == 2

    def test_missing_config_values(self):
        """Test that probes raise ValueError when required config is missing"""
        with pytest.raises(ValueError):
            DNSMXIPProbe(
                {"collection_interval": 300}
            )  # Missing mx_domain and expected_ip

        with pytest.raises(ValueError):
            DNSMXIPProbe(
                {"collection_interval": 300, "mx_domain": "example.com"}
            )  # Missing expected_ip

        with pytest.raises(ValueError):
            DNSMXDomainProbe({"collection_interval": 300})  # Missing mx_domain
