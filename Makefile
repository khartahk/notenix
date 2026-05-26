# notenix / kanal — release helpers
#
# Usage:
#   make bump-patch   # 0.1.0 → 0.1.1  (bug fixes)
#   make bump-minor   # 0.1.0 → 0.2.0  (new features)
#   make bump-major   # 0.1.0 → 1.0.0  (breaking changes)
#   make release      # auto-detect bump from commits, tag, push
#   make install-hooks  # install pre-commit hooks into .git/

.PHONY: bump-patch bump-minor bump-major release install-hooks

# Auto-detect bump level from conventional commits since last tag, then
# tag + push. This is the standard release flow.
release:
	cz bump --changelog
	git push --follow-tags

# Manual overrides when you want to force a specific bump level.
bump-patch:
	cz bump --increment PATCH --changelog
	git push --follow-tags

bump-minor:
	cz bump --increment MINOR --changelog
	git push --follow-tags

bump-major:
	cz bump --increment MAJOR --changelog
	git push --follow-tags

# Install git hooks via pre-commit framework.
# Run once after cloning the repo.
install-hooks:
	pre-commit install --hook-type commit-msg
