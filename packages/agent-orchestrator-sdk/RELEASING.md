# Releasing @rawe/agent-orchestrator-sdk

Internal documentation for publishing the SDK to npm.

## Prerequisites

1. **npm account** with access to the `@rawe` scope
2. **Logged in to npm:**
   ```bash
   npm login
   ```
3. **Verify login:**
   ```bash
   npm whoami
   # Should output: rawe
   ```

## Pre-release Checklist

- [ ] All changes committed
- [ ] Tests pass (if applicable)
- [ ] Version bumped in `package.json`
- [ ] README is up to date
- [ ] Build succeeds

## Release Process

### 1. Build the package

```bash
cd packages/agent-orchestrator-sdk
npm run clean
npm run build
```

### 2. Verify the build

```bash
# Check what will be published
npm pack --dry-run
```

Expected output:
```
dist/
README.md
package.json
```

### 3. Bump version

Follow [semver](https://semver.org/):
- **Patch** (0.1.0 → 0.1.1): Bug fixes, no API changes
- **Minor** (0.1.0 → 0.2.0): New features, backward compatible
- **Major** (0.1.0 → 1.0.0): Breaking changes

```bash
# Patch release
npm version patch

# Minor release
npm version minor

# Major release
npm version major
```

This automatically:
- Updates `package.json` version
- Creates a git commit
- Creates a git tag

### 4. Publish

```bash
# First release (scoped packages are private by default)
npm publish --access public

# Subsequent releases
npm publish
```

### 5. Push tags

```bash
git push origin main --tags
```

## Verify Release

```bash
# Check npm registry
npm view @rawe/agent-orchestrator-sdk

# Test installation in a temp directory
cd /tmp
mkdir test-sdk && cd test-sdk
npm init -y
npm install @rawe/agent-orchestrator-sdk
```

## Unpublish (Emergency Only)

You can unpublish within 72 hours:
```bash
npm unpublish @rawe/agent-orchestrator-sdk@0.1.0
```

## Deprecate a Version

```bash
npm deprecate @rawe/agent-orchestrator-sdk@0.1.0 "Use 0.2.0 instead"
```

## Troubleshooting

### "You must be logged in to publish"
```bash
npm login
```

### "403 Forbidden - Package name too similar"
The `@rawe` scope should prevent this. Verify scope access:
```bash
npm access ls-packages
```

### "402 Payment Required"
Scoped packages require `--access public` on first publish (or npm paid plan for private).
