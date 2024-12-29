"""
Mail probe implementations for checking SMTP functionality.
"""

import socket
import smtplib
from prober.probe import Probe
from loguru import logger


class AuthenticatedSMTPSendProbe(Probe):
    """
    Probe that checks if secure SMTP connection and authentication works.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.server_hostname = config.get("server_hostname")
        self.smtp_port = config.get("smtp_port")
        self.username = config.get("smtp_username")
        self.password = config.get("smtp_password")

        if not self.server_hostname:
            raise ValueError("server_hostname must be specified in config")
        if not self.smtp_port:
            raise ValueError("smtp_port must be specified in config")
        if not self.username:
            raise ValueError("smtp_username must be specified in config")
        if not self.password:
            raise ValueError("smtp_password must be specified in config")

    def _execute_check(self) -> bool:
        """
        Check if SMTP connection, TLS upgrade, and authentication work.
        Handles various SMTP authentication scenarios and provides detailed logging.

        Returns:
            bool: True if all SMTP operations succeed, False otherwise
        """
        smtp = None
        try:
            # Create SMTP connection with configurable timeout
            smtp = smtplib.SMTP(self.server_hostname, self.smtp_port, timeout=30)
            
            # Send EHLO first (best practice)
            smtp.ehlo()
            
            # Get server capabilities
            if not smtp.has_extn('STARTTLS'):
                logger.warning(f"Server does not support STARTTLS: {self.server_hostname}")
                return False

            # Upgrade to TLS
            try:
                smtp.starttls()
                smtp.ehlo()  # Send EHLO again after STARTTLS
            except smtplib.SMTPException as e:
                logger.error(f"STARTTLS failed: {self.server_hostname} - {str(e)}")
                return False

            # Authenticate with detailed error handling
            try:
                smtp.login(self.username, self.password)
            except smtplib.SMTPAuthenticationError as e:
                logger.error(
                    f"Authentication failed for user {self.username}: {str(e)}\n"
                    f"Server: {self.server_hostname}, Port: {self.smtp_port}"
                )
                return False
            except smtplib.SMTPException as e:
                logger.error(
                    f"SMTP Authentication error: {str(e)}\n"
                    f"Server: {self.server_hostname}, Port: {self.smtp_port}"
                )
                return False

            logger.success(
                f"Probe Success: Mail probe authenticated successfully for server: {self.server_hostname}"
            )
            return True

        except socket.error as e:
            logger.warning(
                f"Failed to connect to SMTP server: {self.server_hostname}:{self.smtp_port} - {str(e)}"
            )
            return False
        except smtplib.SMTPException as e:
            logger.warning(
                f"SMTP operation failed: {self.server_hostname}:{self.smtp_port} - {str(e)}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error in SMTP check: {self.server_hostname}:{self.smtp_port} - {str(e)}"
            )
            return False
        finally:
            if smtp:
                try:
                    smtp.quit()
                except:
                    pass


class UnauthenticatedSMTPProbe(Probe):
    """
    Probe that checks if unauthenticated SMTP submission works.
    Tests both plain SMTP (port 25) and SMTP Submit (port 587) without authentication.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.server_hostname = config.get("server_hostname")
        self.port = config.get("smtp_port")
        self.from_address = config.get("from_address", "test@example.com")
        self.to_address = config.get("to_address", "test@example.com")

        if not self.server_hostname:
            raise ValueError("server_hostname must be specified in config")
        if not self.port:
            raise ValueError("smtp_port must be specified in config")

    def _execute_check(self) -> bool:
        """
        Check if unauthenticated SMTP submission works.
        For port 587, attempts STARTTLS but proceeds without authentication.
        For port 25, attempts direct submission.

        Returns:
            bool: True if SMTP connection and submission attempt succeed, False otherwise
        """
        smtp = None
        try:
            # Create SMTP connection with configurable timeout
            smtp = smtplib.SMTP(self.server_hostname, self.port, timeout=30)

            # For port 587, attempt STARTTLS but don't authenticate
            if self.port == 587:
                try:
                    smtp.starttls()
                except smtplib.SMTPException as e:
                    logger.warning(f"STARTTLS failed but continuing: {str(e)}")

            # Attempt to send a test message
            message = f"From: {self.from_address}\r\nTo: {self.to_address}\r\nSubject: SMTP Test\r\n\r\nThis is a test message."
            try:
                smtp.sendmail(self.from_address, [self.to_address], message)
                logger.success(
                    f"Probe Success: Unauthenticated mail submission succeeded on port {self.port}"
                )
                return True
            except smtplib.SMTPRecipientsRefused:
                # Consider this a "success" as we're testing submission capability
                # not whether the server accepts the specific addresses
                logger.success(
                    f"Probe Success: Mail submission attempted but rejected on port {self.port}"
                )
                return True
            except smtplib.SMTPSenderRefused:
                logger.success(
                    f"Probe Success: Attempted mail submission authentication failed on port {self.port}"
                )
                return True
        except socket.error as e:
            logger.warning(
                f"Failed to connect to SMTP server on port {self.port}: {str(e)}"
            )
            return False
        except smtplib.SMTPException as e:
            logger.warning(f"SMTP operation failed on port {self.port}: {str(e)}")
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error in SMTP check on port {self.port}: {str(e)}"
            )
            return False
        finally:
            if smtp:
                try:
                    smtp.quit()
                except:
                    pass
