# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-07-25

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
