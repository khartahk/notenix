# notenix / kanal — release helpers
#
# Usage:
#   make bump-patch   # 0.1.0 → 0.1.1  (bug fixes)
#   make bump-minor   # 0.1.0 → 0.2.0  (new features)
#   make bump-major   # 0.1.0 → 1.0.0  (breaking changes)
#   make release      # auto-detect bump from commits, tag, push
#   make changelog    # regenerate CHANGELOG.md without bumping
#   make install-hooks  # install pre-commit hooks into .git/

CZ = cd pkgs/kanal && cz

.PHONY: bump-patch bump-minor bump-major release changelog install-hooks

# All release logic in one shell context so $$tag is read after bump.
define do-release
	$(CZ) bump --files-only $(1)
	$(CZ) changelog
	@tag=$$(grep '^version' pkgs/kanal/pyproject.toml | head -1 | awk -F'"' '{print $$2}'); \
	git add -A; \
	git commit -m "bump: version → v$$tag"; \
	git tag "v$$tag"; \
	git push origin HEAD "v$$tag"; \
	echo "Waiting for GitHub mirror to sync tag v$$tag…"; \
	for i in 1 2 3 4 5 6 7 8 9 10; do \
	  gh api repos/n1x05/notenix/git/refs/tags/"v$$tag" >/dev/null 2>&1 && break; \
	  echo "  $$i/10 not yet…"; sleep 6; \
	done; \
	notes=$$(awk "/^## v$$tag /{found=1; next} found && /^## /{exit} found{print}" CHANGELOG.md); \
	echo "Creating GitHub release v$$tag…"; \
	printf '%s\n' "$$notes" | gh release create "v$$tag" --repo n1x05/notenix --title "v$$tag" --notes-file -
endef

# Auto-detect bump level from conventional commits since last tag.
release:
	$(call do-release,)

# Manual overrides when you want to force a specific bump level.
bump-patch:
	$(call do-release,--increment PATCH)

bump-minor:
	$(call do-release,--increment MINOR)

bump-major:
	$(call do-release,--increment MAJOR)

# Regenerate CHANGELOG.md from all conventional commits (no version bump).
changelog:
	$(CZ) changelog

# Install git hooks via pre-commit framework.
# Run once after cloning the repo.
install-hooks:
	pre-commit install --hook-type commit-msg
