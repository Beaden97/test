# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Available Agents

This project has 23 custom agents installed in `.claude/agents/`:

### Context & Workflow
- **context-manager** - Context management for multi-agent workflows and long-running tasks

### Python Development
- **python-pro** - Python development specialist
- **django-pro** - Django framework expert
- **fastapi-pro** - FastAPI development specialist
- **temporal-python-pro** - Temporal workflow orchestration

### JavaScript/TypeScript
- **javascript-pro** - JavaScript development specialist
- **typescript-pro** - TypeScript development specialist

### Backend & Architecture
- **backend-architect** - Backend system design
- **graphql-architect** - GraphQL API design
- **event-sourcing-architect** - Event sourcing patterns
- **tdd-orchestrator** - Test-driven development workflows

### Cloud & Infrastructure
- **cloud-architect** - Multi-cloud architecture (AWS/Azure/GCP)
- **kubernetes-architect** - Kubernetes cluster design and operations
- **terraform-specialist** - Infrastructure as code
- **deployment-engineer** - CI/CD and deployment automation
- **network-engineer** - Network architecture and security
- **service-mesh-expert** - Service mesh implementation
- **hybrid-cloud-architect** - Hybrid cloud solutions

### Security
- **security-auditor** - Security auditing and compliance
- **threat-modeling-expert** - Threat analysis and modeling

### Quality & Testing
- **architect-review** - AI-powered architecture review
- **performance-engineer** - Performance optimization
- **test-automator** - Test automation strategies

## GSD Task Management

Use `/gsd:help` to see all available task management commands.

## Universal Development Guidelines

### Code Quality Standards
- Write clean, readable, and maintainable code
- Follow consistent naming conventions across the project
- Use meaningful variable and function names
- Keep functions focused and single-purpose
- Add comments for complex logic and business rules

### Git Workflow
- Use descriptive commit messages following conventional commits format
- Create feature branches for new development
- Keep commits atomic and focused on single changes
- Use pull requests for code review before merging
- Maintain a clean commit history

### Documentation
- Keep README.md files up to date
- Document public APIs and interfaces
- Include usage examples for complex features
- Maintain inline code documentation
- Update documentation when making changes

### Testing Approach
- Write tests for new features and bug fixes
- Maintain good test coverage
- Use descriptive test names that explain the expected behavior
- Organize tests logically by feature or module
- Run tests before committing changes

### Security Best Practices
- Never commit sensitive information (API keys, passwords, tokens)
- Use environment variables for configuration
- Validate input data and sanitize outputs
- Follow principle of least privilege
- Keep dependencies updated

## Project Structure Guidelines

### File Organization
- Group related files in logical directories
- Use consistent file and folder naming conventions
- Separate source code from configuration files
- Keep build artifacts out of version control
- Organize assets and resources appropriately

### Configuration Management
- Use configuration files for environment-specific settings
- Centralize configuration in dedicated files
- Use environment variables for sensitive or environment-specific data
- Document configuration options and their purposes
- Provide example configuration files

## Development Workflow

### Before Starting Work
1. Pull latest changes from main branch
2. Create a new feature branch
3. Review existing code and architecture
4. Plan the implementation approach

### During Development
1. Make incremental commits with clear messages
2. Run tests frequently to catch issues early
3. Follow established coding standards
4. Update documentation as needed

### Before Submitting
1. Run full test suite
2. Check code quality and formatting
3. Update documentation if necessary
4. Create clear pull request description

## Common Patterns

### Error Handling
- Use appropriate error handling mechanisms for the language
- Provide meaningful error messages
- Log errors appropriately for debugging
- Handle edge cases gracefully
- Don't expose sensitive information in error messages

### Performance Considerations
- Profile code for performance bottlenecks
- Optimize database queries and API calls
- Use caching where appropriate
- Consider memory usage and resource management
- Monitor and measure performance metrics

### Code Reusability
- Extract common functionality into reusable modules
- Use dependency injection for better testability
- Create utility functions for repeated operations
- Design interfaces for extensibility
- Follow DRY (Don't Repeat Yourself) principle

## Review Checklist

Before marking any task as complete:
- [ ] Code follows established conventions
- [ ] Tests are written and passing
- [ ] Documentation is updated
- [ ] Security considerations are addressed
- [ ] Performance impact is considered
- [ ] Code is reviewed for maintainability
