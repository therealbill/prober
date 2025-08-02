from prometheus_client import Gauge

# Gauge for probe success/failure with labels for probe name and error type
EMAIL_PROBE_SUCCESS = Gauge(
    'email_probe_success_count',
    'Count of probe execution successes and failures',
    ['probe', 'error_type']
)
