"""
Interactive CLI for Gmail Cleanup

ADHD-Friendly Design (Research-Backed):

Working Memory (62-85% of ADHD have deficits - PMC11110569):
- Pre-made categories reduce cognitive load
- Batch similar decisions together

Decision Fatigue (3x more digital fatigue - J. Attention Disorders 2022):
- 4D Method limits choices to 4 options
- Quick actions with single key press

Time Blindness (Meta-analysis of 55 studies confirms deficits):
- Time-boxed sessions with visual timers
- Break reminders to prevent hyperfocus burnout

Emotional Dysregulation (38% have mood lability - 10x population rate):
- Emotional check-ins before starting
- Progress celebrations for dopamine boost
- Shame cycle interventions

Task Initiation (ADHD paralysis is freeze response, not laziness):
- "Quick wins" shown first
- Micro-sessions for when stuck
- Avoidance help resources
"""

import sys
import time
from typing import Optional, Callable
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich import box

import questionary
from questionary import Style

from ..gmail_cleanup import GmailAuth, GmailClient, EmailAnalyzer, RuleManager
from ..gmail_cleanup.client import Email
from ..gmail_cleanup.rules import Rule, quick_rule
from ..gmail_cleanup.adhd_strategies import (
    ADHDStrategies,
    SESSION_TYPES,
    ADHD_CATEGORIES,
    RECOMMENDED_LABELS,
    get_emotional_checkin,
    get_session_end_reflection,
)


# Nice colors for the prompts
custom_style = Style([
    ('question', 'bold'),
    ('answer', 'fg:green bold'),
    ('pointer', 'fg:yellow bold'),
    ('highlighted', 'fg:yellow'),
    ('selected', 'fg:green'),
])

console = Console()


class InboxCleanup:
    """
    Interactive inbox cleanup assistant.

    This walks you through cleaning up your inbox step by step,
    making decisions together about what to keep, archive, or organize.
    """

    def __init__(self, dry_run: bool = True):
        """
        Start the cleanup assistant.

        Args:
            dry_run: If True, show what would happen without doing it (safe mode)
        """
        self.dry_run = dry_run
        self.auth: Optional[GmailAuth] = None
        self.client: Optional[GmailClient] = None
        self.rules: Optional[RuleManager] = None
        self.emails: list[Email] = []
        self.analyzer: Optional[EmailAnalyzer] = None

        # Track what we've done
        self.archived_count = 0
        self.labeled_count = 0
        self.deleted_count = 0
        self.rules_created = 0

        # ADHD session tracking
        self.session_start_time: Optional[datetime] = None
        self.emails_processed_this_session = 0
        self.emotional_state: str = "okay"

    def start(self):
        """
        Start the interactive cleanup session.
        """
        self._show_welcome()

        if not self._connect():
            return

        self._main_menu()

    def _show_welcome(self):
        """
        Show welcome message with ADHD-friendly framing.
        """
        console.print()
        console.print(Panel.fit(
            "[bold blue]📧 Gmail Inbox Cleanup Assistant[/]\n\n"
            + ADHDStrategies.get_welcome_message() +
            "\n[dim]• Nothing gets deleted without your approval\n"
            "• You can stop anytime - partial progress counts[/]",
            border_style="blue"
        ))
        console.print()

        if self.dry_run:
            console.print("[yellow]🔒 SAFE MODE: Nothing will actually change (dry run)[/]")
            console.print()

        # Emotional check-in (research-backed)
        self._do_emotional_checkin()

    def _do_emotional_checkin(self):
        """
        ADHD emotional check-in before starting.

        Research: Addressing the emotional component before diving in
        helps with task initiation. (Inflow)
        """
        checkin = get_emotional_checkin()

        console.print()
        choice = questionary.select(
            checkin["prompt"],
            choices=[
                f"{emoji} {label} - {desc}"
                for emoji, label, desc, key in checkin["options"]
            ],
            style=custom_style
        ).ask()

        if choice:
            # Extract the emotional state key
            for emoji, label, desc, key in checkin["options"]:
                if label in choice:
                    self.emotional_state = key
                    response = checkin["responses"][key]
                    console.print(f"\n[cyan]{response}[/]\n")

                    # Offer extra help for overwhelmed/frozen states
                    if key in ["overwhelmed", "frozen"]:
                        if questionary.confirm(
                            "Want to see some strategies that might help?",
                            default=True,
                            style=custom_style
                        ).ask():
                            console.print(ADHDStrategies.get_avoidance_help())
                            input("Press Enter to continue...")
                    break

    def _connect(self) -> bool:
        """
        Connect to Gmail.
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Connecting to Gmail...", total=None)

            try:
                self.auth = GmailAuth()
                service = self.auth.get_service()
                self.client = GmailClient(service, dry_run=self.dry_run)
                self.rules = RuleManager(service)
                progress.update(task, description="[green]✅ Connected![/]")
                return True
            except FileNotFoundError as e:
                progress.stop()
                console.print(f"\n[red]{e}[/]")
                return False
            except Exception as e:
                progress.stop()
                console.print(f"\n[red]❌ Couldn't connect: {e}[/]")
                return False

    def _main_menu(self):
        """
        Show the main menu with ADHD-friendly options.
        """
        # Start session timer
        self.session_start_time = datetime.now()

        while True:
            console.print()

            # Check for break reminder (every 25 min)
            self._check_break_reminder()

            stats = self.client.get_inbox_stats()

            # Show current inbox status with session progress
            session_info = ""
            if self.emails_processed_this_session > 0:
                session_info = f"\n\n[green]This session: {self.emails_processed_this_session} emails processed[/]"

            console.print(Panel(
                f"[bold]📬 Inbox Status[/]\n\n"
                f"Total emails: [cyan]{stats['total_inbox']:,}[/]\n"
                f"Unread: [yellow]{stats['unread_inbox']:,}[/]"
                f"{session_info}",
                title="Your Inbox",
                border_style="cyan"
            ))

            choice = questionary.select(
                "What would you like to do?",
                choices=[
                    "🔍 Quick Scan - Find easy cleanup opportunities (recommended first!)",
                    "📊 Analyze top senders - See who emails you most",
                    "🗂️  Review by sender - Go through emails from one sender",
                    "📝 Manage rules - Create/edit auto-organization rules",
                    "🧹 Bulk cleanup - Archive old or unwanted emails",
                    "🆘 ADHD Resources - Strategies, 4D method, help for overwhelm",
                    "⚙️  Settings",
                    "👋 Exit",
                ],
                style=custom_style
            ).ask()

            if choice is None or "Exit" in choice:
                self._show_summary()
                break
            elif "Quick Scan" in choice:
                self._quick_scan()
            elif "Analyze" in choice:
                self._analyze_senders()
            elif "Review by sender" in choice:
                self._review_by_sender()
            elif "Manage rules" in choice:
                self._manage_rules()
            elif "Bulk cleanup" in choice:
                self._bulk_cleanup()
            elif "ADHD Resources" in choice:
                self._adhd_resources()
            elif "Settings" in choice:
                self._settings()

    def _check_break_reminder(self):
        """
        Check if it's time for a break (every 25 min).

        Research: ADHD brains can hyperfocus on organizing, leading to
        exhaustion. Regular breaks maintain sustainable progress.
        """
        if self.session_start_time:
            elapsed = (datetime.now() - self.session_start_time).seconds // 60
            if elapsed > 0 and elapsed % 25 == 0 and self.emails_processed_this_session > 0:
                console.print(ADHDStrategies.get_break_reminder(
                    self.emails_processed_this_session,
                    elapsed
                ))
                input("Press Enter to continue...")

    def _adhd_resources(self):
        """
        Show ADHD resources and strategies.
        """
        console.print()
        console.print("[bold]🆘 ADHD Resources[/]")
        console.print()

        choice = questionary.select(
            "What would you like to see?",
            choices=[
                "📋 The 4D Method - Decision framework for every email",
                "📊 Realistic Expectations - What 'inbox functional' means",
                "😰 Feeling Stuck? - Strategies for when you're frozen",
                "🔄 Breaking the Shame Cycle - You're not lazy",
                "⚠️  Common Mistakes - What to avoid",
                "📧 Email Bankruptcy - The fresh start option",
                "⬅️  Back to menu",
            ],
            style=custom_style
        ).ask()

        if choice and "4D Method" in choice:
            console.print(ADHDStrategies.get_4d_guide())
        elif choice and "Realistic" in choice:
            console.print(ADHDStrategies.get_realistic_expectations())
        elif choice and "Stuck" in choice:
            console.print(ADHDStrategies.get_avoidance_help())
        elif choice and "Shame" in choice:
            console.print(ADHDStrategies.get_shame_cycle_break())
        elif choice and "Mistakes" in choice:
            console.print(ADHDStrategies.get_common_mistakes())
        elif choice and "Bankruptcy" in choice:
            console.print(ADHDStrategies.get_email_bankruptcy_guide())

        if choice and "Back" not in choice:
            input("\nPress Enter to continue...")

    def _quick_scan(self):
        """
        Quick scan for easy cleanup opportunities.
        ADHD-friendly: Shows "quick wins" first!
        """
        console.print()
        console.print("[bold]🔍 Quick Scan[/] - Finding easy cleanup opportunities...")
        console.print()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Scanning inbox...", total=None)

            # Fetch recent emails for analysis
            self.emails = self.client.search_emails(query="in:inbox", max_results=500)
            progress.update(task, description=f"Found {len(self.emails)} emails")

            self.analyzer = EmailAnalyzer(self.emails)
            analysis = self.analyzer.analyze()

        # Show quick wins
        console.print()
        suggestions = self.analyzer.get_cleanup_suggestions()

        if not suggestions:
            console.print("[green]✨ Your inbox looks pretty clean![/]")
            return

        console.print(f"[bold]Found {len(suggestions)} cleanup opportunities:[/]")
        console.print()

        for i, suggestion in enumerate(suggestions[:5], 1):
            priority_color = {1: "red", 2: "yellow", 3: "green"}[suggestion.priority]
            console.print(
                f"  [{priority_color}]{i}.[/] {suggestion.description}\n"
                f"      [dim]{len(suggestion.email_ids)} emails, ~{suggestion.estimated_space_mb:.1f} MB[/]"
            )

        console.print()

        # Let them pick one to act on
        choice = questionary.select(
            "Pick one to review (or skip):",
            choices=[
                f"{i}. {s.description}" for i, s in enumerate(suggestions[:5], 1)
            ] + ["Skip for now"],
            style=custom_style
        ).ask()

        if choice and "Skip" not in choice:
            idx = int(choice.split(".")[0]) - 1
            self._act_on_suggestion(suggestions[idx])

    def _analyze_senders(self):
        """
        Show top senders analysis.
        """
        console.print()
        console.print("[bold]📊 Analyzing your inbox...[/]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Fetching emails...", total=None)

            if not self.emails:
                self.emails = self.client.search_emails(query="in:inbox", max_results=500)

            self.analyzer = EmailAnalyzer(self.emails)
            self.analyzer.analyze()

            progress.update(task, description="Analyzing senders...")
            top_senders = self.analyzer.get_top_senders(limit=15)

        # Show table
        console.print()
        table = Table(title="📬 Top Senders", box=box.ROUNDED)
        table.add_column("#", style="dim", width=3)
        table.add_column("Sender", style="cyan")
        table.add_column("Emails", justify="right")
        table.add_column("Unread", justify="right", style="yellow")
        table.add_column("Size", justify="right")

        for i, sender in enumerate(top_senders, 1):
            table.add_row(
                str(i),
                f"{sender.name[:30]}",
                str(sender.total_count),
                str(sender.unread_count) if sender.unread_count else "-",
                f"{sender.size_mb:.1f} MB"
            )

        console.print(table)
        console.print()

        # Option to act on a sender
        if questionary.confirm(
            "Would you like to review emails from one of these senders?",
            default=False,
            style=custom_style
        ).ask():
            self._pick_sender_to_review(top_senders)

    def _pick_sender_to_review(self, senders):
        """
        Let user pick a sender to review.
        """
        choices = [
            f"{s.name} ({s.total_count} emails)"
            for s in senders[:10]
        ] + ["Cancel"]

        choice = questionary.select(
            "Which sender?",
            choices=choices,
            style=custom_style
        ).ask()

        if choice and "Cancel" not in choice:
            # Find the sender
            sender_name = choice.split(" (")[0]
            for sender in senders:
                if sender.name == sender_name:
                    self._review_sender_emails(sender)
                    break

    def _review_sender_emails(self, sender):
        """
        Review emails from a specific sender.
        """
        console.print()
        console.print(f"[bold]📧 Emails from {sender.name}[/]")
        console.print(f"[dim]{sender.email}[/]")
        console.print()

        # Show sample subjects
        console.print("[bold]Sample subjects:[/]")
        for subj in sender.sample_subjects[:3]:
            console.print(f"  • {subj[:60]}")
        console.print()

        # Quick actions
        action = questionary.select(
            f"What would you like to do with emails from {sender.name}?",
            choices=[
                "📁 Create a rule to auto-organize future emails",
                "📥 Archive all existing emails from this sender",
                "🏷️  Add a label to all emails from this sender",
                "👀 View individual emails to decide",
                "⬅️  Go back",
            ],
            style=custom_style
        ).ask()

        if action and "Create a rule" in action:
            self._create_rule_for_sender(sender)
        elif action and "Archive all" in action:
            self._archive_sender_emails(sender)
        elif action and "Add a label" in action:
            self._label_sender_emails(sender)
        elif action and "View individual" in action:
            self._view_individual_emails(sender)

    def _create_rule_for_sender(self, sender):
        """
        Create a rule for emails from this sender.
        """
        console.print()
        console.print(f"[bold]📝 Create rule for {sender.name}[/]")

        # Get the domain or full email
        email_pattern = sender.email
        if "@" in email_pattern:
            domain = email_pattern.split("@")[1]
            use_domain = questionary.confirm(
                f"Match all emails from @{domain}? (No = just {email_pattern})",
                default=True,
                style=custom_style
            ).ask()
            if use_domain:
                email_pattern = domain

        # What action?
        action = questionary.select(
            "What should happen to these emails?",
            choices=[
                "📥 Archive (skip inbox, but keep email)",
                "🏷️  Add a label",
                "📥 + 🏷️  Archive AND add label",
                "✓ Mark as read",
                "⬅️  Cancel",
            ],
            style=custom_style
        ).ask()

        if action and "Cancel" not in action:
            rule_name = Prompt.ask(
                "Name for this rule",
                default=sender.name.split()[0] if sender.name else "Custom"
            )

            label = None
            if "label" in action.lower():
                label = Prompt.ask("Label name", default=rule_name)

            # Create the rule
            rule = Rule(
                name=rule_name,
                from_email=email_pattern,
                archive="Archive" in action,
                add_label=label,
                mark_read="read" in action.lower()
            )

            self.rules.create_rule(rule)
            self.rules_created += 1

            # Sync to Gmail?
            if questionary.confirm(
                "Sync to Gmail? (Auto-applies to NEW emails)",
                default=True,
                style=custom_style
            ).ask():
                self.rules.sync_to_gmail(rule)

            # Apply to existing?
            if questionary.confirm(
                f"Apply to existing {sender.total_count} emails?",
                default=True,
                style=custom_style
            ).ask():
                self.rules.apply_rule_to_existing(rule, dry_run=self.dry_run)

    def _archive_sender_emails(self, sender):
        """
        Archive all emails from a sender.
        """
        if self.dry_run:
            console.print(f"[yellow]🔹 [DRY RUN] Would archive {sender.total_count} emails[/]")
        else:
            count = self.client.archive_emails(sender.email_ids)
            self.archived_count += count

    def _label_sender_emails(self, sender):
        """
        Add a label to all emails from a sender.
        """
        label = Prompt.ask("Label name", default=sender.name.split()[0])

        # Get or create the label
        labels = self.client.get_labels()
        label_obj = None
        for l in labels:
            if l.name.lower() == label.lower():
                label_obj = l
                break

        if not label_obj:
            label_obj = self.client.create_label(label)

        if label_obj:
            count = self.client.move_to_label(sender.email_ids, label_obj.id, remove_from_inbox=False)
            self.labeled_count += count

    def _view_individual_emails(self, sender):
        """
        View and decide on individual emails.
        """
        # Get emails from this sender
        emails = [e for e in self.emails if e.sender_email.lower() == sender.email.lower()][:10]

        console.print()
        console.print(f"[bold]Showing {len(emails)} emails from {sender.name}[/]")
        console.print("[dim]Press Enter to continue, 'q' to stop[/]")
        console.print()

        for email in emails:
            console.print(Panel(
                f"[bold]{email.subject}[/]\n\n"
                f"[dim]Date: {email.date.strftime('%Y-%m-%d %H:%M')}[/]\n"
                f"[dim]Preview: {email.snippet[:150]}...[/]",
                title=f"{'📬 Unread' if email.is_unread else '📭'}",
                border_style="cyan"
            ))

            action = questionary.select(
                "Action:",
                choices=["Skip", "Archive", "Delete", "Stop reviewing"],
                style=custom_style
            ).ask()

            if action == "Archive":
                self.client.archive_emails([email.id])
                self.archived_count += 1
            elif action == "Delete":
                self.client.move_to_trash([email.id])
            elif action == "Stop reviewing":
                break

            console.print()

    def _review_by_sender(self):
        """
        Pick a sender to review.
        """
        sender_email = Prompt.ask("Enter sender email or domain (e.g., amazon.com)")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Searching...", total=None)
            emails = self.client.search_emails(f"from:{sender_email}", max_results=100)

        if not emails:
            console.print(f"[yellow]No emails found from {sender_email}[/]")
            return

        console.print(f"[green]Found {len(emails)} emails[/]")

        # Create a fake sender stats object
        from ..gmail_cleanup.analyzer import SenderStats
        sender = SenderStats(
            email=sender_email,
            name=emails[0].sender if emails else sender_email,
            total_count=len(emails),
            email_ids=[e.id for e in emails]
        )

        self._review_sender_emails(sender)

    def _manage_rules(self):
        """
        Manage email organization rules.
        """
        console.print()
        console.print("[bold]📝 Email Rules[/]")
        console.print()

        rules = self.rules.list_rules()

        if rules:
            table = Table(title="Your Rules", box=box.ROUNDED)
            table.add_column("Name", style="cyan")
            table.add_column("Matches")
            table.add_column("Actions")
            table.add_column("Gmail Sync", justify="center")

            for rule in rules:
                matches = []
                if rule.from_email:
                    matches.append(f"from:{rule.from_email}")
                if rule.subject_contains:
                    matches.append(f"subject:{rule.subject_contains}")

                actions = []
                if rule.archive:
                    actions.append("Archive")
                if rule.add_label:
                    actions.append(f"Label:{rule.add_label}")
                if rule.mark_read:
                    actions.append("Mark read")

                table.add_row(
                    rule.name,
                    ", ".join(matches) or "-",
                    ", ".join(actions) or "-",
                    "✅" if rule.gmail_filter_id else "❌"
                )

            console.print(table)
        else:
            console.print("[dim]No rules yet. Create one to auto-organize emails![/]")

        console.print()

        action = questionary.select(
            "What would you like to do?",
            choices=[
                "➕ Create new rule",
                "🔄 Sync all rules to Gmail",
                "🗑️  Delete a rule",
                "⬅️  Back to menu",
            ],
            style=custom_style
        ).ask()

        if action and "Create" in action:
            self._create_new_rule()
        elif action and "Sync" in action:
            for rule in rules:
                if not rule.gmail_filter_id:
                    self.rules.sync_to_gmail(rule)
        elif action and "Delete" in action:
            self._delete_rule(rules)

    def _create_new_rule(self):
        """
        Create a new rule interactively.
        """
        console.print()
        console.print("[bold]➕ Create New Rule[/]")

        name = Prompt.ask("Rule name")
        from_email = Prompt.ask("Match emails from (email or domain)", default="")
        subject = Prompt.ask("Match subject containing", default="")

        if not from_email and not subject:
            console.print("[red]Need at least one condition (from or subject)[/]")
            return

        action = questionary.select(
            "What should happen?",
            choices=[
                "Archive",
                "Add label",
                "Archive + Label",
                "Mark as read",
            ],
            style=custom_style
        ).ask()

        label = None
        if "label" in action.lower():
            label = Prompt.ask("Label name", default=name)

        rule = Rule(
            name=name,
            from_email=from_email or None,
            subject_contains=subject or None,
            archive="Archive" in action,
            add_label=label,
            mark_read="read" in action.lower()
        )

        self.rules.create_rule(rule)
        self.rules_created += 1

        if questionary.confirm("Sync to Gmail?", default=True, style=custom_style).ask():
            self.rules.sync_to_gmail(rule)

    def _delete_rule(self, rules):
        """
        Delete a rule.
        """
        if not rules:
            console.print("[dim]No rules to delete[/]")
            return

        choices = [r.name for r in rules] + ["Cancel"]
        choice = questionary.select("Which rule to delete?", choices=choices, style=custom_style).ask()

        if choice and choice != "Cancel":
            if questionary.confirm(f"Delete rule '{choice}'?", default=False, style=custom_style).ask():
                self.rules.delete_rule(choice)

    def _bulk_cleanup(self):
        """
        Bulk cleanup options.
        """
        console.print()
        console.print("[bold]🧹 Bulk Cleanup[/]")
        console.print()

        action = questionary.select(
            "What would you like to clean up?",
            choices=[
                "📅 Old emails (over 1 year old)",
                "📅 Very old emails (over 2 years old)",
                "📦 Large emails (over 10MB)",
                "📧 Promotions category",
                "📧 Social category",
                "⬅️  Back",
            ],
            style=custom_style
        ).ask()

        if action and "Back" not in action:
            query = ""
            if "1 year" in action:
                query = "older_than:1y"
            elif "2 years" in action:
                query = "older_than:2y"
            elif "Large" in action:
                query = "larger:10M"
            elif "Promotions" in action:
                query = "category:promotions"
            elif "Social" in action:
                query = "category:social"

            self._execute_bulk_cleanup(query, action)

    def _execute_bulk_cleanup(self, query: str, description: str):
        """
        Execute a bulk cleanup.
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Searching...", total=None)
            emails = self.client.search_emails(query, max_results=200)

        if not emails:
            console.print("[green]✨ No emails match this criteria![/]")
            return

        console.print(f"[yellow]Found {len(emails)} emails[/]")

        # Show preview
        console.print()
        console.print("[bold]Preview (first 5):[/]")
        for email in emails[:5]:
            console.print(f"  • {email.date.strftime('%Y-%m-%d')} | {email.sender[:20]} | {email.subject[:40]}")

        console.print()

        action = questionary.select(
            f"What to do with these {len(emails)} emails?",
            choices=[
                "📥 Archive all (safe - keeps emails)",
                "🗑️  Move to trash (recoverable for 30 days)",
                "⬅️  Cancel",
            ],
            style=custom_style
        ).ask()

        if action and "Archive" in action:
            email_ids = [e.id for e in emails]
            count = self.client.archive_emails(email_ids)
            self.archived_count += count
        elif action and "trash" in action:
            if questionary.confirm(
                "Are you sure? (Emails go to trash, recoverable for 30 days)",
                default=False,
                style=custom_style
            ).ask():
                email_ids = [e.id for e in emails]
                self.client.move_to_trash(email_ids)

    def _act_on_suggestion(self, suggestion):
        """
        Act on a cleanup suggestion.
        """
        console.print()
        console.print(f"[bold]{suggestion.description}[/]")
        console.print(f"[dim]{len(suggestion.email_ids)} emails, ~{suggestion.estimated_space_mb:.1f} MB[/]")

        action = questionary.select(
            "What would you like to do?",
            choices=[
                f"📥 Archive all {len(suggestion.email_ids)} emails",
                "👀 Review individually first",
                "⬅️  Skip",
            ],
            style=custom_style
        ).ask()

        if action and "Archive" in action:
            count = self.client.archive_emails(suggestion.email_ids)
            self.archived_count += count

    def _settings(self):
        """
        Settings menu.
        """
        console.print()
        console.print("[bold]⚙️  Settings[/]")
        console.print()

        current_mode = "🔒 Safe Mode (dry run)" if self.dry_run else "⚡ Live Mode"
        console.print(f"Current mode: {current_mode}")
        console.print()

        if self.dry_run:
            if questionary.confirm(
                "Switch to Live Mode? (Changes will actually be made)",
                default=False,
                style=custom_style
            ).ask():
                self.dry_run = False
                self.client.dry_run = False
                console.print("[green]Switched to Live Mode[/]")
        else:
            if questionary.confirm(
                "Switch to Safe Mode? (Preview changes without making them)",
                default=False,
                style=custom_style
            ).ask():
                self.dry_run = True
                self.client.dry_run = True
                console.print("[yellow]Switched to Safe Mode[/]")

    def _show_summary(self):
        """
        Show session summary with ADHD-friendly celebration.
        """
        console.print()

        # Progress celebration (dopamine boost!)
        console.print(ADHDStrategies.get_progress_celebration(
            self.archived_count,
            self.deleted_count,
            self.rules_created
        ))

        # Session duration
        if self.session_start_time:
            duration = (datetime.now() - self.session_start_time).seconds // 60
            console.print(f"⏱️  Session duration: {duration} minutes")

        if self.dry_run:
            console.print("\n[yellow](Dry run - no actual changes made)[/]")

        # End-of-session reflection
        console.print(get_session_end_reflection())

        console.print(Panel(
            "[bold green]You showed up. That matters.[/]\n\n"
            "Every session builds the habit. See you next time! 👋",
            border_style="green"
        ))
        console.print()


def main():
    """
    Main entry point for the CLI.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Gmail Inbox Cleanup Assistant")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run in live mode (actually make changes). Default is safe/dry-run mode."
    )

    args = parser.parse_args()

    cleanup = InboxCleanup(dry_run=not args.live)
    cleanup.start()


if __name__ == "__main__":
    main()
