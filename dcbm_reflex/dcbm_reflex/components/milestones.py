"""Milestones tracking section for Welcome, Quarterly bonus, and Annual Fee Waiver."""

import reflex as rx
from dcbm_reflex.state import DCBMState
from dcbm_reflex.styles import CARD_STYLE, SUB_BOX_STYLE, GOLD_ACCENT, GREEN_ACCENT, AMBER_ACCENT


def welcome_card() -> rx.Component:
    """Card 1: Welcome Milestone (₹1.5L in 90d)."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.text("Welcome Milestone", font_size="11px", font_weight="700", text_transform="uppercase", color=rx.color("slate", 11)),
                    rx.text("₹1.5 Lakhs in 90 Days", font_size="15px", font_weight="700"),
                    spacing="0",
                    align_items="start",
                ),
                rx.cond(
                    DCBMState.welcome_met,
                    rx.badge("✅ UNLOCKED", variant="surface", color_scheme="green", radius="full", font_size="11px"),
                    rx.badge(f"⏳ {DCBMState.welcome_days_left}d left", variant="surface", color_scheme="blue", radius="full", font_size="11px"),
                ),
                justify="between",
                width="100%",
                align="start",
            ),
            rx.box(
                rx.hstack(
                    rx.text(f"₹{DCBMState.welcome_spend:,.0f}", font_size="22px", font_weight="800", color=GREEN_ACCENT),
                    rx.text(f"/ ₹{DCBMState.welcome_target:,.0f}", font_size="13px", color=rx.color("slate", 10), font_weight="500"),
                    rx.badge(f"{DCBMState.welcome_progress:.1f}%", color_scheme="green", radius="full", size="1"),
                    align="baseline",
                    spacing="2",
                ),
                rx.progress(
                    value=DCBMState.welcome_progress,
                    color_scheme="green",
                    radius="full",
                    size="2",
                    margin_top="8px",
                ),
                margin_y="8px",
            ),
            rx.box(
                rx.hstack(
                    rx.vstack(
                        rx.text("Perks Status", font_size="10px", font_weight="700", text_transform="uppercase", color=rx.color("slate", 10)),
                        rx.text("Unlocked & Claimed", font_size="12px", font_weight="800", color=GREEN_ACCENT),
                        spacing="0",
                        align_items="start",
                    ),
                    rx.vstack(
                        rx.text("Memberships", font_size="10px", font_weight="700", text_transform="uppercase", color=rx.color("slate", 10)),
                        rx.text("Club Marriott • Prime • Swiggy", font_size="11px", font_weight="600", color=rx.color("slate", 11)),
                        spacing="0",
                        align_items="end",
                    ),
                    justify="between",
                    align="center",
                    width="100%",
                ),
                style=SUB_BOX_STYLE,
                width="100%",
            ),
            justify="between",
            height="100%",
            width="100%",
            spacing="3",
        ),
        style=CARD_STYLE,
        flex="1",
    )


def quarterly_card() -> rx.Component:
    """Card 2: Quarterly Bonus Milestone (₹4L in 90d for 10k bonus RP)."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.text(DCBMState.q_label, font_size="11px", font_weight="700", text_transform="uppercase", color=rx.color("slate", 11)),
                    rx.text("10,000 Bonus RP", font_size="15px", font_weight="700"),
                    spacing="0",
                    align_items="start",
                ),
                rx.cond(
                    DCBMState.q_met,
                    rx.badge("✅ UNLOCKED", variant="surface", color_scheme="green", radius="full", font_size="11px"),
                    rx.badge(f"⏳ {DCBMState.q_days_left}d left", variant="surface", color_scheme="amber", radius="full", font_size="11px"),
                ),
                justify="between",
                width="100%",
                align="start",
            ),
            rx.box(
                rx.hstack(
                    rx.text(f"₹{DCBMState.q_spend:,.0f}", font_size="22px", font_weight="800", color=AMBER_ACCENT),
                    rx.text(f"/ ₹{DCBMState.q_target:,.0f}", font_size="13px", color=rx.color("slate", 10), font_weight="500"),
                    rx.badge(f"{DCBMState.q_progress:.1f}%", color_scheme="amber", radius="full", size="1"),
                    align="baseline",
                    spacing="2",
                ),
                rx.progress(
                    value=DCBMState.q_progress,
                    color_scheme="amber",
                    radius="full",
                    size="2",
                    margin_top="8px",
                ),
                margin_y="8px",
            ),
            rx.box(
                rx.hstack(
                    rx.vstack(
                        rx.text("Remaining Needed", font_size="10px", font_weight="700", text_transform="uppercase", color=rx.color("slate", 10)),
                        rx.text(f"₹{DCBMState.q_remaining:,.0f}", font_size="13px", font_weight="800", color=AMBER_ACCENT),
                        spacing="0",
                        align_items="start",
                    ),
                    rx.vstack(
                        rx.text("Run-Rate Needed", font_size="10px", font_weight="700", text_transform="uppercase", color=rx.color("slate", 10)),
                        rx.text(f"₹{DCBMState.q_runrate:,.0f} / day", font_size="11px", font_weight="600", color=rx.color("slate", 11)),
                        spacing="0",
                        align_items="end",
                    ),
                    justify="between",
                    align="center",
                    width="100%",
                ),
                style=SUB_BOX_STYLE,
                width="100%",
            ),
            justify="between",
            height="100%",
            width="100%",
            spacing="3",
        ),
        style=CARD_STYLE,
        flex="1",
    )


def annual_card() -> rx.Component:
    """Card 3: Annual Fee Waiver (₹8L in card year)."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.text("Annual Fee Waiver", font_size="11px", font_weight="700", text_transform="uppercase", color=rx.color("slate", 11)),
                    rx.text("Save ₹10,000 Fee", font_size="15px", font_weight="700"),
                    spacing="0",
                    align_items="start",
                ),
                rx.cond(
                    DCBMState.ann_met,
                    rx.badge("✅ WAIVED", variant="surface", color_scheme="green", radius="full", font_size="11px"),
                    rx.badge(f"⏳ {DCBMState.ann_days_left}d left", variant="surface", color_scheme="blue", radius="full", font_size="11px"),
                ),
                justify="between",
                width="100%",
                align="start",
            ),
            rx.box(
                rx.hstack(
                    rx.text(f"₹{DCBMState.ann_spend:,.0f}", font_size="22px", font_weight="800", color=GOLD_ACCENT),
                    rx.text(f"/ ₹{DCBMState.ann_target:,.0f}", font_size="13px", color=rx.color("slate", 10), font_weight="500"),
                    rx.badge(f"{DCBMState.ann_progress:.1f}%", color_scheme="amber", radius="full", size="1"),
                    align="baseline",
                    spacing="2",
                ),
                rx.progress(
                    value=DCBMState.ann_progress,
                    color_scheme="amber",
                    radius="full",
                    size="2",
                    margin_top="8px",
                ),
                margin_y="8px",
            ),
            rx.box(
                rx.hstack(
                    rx.vstack(
                        rx.text("Remaining to Waive", font_size="10px", font_weight="700", text_transform="uppercase", color=rx.color("slate", 10)),
                        rx.text(f"₹{DCBMState.ann_remaining:,.0f}", font_size="13px", font_weight="800", color=GOLD_ACCENT),
                        spacing="0",
                        align_items="start",
                    ),
                    rx.vstack(
                        rx.text("Deadline", font_size="10px", font_weight="700", text_transform="uppercase", color=rx.color("slate", 10)),
                        rx.text(f"{DCBMState.ann_deadline}", font_size="11px", font_weight="600", color=rx.color("slate", 11)),
                        spacing="0",
                        align_items="end",
                    ),
                    justify="between",
                    align="center",
                    width="100%",
                ),
                style=SUB_BOX_STYLE,
                width="100%",
            ),
            justify="between",
            height="100%",
            width="100%",
            spacing="3",
        ),
        style=CARD_STYLE,
        flex="1",
    )


def milestones_section() -> rx.Component:
    """Spend milestones section with title and 3 cards."""
    return rx.vstack(
        rx.text(
            "🎯 Spend Milestones & Fee Waiver",
            font_size="16px",
            font_weight="700",
            letter_spacing="-0.01em",
            margin_top="8px",
        ),
        rx.flex(
            welcome_card(),
            quarterly_card(),
            annual_card(),
            gap="4",
            direction=rx.breakpoints(initial="column", md="row"),
            width="100%",
        ),
        spacing="3",
        width="100%",
    )
