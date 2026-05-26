# notenix / kanal — release helpers
#
# Usage:
#   make bump-patch   # 0.1.0 → 0.1.1  (bug fixes)
#   make bump-minor   # 0.1.0 → 0.2.0  (new features)
#   make bump-major   # 0.1.0 → 1.0.0  (breaking changes)
#   make release      # auto-detect bump from commits, tag, push
#   make install-hooks  # install pre-commit hooks into .git/

CZ = cd pkgs/kanal && cz

.PHONY: bump-patch bump-minor bump-major release changelog install-hooks _gh-release

# Auto-detect bump level from conventional commits since last tag, then
# tag + push. This is the standard release flow.
release:
	$(CZ) bump --changelog
	git push --follow-tags
	$(MAKE) _gh-release

# Manual overrides when you want to force a specific bump level.
bump-patch:
	$(CZ) bump --increment PATCH --changelog
	git push --follow-tags
	$(MAKE) _gh-release

bump-minor:
	$(CZ) bump --increment MINOR --changelog
	git push --follow-tags
	$(MAKE) _gh-release

bump-major:
	$(CZ) bump --increment MAJOR --changelog
	git push --follow-tags
	$(MAKE) _gh-release

# Regenerate CHANGELOG.md from all conventional commits (no version bump).
changelog:
	$(CZ) changelog

# Create a GitHub release for the latest tag, using its CHANGELOG section as notes.
# Requires: gh CLI authenticated (gh auth login).
_gh-release:
	@tag=$$(git describe --tags --abbrev=0); \
	notes=$$(awk "/^## $$tag /{found=1; next} found && /^## /{exit} found{print}" CHANGELOG.md); \
	echo "Creating GitHub release $$tag…"; \
	printf '%s\n' "$$notes" | gh release create "$$tag" --repo n1x05/notenix --title "$$tag" --notes-file -

# Install git hooks via pre-commit framework.
# Run once after cloning the repo.
install-hooks:
	pre-commit install --hook-type commit-msg
