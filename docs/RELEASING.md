# Releasing pathetic-cli

This document covers how to publish a new release to PyPI and GitHub.

## Prerequisites

### One-time: Configure PyPI Trusted Publisher

The release workflow uses [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/) (OIDC) instead of API tokens. This is the recommended approach — no secrets to manage or rotate.

1. Go to <https://pypi.org/manage/project/pathetic-cli/settings/publishing/>
2. Click **Add a new publisher**
3. Fill in:
   - **Owner**: `lancereinsmith`
   - **Repository name**: `pathetic`
   - **Workflow name**: `release.yml`
   - **Environment name**: `pypi`
4. Click **Add**

### One-time: Create GitHub Environment

1. Go to your repo **Settings > Environments**
2. Create an environment named `pypi`
3. Optionally add protection rules (e.g., require approval before publishing)

## How to Release

### Option A: Tag push (recommended)

1. Update the version in `pyproject.toml`:

   ```toml
   version = "0.4.0"
   ```

2. Commit and tag:

   ```bash
   git add pyproject.toml
   git commit -m "Release v0.4.0"
   git tag v0.4.0
   git push origin main --tags
   ```

3. The release workflow runs automatically:
   - Runs the test suite
   - Builds the package with `uv build`
   - Creates a GitHub Release with auto-generated release notes
   - Publishes to PyPI via Trusted Publishers

### Option B: Manual dispatch

1. Go to **Actions > Release > Run workflow**
2. Enter the version (e.g., `v0.4.0`)
3. Click **Run workflow**

This is useful for re-running a failed release or publishing without a tag push.

## What the Workflow Does

The release workflow (`.github/workflows/release.yml`) has three jobs:

| Job | What it does |
|-----|-------------|
| **build** | Installs deps, runs tests, builds the sdist + wheel, uploads as artifact |
| **github-release** | Downloads the artifact, creates a GitHub Release with auto-generated notes |
| **pypi-publish** | Downloads the artifact, publishes to PyPI via OIDC (no token needed) |

The `github-release` and `pypi-publish` jobs run in parallel after `build` succeeds.

## Verifying a Release

After the workflow completes:

```bash
# Check PyPI
uv pip install pathetic-cli==0.4.0

# Or upgrade an existing install
uv tool upgrade pathetic-cli

# Verify
ptc --version
```

## Troubleshooting

### "Trusted publisher not configured"

The PyPI Trusted Publisher must be set up before the first release. See the prerequisites above. Make sure the **workflow name** is exactly `release.yml` and the **environment name** is exactly `pypi`.

### "Environment 'pypi' not found"

Create the `pypi` environment in your repo's Settings > Environments.

### Build fails

The workflow runs `uv run pytest` before building. Check the test output in the Actions log. Fix any failures and re-tag or re-run the workflow.
