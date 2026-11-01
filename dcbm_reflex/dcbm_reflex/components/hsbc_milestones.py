"""Milestones and Perks section for HSBC Live+ dashboard."""

import reflex as rx
from dcbm_reflex.state import DCBMState
from dcbm_reflex.styles import CARD_STYLE, GREEN_ACCENT, HSBC_RED, HSBC_RED_BG, HSBC_RED_BORDER, SUB_BOX_STYLE


def hsbc_welcome_card() -> rx.Component:
    """Milestone 1: Welcome Voucher Milestone."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.box(
                        rx.icon("gift", size=18, color=GREEN_ACCENT),
                        background_color="rgba(21, 128, 61, 0.1)",
                        border="1px solid rgba(21, 128, 61, 0.25)",
                        border_radius="8px",
                        padding="6px",
                    ),
                    rx.vstack(
                        rx.text("Welcome Benefit", font_size="12px", font_weight="600", color=rx.color("slate", 11)),
                        rx.text("₹20,000 Spend in 30 Days", font_size="14.5px", font_weight="700"),
                        spacing="0",
                        align_items="start",
                    ),
                    align="center",
                    spacing="2",
                ),
                rx.badge("✅ UNLOCKED", variant="surface", color_scheme="green", radius="full", font_size="11px", font_weight="700"),
                justify="between",
                align="center",
                width="100%",
            ),
            # Spend progress
            rx.vstack(
                rx.hstack(
                    rx.text("₹20,796", font_size="22px", font_weight="800", color=rx.color("slate", 12)),
                    rx.text("/ ₹20,000", font_size="14px", font_weight="600", color=rx.color("slate", 10)),
                    align="baseline",
                    spacing="1",
                ),
                rx.progress(value=100, color_scheme="green", size="3", radius="full", width="100%"),
                spacing="2",
                width="100%",
            ),
            # Reward detail box
            rx.box(
                rx.hstack(
                    rx.vstack(
                        rx.text("Reward Claimed", font_size="11px", color=rx.color("slate", 10), font_weight="500"),
                        rx.text("₹1,000 Amazon Voucher", font_size="13.5px", font_weight="700", color=GREEN_ACCENT),
                        spacing="0",
                        align_items="start",
                    ),
                    rx.badge("Eligible & Processed", variant="soft", color_scheme="green", radius="full", font_size="10.5px"),
                    justify="between",
                    align="center",
                    width="100%",
                ),
                style=SUB_BOX_STYLE,
                width="100%",
            ),
            spacing="3",
            align_items="start",
            width="100%",
        ),
        style=CARD_STYLE,
    )


def hsbc_fee_waiver_card() -> rx.Component:
    """Milestone 2: Annual Fee Waiver (₹2,00,000 spend)."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.box(
                        rx.icon("shield-check", size=18, color=HSBC_RED),
                        background_color=HSBC_RED_BG,
                        border=f"1px solid {HSBC_RED_BORDER}",
                        border_radius="8px",
                        padding="6px",
                    ),
                    rx.vstack(
                        rx.text("Annual Fee Waiver", font_size="12px", font_weight="600", color=rx.color("slate", 11)),
                        rx.text("₹2,00,000 Milestone", font_size="14.5px", font_weight="700"),
                        spacing="0",
                        align_items="start",
                    ),
                    align="center",
                    spacing="2",
                ),
                rx.badge("Save ₹999 + GST", variant="surface", color_scheme="ruby", radius="full", font_size="11px"),
                justify="between",
                align="center",
                width="100%",
            ),
            # Spend progress
            rx.vstack(
                rx.hstack(
                    rx.text(DCBMState.hsbc_formatted_lifetime_spend, font_size="22px", font_weight="800", color=rx.color("slate", 12)),
                    rx.text("/ ₹2,00,000", font_size="14px", font_weight="600", color=rx.color("slate", 10)),
                    align="baseline",
                    spacing="1",
                ),
                rx.progress(value=DCBMState.hsbc_fee_percent, color_scheme="ruby", size="3", radius="full", width="100%"),
                spacing="2",
                width="100%",
            ),
            # Waiver pace details
            rx.box(
                rx.hstack(
                    rx.vstack(
                        rx.text("Remaining Spend", font_size="11px", color=rx.color("slate", 10), font_weight="500"),
                        rx.text(DCBMState.hsbc_formatted_fee_remaining, font_size="13px", font_weight="700"),
                        spacing="0",
                        align_items="start",
                    ),
                    rx.divider(orientation="vertical", size="2"),
                    rx.vstack(
                        rx.text("Required Pace", font_size="11px", color=rx.color("slate", 10), font_weight="500"),
                        rx.text(f"₹{DCBMState.hsbc_fee_run_rate:.0f}/day ({DCBMState.hsbc_fee_days_left}d left)", font_size="13px", font_weight="600", color=rx.color("slate", 11)),
                        spacing="0",
                        align_items="start",
                    ),
                    justify="between",
                    align="center",
                    width="100%",
                ),
                style=SUB_BOX_STYLE,
                width="100%",
            ),
            spacing="3",
            align_items="start",
            width="100%",
        ),
        style=CARD_STYLE,
    )


def hsbc_lounge_card() -> rx.Component:
    """Milestone 3: Lounge and Premium Travel Perks."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.box(
                        rx.icon("plane", size=18, color=HSBC_RED),
                        background_color=HSBC_RED_BG,
                        border=f"1px solid {HSBC_RED_BORDER}",
                        border_radius="8px",
                        padding="6px",
                    ),
                    rx.vstack(
                        rx.text("Travel & Lifestyle", font_size="12px", font_weight="600", color=rx.color("slate", 11)),
                        rx.text("Airport Lounges & Perks", font_size="14.5px", font_weight="700"),
                        spacing="0",
                        align_items="start",
                    ),
                    align="center",
                    spacing="2",
                ),
                rx.badge("Complimentary", variant="surface", color_scheme="ruby", radius="full", font_size="11px"),
                justify="between",
                align="center",
                width="100%",
            ),
            # Perk list
            rx.vstack(
                rx.hstack(
                    rx.text("Domestic Airport Lounge (H2):", font_size="12.5px", color=rx.color("slate", 11)),
                    rx.badge(DCBMState.hsbc_lounge_domestic, variant="surface", color_scheme="green", radius="full", font_size="11px"),
                    justify="between",
                    width="100%",
                ),
                rx.hstack(
                    rx.text("International Lounge:", font_size="12.5px", color=rx.color("slate", 11)),
                    rx.badge(DCBMState.hsbc_lounge_international, variant="surface", color_scheme="green", radius="full", font_size="11px"),
                    justify="between",
                    width="100%",
                ),
                rx.hstack(
                    rx.text("International Roaming eSIM:", font_size="12.5px", color=rx.color("slate", 11)),
                    rx.badge(DCBMState.hsbc_lounge_esim, variant="surface", color_scheme="ruby", radius="full", font_size="11px"),
                    justify="between",
                    width="100%",
                ),
                spacing="2",
                width="100%",
            ),
            # Dining perk note
            rx.box(
                rx.hstack(
                    rx.text("🍽️ Live+ Dining Program:", font_size="11.5px", font_weight="600"),
                    rx.text("Up to 15% discount across partner dining venues nationwide", font_size="11px", color=rx.color("slate", 11)),
                    spacing="1",
                    align="center",
                    wrap="wrap",
                ),
                style=SUB_BOX_STYLE,
                width="100%",
            ),
            spacing="3",
            align_items="start",
            width="100%",
        ),
        style=CARD_STYLE,
    )


def hsbc_milestones_section() -> rx.Component:
    """Milestones grid for HSBC Live+."""
    return rx.grid(
        hsbc_welcome_card(),
        hsbc_fee_waiver_card(),
        hsbc_lounge_card(),
        columns=rx.breakpoints(initial="1", md="3"),
        spacing="4",
        width="100%",
    )
