"""
DNS probe implementations for checking MX records and their IP addresses.
"""

import dns.resolver
from prober.probe import Probe
from loguru import logger


class DNSMXDomainProbe(Probe):
    """
    Probe that checks if MX records exist for a given domain.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.domain = config.get("mx_domain")
        if not self.domain:
            raise ValueError("mx_domain must be specified in config")

    def _execute_check(self) -> bool:
        """
        Check if MX records exist for the configured domain.

        Returns:
            bool: True if MX records exist, False otherwise
        """
        try:
            dns.resolver.resolve(self.domain, "MX")
            return True
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            logger.warning(f"No MX records found for domain {self.domain}")
            return False
        except dns.resolver.NoNameservers:
            logger.error(f"DNS resolution failed for domain {self.domain}")
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error checking MX records for {self.domain}: {str(e)}"
            )
            return False


class DNSMXIPProbe(Probe):
    """
    Probe that checks if MX record targets resolve to expected IP.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.domain = config.get("mx_domain")
        self.expected_ip = config.get("expected_ip")
        if not self.domain:
            raise ValueError("mx_domain must be specified in config")
        if not self.expected_ip:
            raise ValueError("expected_ip must be specified in config")

    def _execute_check(self) -> bool:
        """
        Check if any MX record target resolves to the expected IP.

        Returns:
            bool: True if any MX target resolves to expected IP, False otherwise
        """
        try:
            # Get MX records
            mx_records = dns.resolver.resolve(self.domain, "MX")

            # Check each MX record's IP
            for mx in mx_records:
                mx_hostname = str(mx.exchange).rstrip(".")
                try:
                    # Get A records for MX hostname
                    a_records = dns.resolver.resolve(mx_hostname, "A")

                    # Check if any IP matches expected
                    for rdata in a_records:
                        if str(rdata) == self.expected_ip:
                            logger.success(
                                f"Probe Success: DNS for {self.domain} matches {self.expected_ip}"
                            )
                            return True

                    logger.warning(
                        f"MX target {mx_hostname} does not resolve to expected IP {self.expected_ip}"
                    )
                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                    logger.warning(f"Could not resolve IP for MX target {mx_hostname}")
                    continue
                except Exception as e:
                    logger.error(
                        f"Error resolving IP for MX target {mx_hostname}: {str(e)}"
                    )
                    continue

            # No matching IP found in any MX target
            return False

        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            logger.warning(f"No MX records found for domain {self.domain}")
            return False
        except dns.resolver.NoNameservers:
            logger.error(f"DNS resolution failed for domain {self.domain}")
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error checking MX records for {self.domain}: {str(e)}"
            )
            return False
