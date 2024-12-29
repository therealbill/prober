from prometheus_client import Gauge

# Counter for probe success/failure with labels for probe name and success
EMAIL_PROBE_SUCCESS = Gauge(
    'email_probe_success_count',
    'Count of probe execution successes and failures',
    ['probe']
)
