# Contributing

## Development Setup

Fork this repository and clone your fork:

Install dependencies:

```bash
uv sync --locked
```

List available local tasks:

```bash
task --list
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

- All code must pass linting, type checking, and dead code analysis
- All changes must be tested with Docker
- Avoid unnecessary comments

## Pull Requests

- Target the `dev` branch
- Provide a clear description of changes
- Ensure all checks pass before requesting review

---

## AI Policy

Do not use AI to create, generate or draft any direct communication such as Issues, Comments, PR Bodies, etc.

You MUST fully understand and be able to explain what your changes do and how they interact with the codebase.
