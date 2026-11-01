"""Hero section with Bento Grid metrics for HSBC Live+ dashboard."""

import reflex as rx
from dcbm_reflex.state import DCBMState
from dcbm_reflex.styles import HSBC_HERO_CARD_STYLE, HSBC_RED, HSBC_RED_BG, HSBC_RED_BORDER, SUB_BOX_STYLE, GREEN_ACCENT


def hsbc_cap_card() -> rx.Component:
    """Card 1: Monthly 10% Accelerated Cashback Cap."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.box(
                        rx.icon("wallet", size=18, color=HSBC_RED),
                        background_color=HSBC_RED_BG,
                        border=f"1px solid {HSBC_RED_BORDER}",
                        border_radius="8px",
                        padding="6px",
                    ),
                    rx.vstack(
                        rx.text("Monthly Accelerated Cap", font_size="12px", font_weight="600", color=rx.color("slate", 11)),
                        rx.text(DCBMState.hsbc_cycle_label, font_size="14.5px", font_weight="700"),
                        spacing="0",
                        align_items="start",
                    ),
                    align="center",
                    spacing="2",
                ),
                rx.badge(
                    DCBMState.hsbc_reset_str,
                    variant="surface",
                    color_scheme="ruby",
                    radius="full",
                    font_size="11.5px",
                ),
                justify="between",
                align="center",
                width="100%",
            ),
            # Big KPI
            rx.vstack(
                rx.hstack(
                    rx.text(
                        DCBMState.hsbc_formatted_cap_earned,
                        font_size="36px",
                        font_weight="800",
                        letter_spacing="-0.03em",
                        color=rx.color("slate", 12),
                    ),
                    rx.text("/ ₹1,200", font_size="18px", font_weight="600", color=rx.color("slate", 10)),
                    align="baseline",
                    spacing="2",
                ),
                rx.text(
                    f"{DCBMState.hsbc_cap_percent_used_float}% cap utilized (10% on Dining, Food Delivery & Grocery)",
                    font_size="12.5px",
                    color=rx.color("slate", 11),
                ),
                spacing="0",
                align_items="start",
                width="100%",
            ),
            # Progress bar
            rx.vstack(
                rx.progress(
                    value=DCBMState.hsbc_cap_percent_used,
                    color_scheme="ruby",
                    size="3",
                    radius="full",
                    width="100%",
                ),
                width="100%",
            ),
            # Sub-box stats
            rx.box(
                rx.hstack(
                    rx.vstack(
                        rx.text("Remaining 10% Cap", font_size="11px", color=rx.color("slate", 10), font_weight="500"),
                        rx.text(DCBMState.hsbc_formatted_cap_remaining, font_size="14.5px", font_weight="700", color=GREEN_ACCENT),
                        spacing="0",
                        align_items="start",
                    ),
                    rx.divider(orientation="vertical", size="2"),
                    rx.vstack(
                        rx.text("Total Cycle Cashback", font_size="11px", color=rx.color("slate", 10), font_weight="500"),
                        rx.text(DCBMState.hsbc_formatted_total_cb, font_size="14.5px", font_weight="700"),
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
            spacing="4",
            align_items="start",
            width="100%",
        ),
        style=HSBC_HERO_CARD_STYLE,
    )


def hsbc_headroom_card() -> rx.Component:
    """Card 2: 10% Accelerated Spend Headroom."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.box(
                        rx.icon("sparkles", size=18, color=HSBC_RED),
                        background_color=HSBC_RED_BG,
                        border=f"1px solid {HSBC_RED_BORDER}",
                        border_radius="8px",
                        padding="6px",
                    ),
                    rx.vstack(
                        rx.text("Spend Headroom", font_size="12px", font_weight="600", color=rx.color("slate", 11)),
                        rx.text("10% Category Capacity", font_size="14.5px", font_weight="700"),
                        spacing="0",
                        align_items="start",
                    ),
                    align="center",
                    spacing="2",
                ),
                rx.badge("Max ₹12k Spend", variant="surface", color_scheme="ruby", radius="full", font_size="11px"),
                justify="between",
                align="center",
                width="100%",
            ),
            # Big Capacity
            rx.vstack(
                rx.text(
                    DCBMState.hsbc_formatted_remaining_spend,
                    font_size="34px",
                    font_weight="800",
                    letter_spacing="-0.02em",
                    color=rx.color("slate", 12),
                ),
                rx.text(
                    f"Remaining 10% spend capacity before hitting ₹1,200 cap",
                    font_size="12.5px",
                    color=rx.color("slate", 11),
                ),
                spacing="0",
                align_items="start",
                width="100%",
            ),
            # Spend details
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.text("Accelerated Spend Utilized", font_size="12px", color=rx.color("slate", 11)),
                        rx.text(f"{DCBMState.hsbc_formatted_spent} / ₹12,000", font_size="12.5px", font_weight="700"),
                        justify="between",
                        width="100%",
                    ),
                    rx.text(
                        "Applies to Swiggy, Zomato, Blinkit, Zepto, and all grocery/dining merchants. Beyond ₹12k, spends automatically earn unlimited 1.5% cashback.",
                        font_size="11.5px",
                        color=rx.color("slate", 10),
                    ),
                    spacing="1",
                    width="100%",
                ),
                style=SUB_BOX_STYLE,
                width="100%",
            ),
            spacing="4",
            align_items="start",
            width="100%",
        ),
        style=HSBC_HERO_CARD_STYLE,
    )


def hsbc_portfolio_card() -> rx.Component:
    """Card 3: Net Realized Portfolio & Reward Rate."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.box(
                        rx.icon("trending-up", size=18, color=HSBC_RED),
                        background_color=HSBC_RED_BG,
                        border=f"1px solid {HSBC_RED_BORDER}",
                        border_radius="8px",
                        padding="6px",
                    ),
                    rx.vstack(
                        rx.text("Realized Value", font_size="12px", font_weight="600", color=rx.color("slate", 11)),
                        rx.text("Lifetime Direct Cashback", font_size="14.5px", font_weight="700"),
                        spacing="0",
                        align_items="start",
                    ),
                    align="center",
                    spacing="2",
                ),
                rx.badge("Direct Credit", variant="surface", color_scheme="green", radius="full", font_size="11px"),
                justify="between",
                align="center",
                width="100%",
            ),
            # Big Value
            rx.vstack(
                rx.text(
                    DCBMState.hsbc_formatted_lifetime_cb,
                    font_size="34px",
                    font_weight="800",
                    letter_spacing="-0.02em",
                    color=GREEN_ACCENT,
                ),
                rx.text(
                    "Direct statement credits automatically deducted from monthly bills",
                    font_size="12.5px",
                    color=rx.color("slate", 11),
                ),
                spacing="0",
                align_items="start",
                width="100%",
            ),
            # Spend & Return Rate
            rx.box(
                rx.hstack(
                    rx.vstack(
                        rx.text("Total Spend Tracked", font_size="11px", color=rx.color("slate", 10), font_weight="500"),
                        rx.text(DCBMState.hsbc_formatted_lifetime_spend, font_size="14.5px", font_weight="700"),
                        spacing="0",
                        align_items="start",
                    ),
                    rx.divider(orientation="vertical", size="2"),
                    rx.vstack(
                        rx.text("Effective Reward Rate", font_size="11px", color=rx.color("slate", 10), font_weight="500"),
                        rx.badge(
                            f"{DCBMState.hsbc_effective_reward_rate}% Return",
                            variant="surface",
                            color_scheme="green",
                            radius="full",
                            font_size="12px",
                            font_weight="700",
                        ),
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
            spacing="4",
            align_items="start",
            width="100%",
        ),
        style=HSBC_HERO_CARD_STYLE,
    )


def hsbc_hero_section() -> rx.Component:
    """Responsive 3-column Bento grid for HSBC Live+."""
    return rx.grid(
        hsbc_cap_card(),
        hsbc_headroom_card(),
        hsbc_portfolio_card(),
        columns=rx.breakpoints(initial="1", md="2", lg="3"),
        spacing="4",
        width="100%",
    )
