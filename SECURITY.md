# Security Policy

Software Lifecycle Env is a benchmark environment. It should never contain real credentials, private customer data, production logs, or proprietary code.

## Supported Versions

The `main` branch is the supported development branch.

## Reporting a Vulnerability

If you find a security issue, please report it privately by email:

```text
abhinavmusrifcs@gmail.com
```

Please include:

- affected file or endpoint
- reproduction steps
- expected impact
- whether the issue exposes hidden benchmark answers, secrets, or unsafe execution behavior

## Security Expectations

Contributions must not include:

- API keys or tokens
- real incident logs from private systems
- real customer or user data
- arbitrary shell execution in validators
- network calls inside deterministic task validation

