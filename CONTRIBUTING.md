# Contributing

Thanks for you interest in contributing to this project.

Main tools used in this repository:

| Tool                                             | Description                        |
| ------------------------------------------------ | ---------------------------------- |
| [astral/uv](https://github.com/astral-sh/uv)     | Python project and package manager |
| [jdx/mise](https://github.com/jdx/mise)          | Tool and task runner               |
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

Install [mise](https://mise.jdx.dev/installing-mise.html). All other project tools are declared in `mise.toml` and
installed automatically by mise.

### Install Project

```bash
mise run install
```

## Making Changes

1. Create a feature branch from `dev`.
2. Make your changes.
3. Test your changes by building and running the Docker image:
    ```bash
    mise run rebuild
    ```
    Use `--no-cache` or `--volumes` to select those options without the interactive prompts.
    Verify that Photon starts successfully and OpenSearch is up.
4. Run checks:
    ```bash
    mise run check
    mise run test
    ```
5. Commit and push to your fork.
6. Open a pull request to the upstream `dev` branch.

## Code Quality

- All code must pass checks run through `mise run check`.
- All changes must be tested with Docker.
- Avoid unnecessary comments in the code.

To list available tasks:

```bash
mise tasks ls
```

## Pull Requests

- Target the `dev` branch
- Provide a clear description of changes
- Ensure all checks pass before requesting review
