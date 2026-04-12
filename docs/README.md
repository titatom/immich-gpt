# immich-gpt documentation

This directory holds the detailed guides that sit behind the main project README.

## Start here

- New user: [`getting-started.md`](getting-started.md)
- Docker or Unraid deployer: [`../DOCKER.md`](../DOCKER.md)
- Reverse proxy or HTTPS setup: [`reverse-proxy.md`](reverse-proxy.md)
- Environment variables and runtime behavior: [`configuration.md`](configuration.md)
- Curious about internals: [`architecture.md`](architecture.md)
- Contributor or local developer: [`development.md`](development.md)
- Need help diagnosing a problem: [`troubleshooting.md`](troubleshooting.md)

## Recommended reading paths

### For first-time self-hosters

1. Read the project [`README.md`](../README.md)
2. Follow [`getting-started.md`](getting-started.md)
3. Use [`../DOCKER.md`](../DOCKER.md) for the deployment path you want
4. Read [`reverse-proxy.md`](reverse-proxy.md) if you are exposing the app over HTTPS
5. Keep [`troubleshooting.md`](troubleshooting.md) nearby for common issues

### For existing Immich users evaluating the app

Read these sections in order:

1. Project [`README.md`](../README.md)
2. [`getting-started.md`](getting-started.md)
3. [`configuration.md`](configuration.md)
4. [`architecture.md`](architecture.md)

### For contributors

1. [`development.md`](development.md)
2. [`architecture.md`](architecture.md)
3. project [`README.md`](../README.md)

## Documentation structure

| File | Purpose |
|------|---------|
| `getting-started.md` | Install, first login, first workflow |
| `configuration.md` | Full configuration reference and precedence rules |
| `architecture.md` | System design, jobs, storage, write-back flow |
| `development.md` | Local run commands, tests, builds, migrations |
| `troubleshooting.md` | Common deployment and runtime problems |
| `reverse-proxy.md` | Proxy, HTTPS, SSE, and forwarded header guidance |

If a guide feels incomplete or inaccurate, please open an issue or send a pull request.
