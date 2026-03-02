# Security Policy

## What must NEVER be committed

| Item | Example | Why |
|------|---------|-----|
| `.env` | Portal credentials | Contains passwords |
| `auth_state/*.json` | Session cookies | Grants authenticated access |
| Real entity codes | Production entity / account IDs | Identifies live systems |
| Real URLs / hostnames | Internal portals, file shares | Reveals infrastructure |
| Downloaded reports | CSV / Excel files | May contain sensitive data |

## Before pushing

1. Run `git diff --cached` and review for secrets.
2. Confirm `.env` and `auth_state/` are listed in `.gitignore`.
3. Ensure `config.py` uses only placeholder values (e.g. `example-portal.invalid`).
4. Grep for real domain names, IP addresses, and internal hostnames.

## Reporting vulnerabilities

If you discover that real credentials or internal details have been committed,
open a private issue or contact the repository owner directly.
