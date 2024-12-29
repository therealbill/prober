# Email Server Prometheus Exporter

A Prometheus exporter that monitors email server health through various probes. The exporter checks DNS records, connectivity, security certificates, and SMTP functionality.

## Features

- DNS Probes:
  - MX record existence check
  - MX record IP resolution check (verifies MX records resolve to expected IP)
- Connectivity Probes:
  - ICMP ping check (OS-aware implementation for Windows/Unix)
  - HTTP port (80) connectivity
  - HTTPS port (443) connectivity
  - SMTP port (25) connectivity
  - Secure SMTP port (587) connectivity
- Security Probes:
  - HTTPS certificate validation (supports multiple TLS versions)
  - SMTP TLS certificate validation (supports both STARTTLS and implicit SSL)
  - Certificate hostname verification
  - Certificate chain validation
- Mail Functionality Probes:
  - Authenticated SMTP connection test (with STARTTLS)
  - Unauthenticated SMTP submission test
  - Comprehensive SMTP capability checking

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/prober.git
cd prober
```

2. Install dependencies using Poetry:
```bash
poetry install
```

## Configuration

Copy the example environment file and configure your settings:
```bash
cp .env.example .env
```

Edit `.env` with your email server details:

```env
# Email Server Configuration
EMAIL_SERVER_IP=192.168.1.1           # IP address of your email server
EMAIL_SERVER_HOSTNAME=mail.example.com # Hostname of your email server
EMAIL_MX_DOMAIN=example.com           # Domain to check MX records for
EXPECTED_IP=192.168.1.1               # Expected IP for MX record resolution

# Port Configuration
EMAIL_SERVER_HTTP_PORT=80             # HTTP port
EMAIL_SERVER_HTTPS_PORT=443           # HTTPS port
EMAIL_SERVER_SMTP_PORT=25             # SMTP port
EMAIL_SERVER_SMTP_SECURE_PORT=587     # Secure SMTP port

# SMTP Authentication
EMAIL_SMTP_USERNAME=user@example.com  # SMTP authentication username
EMAIL_SMTP_PASSWORD=your_password     # SMTP authentication password

# SMTP Test Configuration (Optional)
FROM_ADDRESS=test@example.com         # Test sender address
TO_ADDRESS=test@example.com           # Test recipient address

# Probe Configuration
PROBE_COLLECTION_INTERVAL=300         # How often to run probes (seconds)

# Prometheus Metrics
METRICS_EXPORT_PORT=9101              # Port to expose metrics on
```

## Usage

Start the exporter:
```bash
poetry run email-probe
```

The exporter will start running probes and expose metrics at `http://localhost:9101/metrics`.

### Available Metrics

- `email_probe_success_count`: Counter of probe successes and failures
  - Labels:
    - `success`: true|false
    - `probe`: The probe name (e.g., dns_mx_domain, https_certificate, etc.)

### Probe Details

#### DNS Probes
- `dns_mx_domain`: Checks if MX records exist for the configured domain
- `dns_mx_ip`: Verifies MX records resolve to the expected IP address, checking all MX targets

#### Connectivity Probes
- `ip_ping`: Tests if the server responds to ICMP ping (OS-aware implementation)
- `http_port`: Checks if port 80 is accessible with configurable timeout
- `https_port`: Checks if port 443 is accessible with configurable timeout
- `mail_port`: Checks if port 25 is accessible with configurable timeout
- `smtp_port`: Checks if port 587 is accessible with configurable timeout

#### Security Probes
- `https_certificate`: Validates the HTTPS certificate on port 443
  - Verifies certificate chain
  - Validates hostname
  - Supports multiple TLS versions (TLS 1.0, 1.1, 1.2)
- `smtp_certificate`: Validates the SMTP TLS certificate
  - Supports STARTTLS on port 587
  - Supports implicit SSL on other ports
  - Verifies certificate chain and hostname
  - Handles multiple TLS protocol versions

#### Mail Probes
- `smtp_authenticated`: Tests secure SMTP with authentication
  - Establishes connection with configurable timeout
  - Performs STARTTLS upgrade
  - Validates server capabilities
  - Tests authentication with provided credentials
- `smtp_unauthenticated`: Tests SMTP submission without authentication
  - Supports both port 25 and 587
  - Attempts STARTTLS when available
  - Tests basic mail submission capability
  - Handles various SMTP response scenarios

### Prometheus Configuration

Add the following to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'email_server'
    static_configs:
      - targets: ['localhost:9101']
```

## Development

Run tests:
```bash
poetry run pytest
```

Run tests with coverage:
```bash
poetry run pytest --cov=prober
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
