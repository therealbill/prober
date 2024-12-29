"""
Security probe implementations for checking SSL/TLS certificates.
"""

import socket
import ssl
from prober.probe import Probe
from loguru import logger


class CertificateProbe(Probe):
    """
    Base class for probes that check SSL/TLS certificates.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.server_hostname = config.get("server_hostname")
        if not self.server_hostname:
            raise ValueError("server_hostname must be specified in config")
        self.port = self._get_port_from_config(config)

    def _get_port_from_config(self, config: dict) -> int:
        """
        Get the port number from config. Must be implemented by subclasses.

        Args:
            config (dict): Configuration dictionary

        Returns:
            int: Port number to check
        """
        raise NotImplementedError("Subclasses must implement _get_port_from_config")

    def _verify_certificate(self, ssl_sock: ssl.SSLSocket) -> bool:
        """
        Verify the certificate from the SSL socket.

        Args:
            ssl_sock: The SSL socket with an established connection

        Returns:
            bool: True if certificate is valid for the hostname, False otherwise
        """
        try:
            cert = ssl_sock.getpeercert()

            # Check if the certificate exists
            if not cert:
                logger.warning("No certificate provided by server")
                return False

            # Check the hostname in the certificate
            for field in cert.get("subject", []):
                for key, value in field:
                    if key == "commonName" and value == self.server_hostname:
                        logger.success(
                            f"Probe Success: Certificate Validation on {self.server_hostname}:{self.port}."
                        )
                        return True

            logger.warning(
                f"Certificate hostname mismatch. Expected {self.server_hostname}"
            )
            return False

        except Exception as e:
            logger.error(f"Error verifying certificate: {str(e)}")
            return False

    def _create_ssl_context(self, protocol) -> ssl.SSLContext:
        """
        Create an SSL context with appropriate protocol and cipher settings.

        Returns:
            ssl.SSLContext: Configured SSL context
        """

        context = ssl.SSLContext(protocol)
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True
        context.load_default_certs()
        return context

    def _check_starttls_certificate(self) -> bool:
        """
        Check certificate using STARTTLS upgrade.
        Used for ports that require explicit TLS upgrade like 587.

        Returns:
            bool: True if certificate is valid, False otherwise
        """
        import smtplib
        smtp = None
        try:
            # Create SMTP connection
            smtp = smtplib.SMTP(self.server_hostname, self.port, timeout=10)
            
            # Upgrade to TLS
            smtp.starttls()
            
            # Get the SSL socket after STARTTLS upgrade
            if not smtp.sock:
                logger.warning("No SSL socket after STARTTLS")
                return False
                
            return self._verify_certificate(smtp.sock)

        except smtplib.SMTPException as e:
            logger.warning(f"STARTTLS failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error checking STARTTLS certificate: {str(e)}")
            return False
        finally:
            if smtp:
                try:
                    smtp.quit()
                except:
                    pass

    def _check_implicit_ssl_certificate(self) -> bool:
        """
        Check certificate using implicit SSL/TLS connection.
        Used for ports that use SSL/TLS from the start like 465.

        Returns:
            bool: True if certificate is valid, False otherwise
        """
        tls_versions = [
            ssl.PROTOCOL_TLS,  # Negotiate highest protocol version
            ssl.PROTOCOL_TLSv1_2,
            ssl.PROTOCOL_TLSv1_1,
            ssl.PROTOCOL_TLSv1,
        ]

        sock = None
        try:
            # Create a socket and connect
            sock = socket.create_connection(
                (self.server_hostname, self.port), timeout=5
            )

            # Create SSL context with certificate verification
            for tls in tls_versions:
                try:
                    # Wrap the socket with SSL
                    context = self._create_ssl_context(tls)
                    with context.wrap_socket(
                        sock, server_hostname=self.server_hostname
                    ) as ssl_sock:
                        return self._verify_certificate(ssl_sock)
                except ssl.SSLError:
                    continue
            raise ssl.SSLError("All TLS versions failed")

        except ssl.SSLCertVerificationError as e:
            logger.warning(f"Certificate verification failed: {str(e)}")
            return False
        except socket.error as e:
            logger.warning(f"Connection failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking certificate: {str(e)}")
            return False
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass

    def _execute_check(self) -> bool:
        """
        Check if the server has a valid SSL/TLS certificate.
        Uses appropriate method based on port number.

        Returns:
            bool: True if certificate is valid, False otherwise
        """
        # Port 587 requires STARTTLS
        if self.port == 587:
            return self._check_starttls_certificate()
        # Other ports like 465 use implicit SSL
        else:
            return self._check_implicit_ssl_certificate()


class HTTPSCertificateProbe(CertificateProbe):
    """Probe that checks HTTPS certificate validity."""

    def _get_port_from_config(self, config: dict) -> int:
        port = config.get("https_port")
        if not port:
            raise ValueError("https_port must be specified in config")
        return port


class SMTPCertificateProbe(CertificateProbe):
    """Probe that checks SMTP certificate validity."""

    def _get_port_from_config(self, config: dict) -> int:
        port = config.get("smtp_port")
        if not port:
            raise ValueError("smtp_port must be specified in config")
        return port
