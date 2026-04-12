# Contributing to immich-gpt

Thanks for contributing to `immich-gpt`.

## Before you start

- read the project [`README.md`](README.md)
- use [`docs/development.md`](docs/development.md) for local setup
- check [`docs/architecture.md`](docs/architecture.md) if you need system context

## Development basics

### Backend

```bash
cd backend
python3 -m pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm test
npm run lint
npx tsc --noEmit
```

### Production frontend build

```bash
cd frontend
npx vite build
```

## Contribution guidelines

- keep changes focused and scoped to the problem being solved
- prefer updating or adding documentation when behavior changes
- keep user-facing wording clear and accurate
- add or update tests when the change meaningfully affects behavior
- do not mix unrelated refactors into a feature or bug-fix change

## Pull requests

Good pull requests usually include:

- a short description of the problem
- a concise summary of the change
- testing notes with the commands you ran
- screenshots or demo evidence for non-trivial UI changes

## Documentation updates

If you change deployment, configuration, workflow, or behavior:

- update [`README.md`](README.md) when the top-level story changes
- update the relevant guide in [`docs/`](docs/README.md)
- update [`DOCKER.md`](DOCKER.md) or [`docs/reverse-proxy.md`](docs/reverse-proxy.md) when operational steps change

## Questions

If you are not sure where a change belongs, open an issue or draft PR with your proposed direction.
