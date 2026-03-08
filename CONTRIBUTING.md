# Contributing

Thanks for you interest in contributing to this project.

Main tools used in this repository:

| Tool                                             | Description                        |
| ------------------------------------------------ | ---------------------------------- |
| [astral/uv](https://github.com/astral-sh/uv)     | Python project and package manager |
| [go-task/task](https://github.com/go-task/task)  | Task Runner                        |
| [j178/prek](https://github.com/j178/prek)        | pre-commit hook runner             |
| [astral/ruff](https://github.com/astral-sh/ruff) | Formatting/Linting/LSP             |
| [astral/ty](https://github.com/astral-sh/ty)     | Type Checking                      |

## AI Policy

Do NOT use AI to create, generate or draft any direct communication such as Issues, Comments, PR Bodies, etc.

You MUST fully understand and be able to explain what your changes do and how they interact with the codebase.

## Development Setup

Clone the repository:

```bash
git clone https://github.com/rtuszik/photon-docker
cd photon-docker
```

#### Dependencies

The Brewfile can be used in order to install `Task` and `uv` with `Homebrew` on MacOS and Linux

```bash
brew bundle
```

On Windows or for other install methods, refer to the official documentation:

- install [Task](https://taskfile.dev/docs/installation)
- install [uv](https://docs.astral.sh/uv/getting-started/installation)

### Install Project

```bash
# installs python project with uv with dev dependencies and hooks
task install
```

## Making Changes

1. Create a feature branch from `dev`.
2. Make your changes.
3. Test your changes by building and running the Docker image:
    ```bash
    task rebuild
    ```
    Verify that Photon starts successfully and OpenSearch is up.
4. Run checks:
    ```bash
    task check
    task test
    ```
5. Commit and push to your fork.
6. Open a pull request to the upstream `dev` branch.

## Code Quality

- All code must pass checks done through `task check`.
- All changes must be tested with Docker.
- Avoid unnecessary comments in the code.

To list available tasks:

```bash
task
```

## Pull Requests

- Target the `dev` branch
- Provide a clear description of changes
- Ensure all checks pass before requesting review
