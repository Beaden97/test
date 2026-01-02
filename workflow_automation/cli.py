"""Command-line interface for workflow automation."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from .engine import WorkflowEngine


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def cmd_run(args: argparse.Namespace) -> None:
    """Run the workflow engine."""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    engine = WorkflowEngine(config_dir=args.config_dir)

    # Load workflows
    if args.config_dir:
        workflows = engine.load_directory(args.config_dir)
        logger.info(f"Loaded {len(workflows)} workflows from {args.config_dir}")

    if args.workflow:
        for wf_path in args.workflow:
            engine.load_from_yaml(wf_path)

    if not engine.workflows:
        logger.warning("No workflows loaded. Use --config-dir or --workflow to load workflows.")
        return

    # Run the engine
    async def run_engine():
        await engine.start()
        try:
            while engine.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await engine.stop()

    asyncio.run(run_engine())


def cmd_execute(args: argparse.Namespace) -> None:
    """Execute a single workflow."""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    engine = WorkflowEngine()
    workflow = engine.load_from_yaml(args.workflow)

    logger.info(f"Executing workflow: {workflow.name}")

    async def execute():
        context = await workflow.execute({"trigger": "manual"})
        print(f"\nWorkflow completed!")
        print(f"Results: {context.results}")

    asyncio.run(execute())


def cmd_validate(args: argparse.Namespace) -> None:
    """Validate workflow configuration files."""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    engine = WorkflowEngine()
    errors = []

    for wf_path in args.workflows:
        try:
            workflow = engine.load_from_yaml(wf_path)
            print(f"✓ {wf_path}: {workflow.name} ({len(workflow.steps)} steps, {len(workflow.triggers)} triggers)")
        except Exception as e:
            errors.append((wf_path, str(e)))
            print(f"✗ {wf_path}: {e}")

    if errors:
        sys.exit(1)


def cmd_list(args: argparse.Namespace) -> None:
    """List workflows in a directory."""
    setup_logging(args.verbose)

    engine = WorkflowEngine(config_dir=args.config_dir)
    workflows = engine.load_directory()

    if not workflows:
        print("No workflows found.")
        return

    print(f"\nWorkflows in {args.config_dir}:\n")
    print(f"{'Name':<30} {'Steps':<8} {'Triggers':<10} {'Enabled':<8}")
    print("-" * 60)

    for wf in workflows:
        print(f"{wf.name:<30} {len(wf.steps):<8} {len(wf.triggers):<10} {'Yes' if wf.enabled else 'No':<8}")


def cmd_init(args: argparse.Namespace) -> None:
    """Initialize a new workflows directory with an example."""
    path = Path(args.path)
    path.mkdir(parents=True, exist_ok=True)

    example_workflow = """# Example workflow configuration
name: hello-world
description: A simple example workflow

triggers:
  - type: cron
    expression: "*/5 * * * *"  # Every 5 minutes

steps:
  - name: greet
    action:
      type: shell
      command: echo "Hello from workflow automation!"

  - name: log-time
    action:
      type: shell
      command: date
"""

    example_path = path / "example.yaml"
    example_path.write_text(example_workflow)
    print(f"Created example workflow: {example_path}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="workflow",
        description="Intelligent Workflow Automation - Your personal robot army"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # run command
    run_parser = subparsers.add_parser("run", help="Run the workflow engine")
    run_parser.add_argument("-c", "--config-dir", type=Path, help="Directory containing workflow configs")
    run_parser.add_argument("-w", "--workflow", type=Path, action="append", help="Workflow file to load")

    # execute command
    exec_parser = subparsers.add_parser("execute", help="Execute a single workflow")
    exec_parser.add_argument("workflow", type=Path, help="Workflow file to execute")

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate workflow files")
    validate_parser.add_argument("workflows", type=Path, nargs="+", help="Workflow files to validate")

    # list command
    list_parser = subparsers.add_parser("list", help="List workflows in a directory")
    list_parser.add_argument("config_dir", type=Path, help="Directory containing workflow configs")

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize a new workflows directory")
    init_parser.add_argument("path", type=Path, nargs="?", default="workflows", help="Path to create")

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "execute":
        cmd_execute(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "init":
        cmd_init(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
