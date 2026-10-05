# URL Health Checker

A standard-library command-line tool for checking one absolute `http://` or `https://` URL.

```bash
python -m projects.url_health.app https://example.com
python -m projects.url_health.app https://example.com/health --timeout 3
```

It sends a `HEAD` request and retries with `GET` if the server responds `405` or `501`. A 2xx or 3xx result is reported as healthy; other HTTP statuses and network failures return a non-zero exit code. The timeout is per request and is limited to 0.1–60 seconds.

The checker does not follow a list of URLs, submit credentials, or run network requests in tests. Avoid passing URLs that contain secrets or private tokens; the tool rejects embedded username/password credentials.
