#!/usr/bin/env bash
#
# Release dbt-qod.
#
# Bumps the adapter version, verifies the build, then commits, tags and pushes.
# Pushing the v<version> tag triggers .github/workflows/publish.yml, which
# builds and publishes to PyPI via Trusted Publishing (OIDC) - nothing is
# uploaded from this machine.
#
# Usage:
#   scripts/release.sh [--dry-run] <version>
#
#   scripts/release.sh 0.2.0            # release 0.2.0
#   scripts/release.sh --dry-run 0.2.0  # run all checks, change nothing
#
# Requires: git, python with the `build` and `twine` packages installed.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION_FILE="dbt/adapters/qod/__version__.py"
RELEASE_BRANCH="main"

die() { echo "error: $*" >&2; exit 1; }
step() { echo; echo "==> $*"; }

# --- arguments ---------------------------------------------------------------

DRY_RUN=false
VERSION=""
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    -h|--help) sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) die "unknown option: $arg" ;;
    *) [[ -n "$VERSION" ]] && die "unexpected argument: $arg"; VERSION="$arg" ;;
  esac
done

[[ -n "$VERSION" ]] || die "usage: scripts/release.sh [--dry-run] <version>"
# PEP 440 subset: X.Y.Z with an optional pre-release suffix (e.g. 0.2.0rc1).
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+((a|b|rc)[0-9]+)?$ ]] \
  || die "version must look like 1.2.3 or 1.2.3rc1, got: $VERSION"
TAG="v$VERSION"

cd "$REPO_ROOT"

# --- preflight ---------------------------------------------------------------

step "Preflight checks"

CURRENT_VERSION="$(python -c "
ns = {}
exec(open('$VERSION_FILE').read(), ns)
print(ns['version'])
")"
[[ "$VERSION" != "$CURRENT_VERSION" ]] \
  || die "version $VERSION is already the current version"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[[ "$BRANCH" == "$RELEASE_BRANCH" ]] \
  || die "releases must be cut from $RELEASE_BRANCH (on: $BRANCH)"

[[ -z "$(git status --porcelain --untracked-files=no)" ]] \
  || die "working tree has uncommitted changes; commit or stash first"

git fetch origin "$RELEASE_BRANCH" --tags
[[ "$(git rev-parse HEAD)" == "$(git rev-parse "origin/$RELEASE_BRANCH")" ]] \
  || die "local $RELEASE_BRANCH is not in sync with origin/$RELEASE_BRANCH"

git rev-parse -q --verify "refs/tags/$TAG" >/dev/null \
  && die "tag $TAG already exists"

python -c "import build, twine" 2>/dev/null \
  || die "missing build tools; run: python -m pip install build twine"

echo "ok: $CURRENT_VERSION -> $VERSION on $RELEASE_BRANCH"

# --- bump + verify -----------------------------------------------------------

step "Bumping $VERSION_FILE to $VERSION"
printf 'version = "%s"\n' "$VERSION" > "$VERSION_FILE"

restore_on_failure() {
  echo "restoring $VERSION_FILE" >&2
  git checkout -- "$VERSION_FILE"
}
trap restore_on_failure ERR

step "Building distributions"
rm -rf dist
python -m build
twine check dist/*
ls dist/ | grep -q "dbt_qod-$VERSION" \
  || die "built artifacts do not carry version $VERSION"

# --- commit, tag, push -------------------------------------------------------

if $DRY_RUN; then
  trap - ERR
  git checkout -- "$VERSION_FILE"
  step "Dry run complete"
  echo "All checks passed. Without --dry-run this would have:"
  echo "  - committed 'Release $TAG' on $RELEASE_BRANCH"
  echo "  - tagged $TAG and pushed branch + tag"
  echo "  - triggered publish.yml to release to PyPI"
  exit 0
fi

step "Committing and tagging $TAG"
git add "$VERSION_FILE"
git commit -m "Release $TAG"
git tag -a "$TAG" -m "Release $TAG"
trap - ERR

step "Pushing $RELEASE_BRANCH and $TAG"
git push origin "$RELEASE_BRANCH" "$TAG"

step "Done"
echo "PyPI publish is now running in GitHub Actions:"
echo "  https://github.com/starlake-ai/dbt-qod-adapter/actions/workflows/publish.yml"
echo "Once green, verify: pip install dbt-qod==$VERSION"
