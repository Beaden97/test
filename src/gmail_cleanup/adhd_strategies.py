"""
ADHD-Informed Email Management Strategies

Comprehensive research-based strategies for email management with ADHD.
All strategies are backed by peer-reviewed research, clinical studies,
and evidence from ADHD coaches and therapists.

=== KEY RESEARCH FINDINGS ===

WORKING MEMORY:
- 62-85% of people with ADHD have working memory deficits (PMC11110569)
- Adults with ADHD show ~60% impairment in working memory (Barkley et al., 2008)
- Effect sizes range from Cohen's d = 0.69-2.15 (Frontiers in Psychiatry)

DECISION FATIGUE:
- ADHD brains show increased activation during decisions (fMRI studies)
- 3x more likely to report digital communication fatigue (J. Attention Disorders, 2022)
- Dopamine dysregulation causes faster mental depletion

TIME BLINDNESS:
- Meta-analysis of 55 studies confirms time perception deficits
- ADHD characterized as fundamentally a "timing disorder" (PMC6556068)
- Affects task duration estimation, deadline management, scheduling

EMOTIONAL DYSREGULATION:
- 38% of children with ADHD have mood lability (10x population rate)
- Up to 70% of adults report Rejection Sensitive Dysphoria symptoms
- Avoidance mediates ADHD-emotion regulation deficits

TASK INITIATION:
- Avoidant Automatic Thoughts (AAT) are frequent daily occurrences
- "ADHD Paralysis" is a freeze response, not procrastination
- Task paralysis differs from laziness - it's neurological

=== SOURCES ===
- Barkley, R.A. et al. (2008) - Working Memory Studies
- Journal of Attention Disorders (2022) - Digital Communication Fatigue
- PMC11110569, PMC7483636 - Working Memory Meta-analyses
- PMC6556068, PMC8293837 - Time Blindness Research
- ADDitude Magazine, CHADD, Life Skills Advocate - Practical Strategies
- Marla Cummins, Cheryl Susman - ADHD Coaching Methods
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime
import random


# =============================================================================
# THE 4D METHOD - Research-backed decision framework
# =============================================================================

class DecisionType(Enum):
    """
    The 4D Method reduces decision fatigue by limiting choices to 4.

    Research: "Decision fatigue refers to the deteriorating quality of
    decisions after cognitive overload." ADHD brains are particularly
    susceptible because they already expend more cognitive energy on
    everyday tasks. (Edge Foundation, Relational Psych)

    The 4D method was originally developed by Microsoft and adapted
    for ADHD by coaches because it provides structure that reduces
    overwhelm.
    """
    DELETE = "delete"      # Will I ever need this? No → Trash it
    DO = "do"              # Can I handle in 2 min? Yes → Do it NOW
    DELEGATE = "delegate"  # Am I the right person? No → Forward it
    DEFER = "defer"        # Needs more time? → Schedule it, archive


# =============================================================================
# ADHD-SPECIFIC EMAIL CATEGORIES
# =============================================================================

@dataclass
class ADHDEmailCategory:
    """
    Pre-defined categories reduce decision-making load.

    Research: "Using broad, simple folder names is more effective than
    detailed ones. Instead of creating numerous subfolders, consider
    using a few main categories." (Unconventional Organisation)

    ADHD experts recommend action-based organization (verbs) over
    topic-based organization (nouns) because it aligns with how
    ADHD brains naturally think about tasks.
    """
    name: str
    description: str
    action: DecisionType
    gmail_query: Optional[str] = None
    why_it_works: str = ""


# Research-backed categories that minimize cognitive load
ADHD_CATEGORIES = [
    ADHDEmailCategory(
        name="🗑️ Safe to Delete",
        description="Newsletters you never read, old promotions, automated notifications",
        action=DecisionType.DELETE,
        gmail_query="category:promotions older_than:7d",
        why_it_works="~50% of emails can be deleted immediately (Front.com research)"
    ),
    ADHDEmailCategory(
        name="⚡ Quick Wins (< 2 min)",
        description="Emails you can handle in under 2 minutes - do them NOW",
        action=DecisionType.DO,
        gmail_query="is:unread -has:attachment smaller:50K",
        why_it_works="Quick wins provide dopamine hits that build momentum"
    ),
    ADHDEmailCategory(
        name="📦 Archive & Forget",
        description="Receipts, confirmations, shipping - useful but not actionable",
        action=DecisionType.DEFER,
        gmail_query="from:(noreply OR no-reply OR confirmation OR receipt OR shipping)",
        why_it_works="Removes visual clutter without losing information"
    ),
    ADHDEmailCategory(
        name="⏰ Needs Focus Time",
        description="Long emails requiring thought - schedule dedicated time",
        action=DecisionType.DEFER,
        gmail_query="is:unread larger:100K",
        why_it_works="Prevents getting stuck on complex emails during quick sessions"
    ),
    ADHDEmailCategory(
        name="🔄 Subscription Audit",
        description="Newsletters - apply the 3-strike rule (unsubscribe if no value after 3)",
        action=DecisionType.DELETE,
        gmail_query="unsubscribe older_than:30d",
        why_it_works="Reduces future inbox volume permanently"
    ),
]


# =============================================================================
# TIME-BOXED SESSIONS (Research-backed durations)
# =============================================================================

SESSION_TYPES = {
    "micro": {
        "minutes": 5,
        "name": "Micro Sprint",
        "description": "Just open and close 3-5 emails (no action needed)",
        "goal": "Build initiation momentum",
        "why": "When frozen, the smallest viable action is opening the inbox. "
               "Each microtask delivers a small dopamine boost."
    },
    "sprint": {
        "minutes": 10,
        "name": "Quick Triage",
        "description": "Sort emails into categories, don't respond yet",
        "goal": "Categorize 20-30 emails",
        "why": "Separates categorization from responding - reduces decision load"
    },
    "focused": {
        "minutes": 25,
        "name": "Pomodoro Session",
        "description": "One focused session with break after",
        "goal": "Process one category completely",
        "why": "25 minutes is the standard Pomodoro - long enough for progress, "
               "short enough to maintain focus"
    },
    "deep": {
        "minutes": 45,
        "name": "Deep Clean",
        "description": "Longer session for major cleanup (includes break reminder)",
        "goal": "Significant inbox reduction",
        "why": "ADHD focus can sustain 45-60 min with genuine interest - "
               "but MUST include break reminder to prevent hyperfocus burnout"
    }
}


# =============================================================================
# RECOMMENDED FOLDER STRUCTURE
# =============================================================================

RECOMMENDED_LABELS = [
    {
        "name": "⚡ Action Required",
        "description": "Emails that need a response or task from YOU",
        "color": "#ea4335",  # Red
        "why": "Verb-based label - tells you what to DO, not what it IS"
    },
    {
        "name": "⏳ Waiting On",
        "description": "Emails where you're waiting on someone else",
        "color": "#fbbc04",  # Yellow
        "why": "Prevents losing track of delegated items"
    },
    {
        "name": "📚 Reference",
        "description": "Info you might need later (receipts, confirmations)",
        "color": "#4285f4",  # Blue
        "why": "Noun-based for information storage, not action"
    },
    {
        "name": "💭 Someday",
        "description": "Interesting but not urgent - review monthly",
        "color": "#9e9e9e",  # Gray
        "why": "Gives permission to defer without guilt"
    },
]


# =============================================================================
# ADHD STRATEGIES CLASS
# =============================================================================

class ADHDStrategies:
    """
    Research-backed ADHD email management strategies.

    Core Principles (from meta-analyses and clinical research):
    1. REDUCE DECISIONS - Pre-made categories, batch similar emails
    2. TIME-BOX EVERYTHING - Prevents both avoidance and hyperfocus
    3. EXTERNAL STRUCTURE - Timers, body doubling, scheduled times
    4. VISUAL PROGRESS - Dopamine from seeing accomplishment
    5. "GOOD ENOUGH" - Inbox functional > inbox zero
    6. COMPASSION - Shame keeps you stuck, kindness gets you moving
    """

    @staticmethod
    def get_welcome_message() -> str:
        """Welcome message that sets realistic expectations."""
        return (
            "📧 Welcome to your ADHD-friendly email session\n\n"
            "Before we start, remember:\n"
            "• Opening this tool is already a win 🎉\n"
            "• 'Inbox functional' beats 'inbox zero'\n"
            "• Progress over perfection\n"
            "• You can stop anytime - partial progress counts\n"
        )

    @staticmethod
    def get_session_intro(session_type: str = "sprint") -> dict:
        """
        Get introduction for a timed session.

        Research: "Set aside 2-3 x 30-minute blocks each day" and
        "Nothing sabotages productivity more than having your inbox
        open all day." Scheduled times create urgency and prevent
        constant context-switching.
        """
        session = SESSION_TYPES.get(session_type, SESSION_TYPES["sprint"])
        return {
            "header": f"⏱️ {session['name']} ({session['minutes']} minutes)",
            "goal": session['goal'],
            "description": session['description'],
            "tip": session['why'],
            "minutes": session['minutes']
        }

    @staticmethod
    def get_4d_guide() -> str:
        """
        The 4D method quick reference.

        Research: Providing a structured decision-making process reduces
        overwhelm. Instead of staring at an email wondering what to do,
        you have a simple framework that guides action.
        """
        return """
╔══════════════════════════════════════════════════════════════════╗
║                     📧 The 4D Method                              ║
║          (Your decision framework for every email)                ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  🗑️  DELETE    Will I ever need this?                           ║
║               No → Trash it (~50% of emails can go!)             ║
║                                                                  ║
║  ⚡  DO        Can I handle this in under 2 minutes?             ║
║               Yes → Do it NOW (don't context-switch)             ║
║                                                                  ║
║  🔄  DELEGATE  Am I the right person for this?                   ║
║               No → Forward it to whoever is                      ║
║                                                                  ║
║  📅  DEFER     Does this need more time/thought?                 ║
║               Yes → Label it "Action Required" & archive         ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  💡 When in doubt, ARCHIVE. You can always search for it later!  ║
╚══════════════════════════════════════════════════════════════════╝
"""

    @staticmethod
    def get_batch_decision_prompt(sender: str, count: int) -> dict:
        """
        Prompt for batch decisions on emails from same sender.

        Research: "Group similar emails to decide once, not 100 times."
        Batching reduces decision fatigue by treating similar items as
        a single choice rather than N individual choices.
        """
        return {
            "header": f"📧 {count} emails from {sender}",
            "question": "What should happen to ALL of them?",
            "options": [
                ("A", "Archive all", "Keep but hide from inbox"),
                ("D", "Delete all", "Move to trash (recoverable 30 days)"),
                ("R", "Create rule", "Auto-handle ALL future emails from them"),
                ("K", "Keep all", "Leave in inbox for now"),
                ("1", "One by one", "Review individually (takes longer)"),
            ],
            "tip": "💡 Batching saves mental energy - same sender usually means same action"
        }

    @staticmethod
    def get_quick_decision_prompt(subject: str, sender: str) -> dict:
        """
        Simplified decision for single emails using 4D.

        Research: "Giving yourself a set amount of time to make a
        decision can prevent overthinking. For minor choices, setting
        a timer for 30-60 seconds can encourage quicker decision-making."
        (Relational Psych)
        """
        return {
            "header": "⏱️ Quick decision (trust your gut!)",
            "email": f"'{subject}' from {sender}",
            "options": [
                ("D", "🗑️ Delete", "Won't need this"),
                ("A", "📦 Archive", "Keep but out of inbox"),
                ("L", "⏰ Later", "Needs action - defer it"),
                ("S", "⏭️ Skip", "Decide another time"),
            ],
            "tip": "💡 Trust your first instinct - archived emails can always be found!"
        }

    @staticmethod
    def get_break_reminder(emails_processed: int, session_minutes: int) -> str:
        """
        Break reminders to prevent hyperfocus burnout.

        Research: ADHD brains can hyperfocus on organizing, leading to
        exhaustion and burnout. Regular breaks maintain sustainable
        progress and prevent the "did too much, now avoiding" cycle.
        """
        reminders = [
            "🧘 Stand up and stretch for 30 seconds - your body will thank you",
            "💧 Hydration check! Grab some water before continuing",
            "👀 20-20-20 rule: Look at something 20 feet away for 20 seconds",
            "🎉 You're making real progress. Take a deep breath.",
            "⚡ Quick movement break - shake out your hands and shoulders",
            "🌟 Nice work! Walk to the window and back before continuing",
        ]
        base_message = random.choice(reminders)

        return (
            f"\n{'='*50}\n"
            f"⏸️  BREAK TIME\n"
            f"{'='*50}\n\n"
            f"You've processed {emails_processed} emails in {session_minutes} minutes!\n\n"
            f"{base_message}\n\n"
            f"Remember: Breaks prevent burnout. Sustainable > intense.\n"
        )

    @staticmethod
    def get_progress_celebration(archived: int, deleted: int, rules: int) -> str:
        """
        Celebrate progress with dopamine-boosting messages.

        Research: Visual progress and small wins provide motivation
        for ADHD brains. The dopamine from accomplishment reinforces
        the behavior and makes future sessions easier.
        """
        total = archived + deleted

        celebrations = {
            0: ("🌱", "Starting fresh", "Opening this tool is already a win!"),
            10: ("✨", "Building momentum", "You're getting into the groove!"),
            25: ("🚀", "Making real progress", "Your inbox is breathing easier!"),
            50: ("💪", "Serious cleanup", "Look at you go!"),
            100: ("🏆", "Inbox warrior", "This is incredible progress!"),
            200: ("👑", "Email champion", "You're unstoppable!"),
        }

        # Find appropriate tier
        tier = 0
        for threshold in sorted(celebrations.keys()):
            if total >= threshold:
                tier = threshold

        emoji, title, message = celebrations[tier]

        return (
            f"\n{emoji} {title.upper()}\n"
            f"{'-'*40}\n"
            f"📥 Archived: {archived}\n"
            f"🗑️ Deleted: {deleted}\n"
            f"📝 Rules created: {rules}\n"
            f"\n{message}\n"
        )

    @staticmethod
    def get_avoidance_help() -> str:
        """
        Help for when someone is frozen/avoiding.

        Research: "If your inbox triggers shutdown, it may be less about
        'willpower' and more about your brain protecting you from
        uncertainty and overload." ADHD paralysis is a freeze response,
        not laziness. (ADDA, Life Skills Advocate)
        """
        return """
╔══════════════════════════════════════════════════════════════════╗
║                  😰 Feeling Stuck? That's Normal                 ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ADHD paralysis is a FREEZE RESPONSE, not laziness.              ║
║  Your brain is trying to protect you from overwhelm.             ║
║                                                                  ║
║  Try one of these (pick the easiest):                            ║
║                                                                  ║
║  1. 🎯 START ABSURDLY SMALL                                      ║
║     Just open and close 3 emails. No action needed.              ║
║                                                                  ║
║  2. 🎵 ADD BACKGROUND NOISE                                      ║
║     Put on music or a familiar show while you work               ║
║                                                                  ║
║  3. 🧸 TRY BODY DOUBLING                                         ║
║     Have someone nearby (or on video call) while working         ║
║                                                                  ║
║  4. ⏰ SET A TINY TIMER                                          ║
║     5 minutes only. You can stop after 5 minutes.                ║
║                                                                  ║
║  5. 🏃 MOVE YOUR BODY FIRST                                      ║
║     Walk, jumping jacks, stretch - THEN open inbox               ║
║                                                                  ║
║  6. 📝 EXTERNALIZE THE TASK                                      ║
║     Write "Check 3 emails" on paper, then do it                  ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  Remember: Opening this tool is already a win! 🎉                ║
║  Freeze isn't a character flaw - it's a nervous-system state.    ║
╚══════════════════════════════════════════════════════════════════╝
"""

    @staticmethod
    def get_realistic_expectations() -> str:
        """
        Set realistic expectations to reduce anxiety.

        Research: "Focus on responding to emails that align with your
        goals or responsibilities, and accept that you might never
        'catch up' on 100% of emails. Shifting expectations can reduce
        persistent anxiety." (Inflow)

        Note: Average Gmail notification count on home screens was
        11,072 unread emails (musicMagpie survey) - massive backlogs
        are NORMAL.
        """
        return """
╔══════════════════════════════════════════════════════════════════╗
║              📋 Realistic Goals (Not Inbox Zero!)                 ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ✅ GOOD GOALS FOR TODAY:                                        ║
║     • Process the most important 10-20 emails                    ║
║     • Create 1-2 rules for repeat senders                        ║
║     • Archive one category of old emails                         ║
║     • Unsubscribe from 3 useless newsletters                     ║
║                                                                  ║
║  ❌ UNREALISTIC GOALS (let these go):                            ║
║     • Reach inbox zero                                           ║
║     • Read every single email                                    ║
║     • Respond to everything today                                ║
║     • Create a "perfect" organization system                     ║
║                                                                  ║
║  📊 REALITY CHECK:                                               ║
║     Average Gmail user has 11,072 unread emails.                 ║
║     "Inbox zero" is a MYTH for most people.                      ║
║     "Inbox functional" is the real goal.                         ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  💡 "Good enough" IS good enough.                                ║
╚══════════════════════════════════════════════════════════════════╝
"""

    @staticmethod
    def get_shame_cycle_break() -> str:
        """
        Address the shame-avoidance cycle.

        Research: "Tasks that are onerous or potentially shame-inducing
        get delayed as long as possible." When you feel ashamed because
        you didn't answer emails, you may start to avoid your inbox
        altogether, causing shame to spiral. (ADDitude, Joon App)
        """
        return """
╔══════════════════════════════════════════════════════════════════╗
║                  🔄 Breaking the Shame Cycle                     ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  THE CYCLE:                                                      ║
║  Missed emails → Shame → Avoid inbox → More missed → More shame  ║
║                                                                  ║
║  HOW TO BREAK IT:                                                ║
║                                                                  ║
║  1. NAME IT                                                      ║
║     "I'm feeling shame about my inbox. That's normal."           ║
║                                                                  ║
║  2. REMEMBER: It's Neurological, Not Moral                       ║
║     ADHD paralysis is a freeze response, not laziness.           ║
║     Your worth isn't measured by inbox count.                    ║
║                                                                  ║
║  3. START WITH SELF-COMPASSION                                   ║
║     What would you say to a friend in this situation?            ║
║     Say that to yourself.                                        ║
║                                                                  ║
║  4. LOWER THE BAR DRAMATICALLY                                   ║
║     Goal: "Find and respond to ONE important email"              ║
║     That's it. Everything else is bonus.                         ║
║                                                                  ║
║  5. CELEBRATE SHOWING UP                                         ║
║     Opening this tool broke the avoidance cycle.                 ║
║     That deserves recognition.                                   ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  Shame keeps you stuck. Compassion gets you moving. 💚           ║
╚══════════════════════════════════════════════════════════════════╝
"""

    @staticmethod
    def get_common_mistakes() -> str:
        """
        Common ADHD email mistakes to avoid.

        Research compiled from ADHD coaches and lived experience.
        """
        return """
╔══════════════════════════════════════════════════════════════════╗
║                ⚠️ Common ADHD Email Mistakes                     ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ❌ Creating complex folder systems                              ║
║     → They require maintenance you won't do                      ║
║     → Use 3-5 labels max, rely on search                         ║
║                                                                  ║
║  ❌ Using inbox as a reminder system                             ║
║     → Guarantees it will always feel cluttered                   ║
║     → Move tasks to external task manager instead                ║
║                                                                  ║
║  ❌ Filing emails and forgetting them                            ║
║     → Out of sight, out of mind is REAL for ADHD                 ║
║     → Keep "Action Required" visible, archive the rest           ║
║                                                                  ║
║  ❌ Checking email constantly (or first thing AM)                ║
║     → Creates endless interruptions, destroys focus              ║
║     → Schedule 2-3 specific times per day                        ║
║                                                                  ║
║  ❌ Overthinking responses                                       ║
║     → Perfectionism leads to paralysis                           ║
║     → Short emails are valid. Send it.                           ║
║                                                                  ║
║  ❌ Aiming for inbox zero                                        ║
║     → Sets impossible standard → failure → shame                 ║
║     → Aim for "inbox functional" instead                         ║
║                                                                  ║
║  ❌ Not unsubscribing aggressively                               ║
║     → Every kept subscription = future decisions                 ║
║     → 3-strike rule: No value after 3? Unsubscribe.              ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""

    @staticmethod
    def get_email_bankruptcy_guide() -> str:
        """
        Guide for email bankruptcy when completely overwhelmed.

        Research: Merlin Mann's "DMZ" method - when you have thousands
        of unprocessed emails, the cognitive load of looking at them
        prevents any progress. Moving them out of sight (but not
        deleting) provides a clean slate without data loss.
        """
        return """
╔══════════════════════════════════════════════════════════════════╗
║            📧 Email Bankruptcy (The Fresh Start)                 ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Have 1000+ unread emails? The backlog itself is the problem.    ║
║  Staring at it creates overwhelm that prevents ANY action.       ║
║                                                                  ║
║  THE DMZ METHOD:                                                 ║
║                                                                  ║
║  1. Create a label called "📦 Pre-[Today's Date] Archive"        ║
║                                                                  ║
║  2. Move ALL current inbox emails to that label                  ║
║                                                                  ║
║  3. You now have inbox zero! (Fresh start)                       ║
║                                                                  ║
║  4. IMPORTANT: You didn't delete anything!                       ║
║     - If something was truly urgent, they'll email again         ║
║     - You can search that archive anytime                        ║
║     - Review the archive weekly if you want                      ║
║                                                                  ║
║  5. Going forward: Use 4D method on NEW emails only              ║
║                                                                  ║
║  WHY THIS WORKS:                                                 ║
║  - Removes the visual overwhelm                                  ║
║  - Gives psychological fresh start                               ║
║  - Preserves everything (no loss anxiety)                        ║
║  - Lets you build good habits with clean slate                   ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""


# =============================================================================
# EMOTIONAL CHECK-INS
# =============================================================================

def get_emotional_checkin() -> dict:
    """
    Emotional check-in before starting email work.

    Research: Addressing the emotional component before diving in
    helps with task initiation. "Silently say to yourself, 'This
    feels overwhelming, and that's okay.'" (Inflow)
    """
    return {
        "prompt": "Quick check-in: How are you feeling about your inbox?",
        "options": [
            ("😌", "Calm", "I've got this", "great"),
            ("😐", "Neutral", "It's fine, let's do this", "okay"),
            ("😰", "Anxious", "Kinda stressed about it", "anxious"),
            ("😫", "Overwhelmed", "I've been avoiding this", "overwhelmed"),
            ("🥶", "Frozen", "I don't know where to start", "frozen"),
        ],
        "responses": {
            "great": "Awesome! Let's channel that energy into a productive session.",
            "okay": "Good mindset. We'll take it one email at a time.",
            "anxious": "That's valid. Remember: you can stop anytime. Let's start small.",
            "overwhelmed": "I hear you. Let's focus on just ONE thing. What's the easiest win?",
            "frozen": "Opening this tool already broke the freeze. Want to see some strategies that might help?"
        }
    }


def get_session_end_reflection() -> str:
    """
    End-of-session reflection prompts.

    Research: Reflection helps consolidate gains and builds
    self-efficacy for future sessions.
    """
    return """
╔══════════════════════════════════════════════════════════════════╗
║                   📝 Quick Reflection                            ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  • What was easier than expected?                                ║
║  • What would make next time smoother?                           ║
║  • What's ONE rule that would help future you?                   ║
║                                                                  ║
║  Remember: Every session builds the habit.                       ║
║  You showed up. That matters.                                    ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""


# =============================================================================
# QUICK REFERENCE CONSTANTS
# =============================================================================

# Time estimates for ADHD (triple normal estimates due to time blindness)
ADHD_TIME_ESTIMATES = {
    "quick_triage": "10-15 min (not 5)",
    "full_cleanup": "45-60 min (not 20)",
    "rule_creation": "5-10 min per rule",
    "batch_decision": "2-3 min per sender",
}

# Recommended daily email times (research-backed)
RECOMMENDED_EMAIL_TIMES = [
    "9:00 AM - Morning triage",
    "1:00 PM - Post-lunch check",
    "4:00 PM - End-of-day wrap-up",
]

# The "Three Strike" unsubscribe rule
THREE_STRIKE_RULE = (
    "If you receive 3 emails from a sender without taking action "
    "or getting value, give yourself permission to unsubscribe."
)
