# Contributing

## Development Setup

### MacOS/Linux

```bash
brew bundle
```

### Windows

- install [Task](https://taskfile.dev/docs/installation#official-package-managers)
- install [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Install Project

```bash
# installs python project with uv with dev dependencies and hooks
task install
```

## Making Changes

1. Create a feature branch from `dev`
2. Make your changes
3. Run quality checks:
    ```bash
    task check
    ```
4. Test your changes by building and running the Docker image:
    ```bash
    task rebuild
    ```
    Verify that Photon starts successfully and OpenSearch is up.
5. Commit and push to your fork
6. Open a pull request to the upstream `dev` branch

## Code Quality

- All code must pass checks done through `task check`
- All changes must be tested with Docker
- Avoid unnecessary comments.

To list available tasks:

```bash
task
```

## Pull Requests

- Target the `dev` branch
- Provide a clear description of changes
- Ensure all checks pass before requesting review

---

## AI Policy

Do not use AI to create, generate or draft any direct communication such as Issues, Comments, PR Bodies, etc.

You MUST fully understand and be able to explain what your changes do and how they interact with the codebase.
