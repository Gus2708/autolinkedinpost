"""Viral hook formulas and founder angles registry for 2026 LinkedIn optimization."""
from __future__ import annotations

from typing import Any, Dict, Optional

HOOK_FORMULAS: Dict[str, Dict[str, Any]] = {
    "F1": {
        "name": "Platform Risk Anaphora",
        "category": "long-form",
        "goal": "comments",
        "template": "{Platform1} can {restrict|shadowban|throttle} you {timing}.\n{Platform2} can {bad thing} for {reason}.\nYou don't own {audience}. You don't own {feed}. You're renting {attention}.",
        "description": "Exposes rented audience vulnerabilities with escalating parallel clauses.",
    },
    "F2": {
        "name": "R.I.P. Category Obituary",
        "category": "long-form",
        "goal": "reposts",
        "template": "R.I.P. {Old Category} (Year-Year).\nMost people haven't noticed, but {trigger event} changed everything.",
        "description": "Declares an obsolete tool or methodology dead to reframe the standard.",
    },
    "F3": {
        "name": "Year-over-Year Pivot",
        "category": "long-form",
        "goal": "likes",
        "template": "In {Year-1}: {Old Belief / Old Metric}.\nIn {Year}: {New Reality / New Pivot}.\nHere is what changed:",
        "description": "Juxtaposes previous mindset with current hard-won conviction.",
    },
    "F4": {
        "name": "Time-Anchor Confession",
        "category": "long-form",
        "goal": "comments",
        "template": "I spent {Number} years doing {Activity} the wrong way.\nUntil {Turning point} forced me to rethink:",
        "description": "Builds high empathy and curiosity via vulnerable confession.",
    },
    "F5": {
        "name": "Self-Proving Meta",
        "category": "long-form",
        "goal": "saves",
        "template": "This post will {proof / outcome} in under {time}.\nBecause {mechanism}:\n1. {Step 1}\n2. {Step 2}",
        "description": "Demonstrates the principle inside the post itself in real-time.",
    },
    "F6": {
        "name": "Comment-Gate Lead Magnet",
        "category": "long-form",
        "goal": "comments",
        "template": "I built {Asset / Resource} that solves {Pain point}.\nComment '{Keyword}' and I'll send it directly.",
        "description": "Maximizes comment velocity within the golden first hour.",
    },
    "F7": {
        "name": "Odd-Precision Money Ledger",
        "category": "long-form",
        "goal": "saves",
        "template": "Exactly ${Exact Amount} spent on {Subject}.\nHere is the exact breakdown and ROI:",
        "description": "Uses non-rounded financial figures to project radical credibility.",
    },
    "F8": {
        "name": "Paid-vs-Free Reversal",
        "category": "long-form",
        "goal": "reposts",
        "template": "People pay ${Amount} for {Course/Consulting}.\nHere it is for free in {Number} bullet points:",
        "description": "High perceived-value arbitrage between gated products and open copy.",
    },
    "F9": {
        "name": "Curiosity-Gap Teaser",
        "category": "long-form",
        "goal": "comments",
        "template": "The single biggest mistake in {Topic} isn't {Common Guess}.\nIt's {Unintuitive Answer}.",
        "description": "Breaks standard assumptions before revealing the counter-intuitive fix.",
    },
    "F10": {
        "name": "Contrarian + Historical Receipts",
        "category": "long-form",
        "goal": "reposts",
        "template": "Everyone is betting on {Trend A}.\nHistory shows that {Historical Parallel} won instead.\nHere are the receipts:",
        "description": "Validates contrarian conviction with historical evidence.",
    },
    "F11": {
        "name": "Emotional Cold-Open",
        "category": "short-form",
        "goal": "comments",
        "template": "{Short visceral sentence}.\nNo context. Just the truth:",
        "description": "Strips introductory pleasantries for immediate emotional hook.",
    },
    "F12": {
        "name": "Permission Slip",
        "category": "short-form",
        "goal": "likes",
        "template": "You are allowed to stop {Common Obligation}.\nYou don't need to {Unnecessary hustle}.",
        "description": "Relieves audience fatigue by granting permission to drop performative tasks.",
    },
    "F13": {
        "name": "Bait-and-Switch Reversal",
        "category": "short-form",
        "goal": "comments",
        "template": "I thought {Premise A} was the key to {Goal}.\nI was completely wrong.",
        "description": "Immediate narrative turn right at the fold.",
    },
    "F14": {
        "name": "Named Gratitude / Tribute",
        "category": "short-form",
        "goal": "likes",
        "template": "The best advice I ever received came from {Person}.\n{Short memorable quote}:",
        "description": "Leverages genuine mentorship and relationship capital.",
    },
    "F15": {
        "name": "Explain-to-Kids Simplification",
        "category": "short-form",
        "goal": "saves",
        "template": "If you cannot explain {Complex Tech} to a 10-year-old, you don't understand it.\nHere is {Concept} in 3 analogies:",
        "description": "Forces clarity over cleverness through extreme simplification.",
    },
    "F16": {
        "name": "Status-Strip Humility",
        "category": "short-form",
        "goal": "comments",
        "template": "Titles don't matter when {Crisis / Real Work}.\nHere is what actually held the system together:",
        "description": "Subverts professional ego to highlight boots-on-the-ground engineering.",
    },
    "F17": {
        "name": "Controlled A/B Anecdote",
        "category": "structural",
        "goal": "comments",
        "template": "We tested {Strategy A} vs {Strategy B} on {Sample / Timeframe}.\nResult: {Outcome A} vs {Outcome B}.\nThe difference was one variable:",
        "description": "Shapes post around empirical side-by-side contrast.",
    },
    "F18": {
        "name": "False-Binary Dissolve",
        "category": "structural",
        "goal": "reposts",
        "template": "The debate between {Option A} and {Option B} is missing the point.\nThe real bottleneck is {Option C}.",
        "description": "Rejects false dichotomies to introduce structural third alternatives.",
    },
    "F19": {
        "name": "Anecdote-Meets-Evidence Bridge",
        "category": "structural",
        "goal": "saves",
        "template": "Last week {Concrete micro-story}.\nIt sounded like an anomaly until I checked the data:\n— {Data point 1}\n— {Data point 2}",
        "description": "Connects individual symptom to macro data proof.",
    },
    "F20": {
        "name": "Diverging-Curves Close",
        "category": "structural",
        "goal": "reposts",
        "template": "At Day 1: Both {Cohort A} and {Cohort B} look identical.\nAt Year 2: One scales 10x, the other stalls.\nHere is the divergence point:",
        "description": "Visualizes compounding advantages over time.",
    },
}

FOUNDER_ANGLES: Dict[str, Dict[str, Any]] = {
    "A1": {
        "name": "Reprice the Category",
        "tension": "Outsiders value you by a low-status label (wrapper, agency, feature).",
        "best_fit_formula": "F10",
        "goal": "reposts",
        "template": "Everyone calls what we do {low-status label}.\nThat label sets the price. And the price is wrong.\nBecause {mechanism} means it behaves like {high-status category}:",
    },
    "A2": {
        "name": "Content-to-Pipeline Bridge",
        "tension": "Views don't pay payroll; high-trust pipeline does.",
        "best_fit_formula": "F5",
        "goal": "comments",
        "template": "We stopped posting for impressions.\nHere is how 5 targeted conversations generated our biggest design partner:",
    },
    "A3": {
        "name": "Audience of One",
        "tension": "Broad appeal dilutes technical authority.",
        "best_fit_formula": "F17",
        "goal": "reposts",
        "template": "I wrote this for exactly one engineer considering our team:\n{Specific architectural challenge}:",
    },
    "A4": {
        "name": "The Scarce-Shots Math",
        "tension": "Early-stage runway means limited high-conviction bets.",
        "best_fit_formula": "F7",
        "goal": "saves",
        "template": "We only had {Number} engineering bets before runway ran out.\nHere is how we filtered {Option A} to bet on {Option B}:",
    },
    "A5": {
        "name": "The Unglamorous Bet",
        "tension": "Competitors chase hype; durable moats come from boring infrastructure.",
        "best_fit_formula": "F18",
        "goal": "reposts",
        "template": "While everyone rushed into {Hype Trend}, we spent 6 months optimizing {Boring Layer}.\nHere is why that unglamorous bet became our biggest moat:",
    },
    "A6": {
        "name": "The Limit of Delegation",
        "tension": "Knowing what a founder can never delegate.",
        "best_fit_formula": "F16",
        "goal": "comments",
        "template": "You can delegate {Task A} and {Task B}.\nNever delegate {Core Conviction}.\nHere is the exact boundary line:",
    },
    "A7": {
        "name": "Designed Serendipity",
        "tension": "Luck favors intentional surface area.",
        "best_fit_formula": "F19",
        "goal": "likes",
        "template": "Our biggest breakthrough looked like luck from the outside.\nIn reality, we engineered 50 micro-experiments:",
    },
    "A8": {
        "name": "The Evasive-Sentence Test",
        "tension": "Corporate jargon hides failure; brutal clarity reveals fixes.",
        "best_fit_formula": "F11",
        "goal": "comments",
        "template": "When an engineer or founder says '{Jargon phrase}', it usually means '{Uncomfortable truth}'.\nHere is what happens when you remove the euphemism:",
    },
    "A9": {
        "name": "The Delegation Line",
        "tension": "Scaling past initial founder bottleneck.",
        "best_fit_formula": "F3",
        "goal": "saves",
        "template": "The moment I stepped out of {Operational duty}, velocity doubled.\nHere is the framework for knowing when to let go:",
    },
    "A10": {
        "name": "The Learning Gate",
        "tension": "Speed of iteration over perfection.",
        "best_fit_formula": "F20",
        "goal": "reposts",
        "template": "Shipping is not the goal. Learning velocity is.\nHere is our feedback loop from commit to customer insight in under 24 hours:",
    },
}


def get_hook_formula(code: str) -> Optional[Dict[str, Any]]:
    """Retrieve hook formula by code (F1..F20)."""
    return HOOK_FORMULAS.get(code.upper().strip())


def get_founder_angle(code: str) -> Optional[Dict[str, Any]]:
    """Retrieve founder angle by code (A1..A10)."""
    return FOUNDER_ANGLES.get(code.upper().strip())
