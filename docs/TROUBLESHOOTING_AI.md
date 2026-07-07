# AI Troubleshooting

Run:

```bash
cairos config ai doctor
cairos config ai status
cairos config ai test
```

CAIROS never prints raw API key values. It shows only the configured
environment variable name and whether it is visible.

## HTTP Errors

401 or 403:

```text
Key missing, invalid, expired, restricted, or not allowed for this model/endpoint.
```

Check the env var in the current shell, regenerate the key, and verify account,
org or project permissions.

Use helper commands to avoid mixing up the environment variable name and the
secret value:

```bash
cairos config ai key status OPENROUTER_API_KEY
cairos config ai key commands OPENROUTER_API_KEY --shell auto
```

Only use reveal when you intentionally want the value printed locally:

```bash
cairos config ai key reveal OPENROUTER_API_KEY
```

402:

```text
Payment required / insufficient credits.
```

For OpenRouter paid models, try:

```bash
cairos config ai use-openrouter-free
cairos config ai test
```

429:

```text
Rate limit, quota, billing, credits, or provider throttling.
```

Retry later, use a cheaper/free model, check usage/billing, or switch profiles.

404:

```text
Model or endpoint not found.
```

Check model slug and base endpoint. For Gemini, run
`cairos config ai list-models`.

Network errors usually mean connection, proxy, DNS, TLS, endpoint URL or
provider outage issues.

## Automatic Fallback

Run:

```bash
cairos config ai fallback status
cairos config ai profiles
```

When fallback is enabled, CAIROS tries saved profiles in this order:

1. active profile
2. profiles in `ai.fallback_order`
3. remaining profiles with sensible preference for free/local options

Recoverable categories include `rate_limit_quota`, `insufficient_credits`,
`temporary_provider`, `network`, `auth`, `model_unavailable`, and
`missing_key`. If all profiles fail, CAIROS prints a `Tried:` list with each
profile and the normalized category.

To keep fallback for one request only instead of switching the active profile,
set:

```bash
cairos config set ai.fallback_persist_switch false
```

## Windows Notes

`setx` and PowerShell persistent environment changes require a new terminal.
For the current terminal, use `set NAME=value` in cmd.exe or
`$env:NAME="value"` in PowerShell.
