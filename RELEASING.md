# Releasing ApexAI

**CI** runs on every push / PR to `main`:
- Backend — `pytest` (in-memory SQLite, no services)
- Web — `eslint` + `next build`
- Client — `dotnet test` (telemetry parser)

## Cut a release + deploy

```bash
git tag v1.0.0
git push origin v1.0.0
```

The **Release & Deploy** workflow then:

1. Re-runs the full CI gate (no release ships untested code).
2. Builds `apexai.exe` — win-x64, self-contained, single file.
3. Creates a **GitHub Release** for the tag with **auto-generated notes** and
   `apexai-v1.0.0.exe` attached for download.
4. **Deploys**: rsyncs the repo to `/opt/apexai` on the server, then runs
   `infra/deploy.sh` to rebuild the stack and health-check it.

`deploy` and the release/exe build run in parallel once tests pass.

## Required GitHub Actions secrets

| Secret           | Value                                                          |
|------------------|----------------------------------------------------------------|
| `DEPLOY_SSH_KEY` | Private SSH key whose public half is in the server's `authorized_keys` |
| `DEPLOY_HOST`    | Server IP / hostname                                           |
| `DEPLOY_USER`    | SSH user (`root`)                                              |

Server prerequisites (one-time): Docker + compose installed, and
`/opt/apexai/.env` present (generated on the server, **never committed**).
