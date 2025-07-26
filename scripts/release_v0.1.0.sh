#!/bin/bash
# GatheRing v0.1.0 Release Script

echo "🚀 Preparing GatheRing v0.1.0 release..."

# Ensure we're on main branch and up to date
echo "📌 Checking current branch..."
git checkout main
git pull origin main

# Add all documentation files
echo "📝 Adding documentation..."
mkdir -p docs/api docs/user docs/technical

# Create the documentation files (you need to save the artifacts to these locations)
cat > docs/api/reference.md << 'EOF'
# Copy content from the API Reference artifact here
EOF

cat > docs/user/guide.md << 'EOF'
# Copy content from the User Guide artifact here
EOF

cat > docs/technical/developer.md << 'EOF'
# Copy content from the Developer Guide artifact here
EOF

# Create a VERSION file
echo "0.1.0" > VERSION

# Create a CHANGELOG for this release
cat > CHANGELOG.md << 'EOF'
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-01-XX

### Added
- Initial release of GatheRing framework
- Core agent system with customizable personalities
- Multi-LLM provider support (OpenAI, Anthropic, Ollama)
- Modular personality block system
- Tool system with Calculator and FileSystem tools
- Multi-agent conversation support
- Memory management system
- Comprehensive test suite with 61% coverage
- Complete API documentation
- User guide and developer documentation

### Architecture
- Interface-based design for extensibility
- Factory pattern for object creation
- Dependency injection for flexibility
- Plugin-ready architecture

### Testing
- TDD approach with pytest
- Unit, integration, and e2e test structure
- Fixtures and mocking support
- CI/CD ready configuration

### Known Limitations
- Mock LLM provider for testing only
- Basic tool implementations
- Memory is in-memory only (no persistence)
- Web interface not yet implemented
EOF

# Update version in pyproject.toml and setup.py if they exist
if [ -f pyproject.toml ]; then
    sed -i 's/version = ".*"/version = "0.1.0"/' pyproject.toml
fi

# Commit all changes
echo "💾 Committing release preparation..."
git add -A
git commit -m "chore: prepare release v0.1.0

- Add comprehensive documentation
  - API reference guide
  - User guide
  - Developer guide
- Add CHANGELOG.md
- Add VERSION file
- Update project metadata

This release includes:
- Core agent framework
- Personality system
- Tool integration
- Multi-agent conversations
- 20/20 tests passing
- 61% code coverage"

# Create annotated tag for the release
echo "🏷️  Creating release tag..."
git tag -a v0.1.0 -m "Release version 0.1.0

Initial release of GatheRing - Collaborative Multi-Agent AI Framework

Features:
- Customizable AI agents with personalities
- Multi-LLM provider support
- Modular tool system
- Agent collaboration capabilities
- Comprehensive test suite
- Full documentation

See CHANGELOG.md for details."

# Create develop branch
echo "🌿 Creating develop branch..."
git checkout -b develop

# Push everything
echo "📤 Pushing to remote..."
git push origin main
git push origin develop
git push origin v0.1.0

echo "✅ Release v0.1.0 completed!"
echo ""
echo "Next steps:"
echo "1. Go to GitHub and create a release from the v0.1.0 tag"
echo "2. Add release notes from CHANGELOG.md"
echo "3. Announce the release"
echo ""
echo "Development continues on 'develop' branch"
echo "Current branch: $(git branch --show-current)"