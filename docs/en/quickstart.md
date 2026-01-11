# Quickstart

This quickstart guide will have you using AI-powered coding assistance in just a few minutes. By the end, you'll understand how to use Claude Code for common development tasks.

## Getting Started

Claude Code is your AI pair programmer. Talk to it like you would a helpful colleague - describe what you want to achieve, and it will help you get there.

## Let Claude Explore First

One of the most important best practices when working with Claude Code is to **let Claude explore your codebase before making changes**. Skipping exploration is a common mistake that leads to lower quality results.

### Why Exploration Matters

Having Claude jump straight into code changes without understanding the context creates rework. Claude might:

- Implement a solution that misses requirements
- Choose the wrong architectural approach
- Make changes that break existing functionality
- Miss established patterns and conventions in your codebase

Think of it like building a house without blueprints - fast at first, but problems emerge quickly.

### The Explore → Plan → Code → Commit Workflow

Instead of giving Claude a large task all at once, break it down into progressive steps:

1. **Explore**: Ask Claude to read relevant files, images (like UI mockups), or URLs. Instruct it not to write any code yet. The goal is information gathering.

2. **Plan**: Have Claude outline the approach before implementation. This significantly improves the quality and success rate of the final code.

3. **Code**: With context and a plan in place, Claude can now implement changes effectively.

4. **Commit**: Review and commit the changes with clear commit messages.

### How to Use Exploration Mode

#### Using Plan Mode

Use Plan Mode (toggle with `Shift+Tab`) when dealing with a large or unfamiliar codebase. This lets Claude safely explore the repository, read relevant files, and build a mental model of the project before suggesting modifications.

Example prompts for exploration:

```
Explain the codebase structure
```

```
I want to build X, can you explore solutions starting with the simplest one first?
```

```
Read the authentication module and explain how it works - don't make any changes yet
```

#### Using the Explore Agent

The Explore agent is a read-only file search specialist that can:

- Use Glob and Grep to find files
- Read file contents
- Navigate codebases safely

It's strictly prohibited from creating or modifying files, making it perfect for initial investigation.

### Example Workflow

Here's a practical example of the explore-first approach:

**Task**: Add a dark mode toggle to the application settings

**Step 1 - Explore**:
```
Look at the current settings implementation and theming system.
How is styling currently handled? Don't make any changes yet.
```

**Step 2 - Plan**:
```
Based on what you found, outline a plan for adding dark mode support.
What files need to change? What's the simplest approach?
```

**Step 3 - Code**:
```
Implement the dark mode toggle following the plan we discussed.
```

**Step 4 - Commit**:
```
Commit these changes with an appropriate message.
```

### Setting Up Exploration Workflows in CLAUDE.md

You can define standard workflows in your `CLAUDE.md` file that Claude should follow for different types of tasks:

```markdown
## Workflows

Before making changes, answer these questions:
1. Is this a question about current state that requires investigation first?
2. Does this need a detailed plan before implementation?

Standard workflows:
- Features: explore-plan-code-commit
- Bug fixes: reproduce-investigate-fix-verify
- Refactoring: understand-plan-refactor-test
```

### Key Takeaways

- **Don't skip exploration** - it's tempting to jump straight to coding, but taking time to understand the codebase leads to better results
- **Use Plan Mode** for complex or unfamiliar codebases
- **Break down large tasks** into explore → plan → code → commit phases
- **Document your workflows** in CLAUDE.md for consistent results

## Next Steps

- Learn about [CLAUDE.md files](/docs/en/claude-md) for customizing Claude Code for your codebase
- Explore [best practices](/docs/en/best-practices) for maximizing productivity
- Set up [hooks](/docs/en/hooks) for automated workflows
