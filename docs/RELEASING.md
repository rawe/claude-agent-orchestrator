# Release Guide

This document describes the release process for the Agent Orchestration Framework (AOF) container images.

## Overview

AOF uses an **overarching version** strategy: all container images share the same release version, ensuring they are compatible and work together.

| Image | Description |
|-------|-------------|
| `ghcr.io/rawe/aof-coordinator` | Session management and agent registry |
| `ghcr.io/rawe/aof-runner-claude-code` | Agent execution with Claude Code |
| `ghcr.io/rawe/aof-runner-procedural` | Agent execution with procedural executor |
| `ghcr.io/rawe/aof-dashboard` | Web UI for management and monitoring |
| `ghcr.io/rawe/aof-context-store` | Document management and synchronization |

When you release version `1.0.0`, all images are tagged as `1.0.0` and are guaranteed to be compatible.

### Component Versions

Each component also has its own internal version (tracked in `pyproject.toml` or `package.json`). These are embedded as Docker labels but do not affect the image tag. This allows tracking internal changes while maintaining a simple, unified release version.

| Component | Version Location |
|-----------|------------------|
| Coordinator | `servers/agent-coordinator/pyproject.toml` |
| Runner | Defined in `Makefile` (RUNNER_VERSION) |
| Dashboard | `apps/dashboard/package.json` |
| Context Store | `servers/context-store/pyproject.toml` |

## Multi-Architecture Images

All release images are built for **linux/amd64** and **linux/arm64**. Docker automatically pulls the correct architecture — an Apple Silicon Mac gets arm64, an x86 server gets amd64.

- CI builds use QEMU emulation for arm64 on x86 GitHub Actions runners
- Local builds (`make release VERSION=x.y.z` without `PUSH=true`) build for the host architecture only

## Build Cache Strategy

CI builds use a **registry-based BuildKit cache** to avoid rebuilding dependency layers on every release. Each image has a `:buildcache` tag in GHCR that stores cached layers for both architectures.

| Tag | Purpose |
|-----|---------|
| `0.7.0` | Versioned release image (amd64 + arm64 manifest) |
| `latest` | Most recent release |
| `buildcache` | Cache-only image used by BuildKit (not runnable) |

Cache uses `mode=max` to cache ALL layers including intermediate build stages. This is critical for multi-stage Dockerfiles (dashboard, runners) where expensive dependency layers (`npm ci`, `apt-get`, Claude CLI install) are in non-final stages.

The first CI build after this change will be slow (no cache exists). Subsequent builds reuse cached dependency layers and only rebuild changed source code layers.

## Prerequisites

### For Local Builds

- Docker with buildx (included in modern Docker Desktop)
- No registry authentication needed for local builds

### For Pushing to Registry (local or CI)

- Authenticated with `docker login ghcr.io`
- Push access to the repository (for CI: automatic via `GITHUB_TOKEN`)

## Local vs CI Builds

| | Local (`make release`) | CI (`PUSH=true`) |
|---|---|---|
| Architecture | Host only (fast) | amd64 + arm64 (QEMU) |
| Output | Loaded into local Docker daemon | Pushed to GHCR |
| Cache | None (not needed) | Registry-based (:buildcache tags) |
| Auth | Not required | GHCR login required |

## Local Build

Use the Makefile to build images locally. This is useful for testing before pushing.

### Build All Images

```bash
# Build all images locally (host architecture, no push)
make release VERSION=1.0.0

# Build and push to registry (multi-arch, with cache)
make release VERSION=1.0.0 PUSH=true
```

### Build Individual Images

```bash
make release-coordinator VERSION=1.0.0
make release-runner VERSION=1.0.0
make release-runner-procedural VERSION=1.0.0
make release-dashboard VERSION=1.0.0
make release-context-store VERSION=1.0.0
```

### Override Registry

By default, images are tagged for `ghcr.io/rawe`. Override if needed:

```bash
make release VERSION=1.0.0 REGISTRY=ghcr.io/myorg
```

### Authenticate to ghcr.io

Before pushing, authenticate with GitHub Container Registry:

```bash
# Using GitHub CLI
gh auth token | docker login ghcr.io -u USERNAME --password-stdin

# Or using a Personal Access Token (PAT)
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

## GitHub Actions Release

The preferred method for production releases is via GitHub Actions. This ensures consistent builds and automatic publishing.

### How It Works

1. A GitHub Actions workflow (`.github/workflows/release-images.yml`) is triggered by tags matching `v*`
2. The workflow extracts the version from the tag (e.g., `v1.0.0` → `1.0.0`)
3. It authenticates to ghcr.io, sets up QEMU (for arm64) and Docker Buildx
4. It runs `make release VERSION=... PUSH=true` to build multi-arch images with cache and push to GHCR
5. A summary is generated with pull commands

### Trigger a Release

```bash
# Create and push a tag
git tag v1.0.0
git push origin v1.0.0
```

The workflow will automatically:
- Build all 5 images for amd64 + arm64
- Tag them as `1.0.0` and `latest`
- Push to ghcr.io with registry cache update

### Manual Trigger

You can also trigger a release manually from the GitHub Actions UI:

1. Go to **Actions** → **Release Container Images**
2. Click **Run workflow**
3. Enter the version (without `v` prefix, e.g., `1.0.0`)
4. Click **Run workflow**

## Step-by-Step Release Checklist

### Before Release

- [ ] All changes are merged to `main`
- [ ] Tests pass (if applicable)
- [ ] Update component versions if needed:
  - `servers/agent-coordinator/pyproject.toml`
  - `apps/dashboard/package.json`
  - `RUNNER_VERSION` in `Makefile`
  - `servers/context-store/pyproject.toml`
- [ ] Update `CHANGELOG.md` (if you maintain one)

### Local Testing (Optional but Recommended)

```bash
# Build images locally
make release VERSION=1.0.0

# Verify images were created
docker images | grep aof

# Test locally with docker-compose
docker-compose up
```

### Release

```bash
# Commit any version updates
git add -A
git commit -m "chore: prepare release 1.0.0"

# Create tag
git tag v1.0.0

# Push commit and tag
git push origin main
git push origin v1.0.0
```

### After Release

- [ ] Verify GitHub Actions workflow completed successfully
- [ ] Verify images are available on ghcr.io
- [ ] Create a GitHub Release (optional, for release notes)

```bash
# Verify images (Docker auto-selects your architecture)
docker pull ghcr.io/rawe/aof-coordinator:1.0.0
docker pull ghcr.io/rawe/aof-runner-claude-code:1.0.0
docker pull ghcr.io/rawe/aof-runner-procedural:1.0.0
docker pull ghcr.io/rawe/aof-dashboard:1.0.0
docker pull ghcr.io/rawe/aof-context-store:1.0.0

# Verify multi-arch manifest
docker manifest inspect ghcr.io/rawe/aof-coordinator:1.0.0
```

## Versioning Policy

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (x.0.0): Breaking changes to APIs, configuration, or container interfaces
- **MINOR** (0.x.0): New features, backward-compatible changes
- **PATCH** (0.0.x): Bug fixes, minor improvements

### What Constitutes a Breaking Change?

- Changes to required environment variables
- Changes to API endpoints used between components
- Changes to volume mount paths
- Incompatible schema changes in agent blueprints

### Tag Strategy

| Tag | Description |
|-----|-------------|
| `1.0.0` | Specific release version (amd64 + arm64 manifest) |
| `latest` | Most recent release (updated automatically) |
| `buildcache` | BuildKit cache layers (managed automatically, not runnable) |

## Troubleshooting

### Build fails locally

```bash
# Check Docker is running
docker info

# Clean build cache and retry
docker builder prune
make release VERSION=1.0.0
```

### Push fails with authentication error

```bash
# Re-authenticate to ghcr.io
docker logout ghcr.io
gh auth token | docker login ghcr.io -u YOUR_USERNAME --password-stdin
```

### GitHub Actions workflow fails

1. Check the workflow logs in GitHub Actions
2. Verify the tag format is correct (`v1.0.0`, not `1.0.0`)
3. Check repository permissions for `packages: write`

## References

- [Container Images Overview](./containers/README.md)
- [Coordinator Documentation](./containers/coordinator.md)
- [Runner Documentation](./containers/runner-claude-code.md)
- [Dashboard Documentation](./containers/dashboard.md)
- [GitHub Actions Workflow](../.github/workflows/release-images.yml)
