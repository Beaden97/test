# Workflow Automation

**Your personal robot army for intelligent workflows.**

A powerful Python-based workflow automation system with scheduled jobs, file watchers, webhooks, and configurable YAML workflows.

## Features

- **Multiple Trigger Types**
  - Cron expressions for scheduled jobs
  - File system watchers for reactive automation
  - Webhooks for external integrations
  - Manual triggers for on-demand execution

- **Flexible Actions**
  - Shell commands with variable interpolation
  - HTTP requests for API integrations
  - Python code execution for complex logic
  - Parallel and sequential action composition

- **Smart Execution**
  - Automatic retries with configurable delays
  - Conditional step execution
  - Context passing between steps
  - Comprehensive execution history

## Installation

```bash
pip install -e .
```

Or install dependencies directly:

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Initialize a workflows directory

```bash
workflow init my-workflows
```

### 2. Create a workflow (YAML)

```yaml
name: hello-world
description: A simple example workflow

triggers:
  - type: cron
    expression: "*/5 * * * *"  # Every 5 minutes

steps:
  - name: greet
    action:
      type: shell
      command: echo "Hello, automation!"
```

### 3. Run the engine

```bash
workflow run --config-dir my-workflows
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `workflow run` | Start the workflow engine |
| `workflow execute <file>` | Run a single workflow |
| `workflow validate <files>` | Validate workflow configs |
| `workflow list <dir>` | List workflows in directory |
| `workflow init [path]` | Create example workflow |

## Workflow Configuration

### Triggers

**Cron Trigger** - Schedule-based execution:
```yaml
triggers:
  - type: cron
    expression: "0 * * * *"  # Every hour
```

**File Trigger** - React to file changes:
```yaml
triggers:
  - type: file
    path: /path/to/watch
    patterns: ["*.txt", "*.json"]
    events: [created, modified, deleted]
```

**Webhook Trigger** - HTTP endpoint:
```yaml
triggers:
  - type: webhook
    path: /my-webhook
    method: POST
```

### Actions

**Shell Action** - Execute commands:
```yaml
action:
  type: shell
  command: echo "Processing {{trigger.path}}"
  timeout: 60
```

**HTTP Action** - Make API calls:
```yaml
action:
  type: http
  url: https://api.example.com/endpoint
  method: POST
  headers:
    Authorization: "Bearer {{api_token}}"
  body:
    message: "Hello from workflow"
```

**Python Action** - Run Python code:
```yaml
action:
  type: python
  code: |
    result = {"processed": len(context.variables)}
```

### Step Options

```yaml
steps:
  - name: my-step
    action:
      type: shell
      command: ./process.sh
    condition: "results['previous_step']['success']"
    on_failure: continue  # or: stop, retry
    retry_count: 3
    retry_delay: 5.0
```

## Programmatic Usage

```python
import asyncio
from workflow_automation import (
    WorkflowEngine, Workflow,
    CronTrigger, ShellAction
)

# Create a workflow
workflow = Workflow(name="my-workflow")
workflow.add_trigger(CronTrigger("*/1 * * * *"))
workflow.add_step("greet", ShellAction("echo 'Hello!'"))

# Run with engine
engine = WorkflowEngine()
engine.register(workflow)

asyncio.run(engine.start())
```

## Examples

See the `examples/` directory for complete workflow examples:

- `backup-workflow.yaml` - Daily automated backups
- `file-sync-workflow.yaml` - File synchronization on changes
- `health-check-workflow.yaml` - Service monitoring
- `notification-workflow.yaml` - Webhook notifications
- `data-pipeline-workflow.yaml` - Data processing pipeline

## License

MIT