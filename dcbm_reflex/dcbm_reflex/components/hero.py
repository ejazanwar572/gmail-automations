"""Hero Section with 3 Bento Cards for Cap, Headroom, and Portfolio value."""

import reflex as rx
from dcbm_reflex.state import DCBMState
from dcbm_reflex.styles import CARD_STYLE, HERO_CARD_STYLE, SUB_BOX_STYLE, GOLD_ACCENT


def cap_card() -> rx.Component:
    """Card 1: Monthly 10,000 Accelerated Cap Monitor."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.text(
                        "Accelerated Reward Points Limit",
                        font_size="11px",
                        font_weight="700",
                        text_transform="uppercase",
                        letter_spacing="0.06em",
                        color=GOLD_ACCENT,
                    ),
                    rx.text(
                        DCBMState.cycle_title,
                        font_size="17px",
                        font_weight="700",
                    ),
                    spacing="0",
                    align_items="start",
                ),
                rx.badge(
                    f"⏳ Resets in {DCBMState.days_remaining} days",
                    variant="surface",
                    color_scheme="amber",
                    radius="full",
                    font_size="11.5px",
                ),
                justify="between",
                width="100%",
                align="start",
            ),
            rx.box(
                rx.hstack(
                    rx.text(
                        DCBMState.cap_remaining,
                        font_size="38px",
                        font_weight="800",
                        letter_spacing="-0.03em",
                        line_height="1",
                    ),
                    rx.text(
                        f"/ {DCBMState.monthly_cap} RP remaining",
                        font_size="15px",
                        font_weight="600",
                        color=rx.color("slate", 11),
                    ),
                    align="baseline",
                    spacing="2",
                ),
                rx.text(
                    f"{DCBMState.cap_percent_remaining}% of monthly cap still available to earn",
                    font_size="12.5px",
                    color=rx.color("slate", 10),
                    margin_top="4px",
                ),
                margin_y="12px",
            ),
            rx.vstack(
                rx.hstack(
                    rx.text(
                        f"Monthly Progress: {DCBMState.cap_earned} / {DCBMState.monthly_cap} RP",
                        font_size="12px",
                        font_weight="600",
                        color=rx.color("slate", 11),
                    ),
                    rx.text(
                        f"Today: {DCBMState.today_earned} / {DCBMState.today_cap} RP",
                        font_size="12px",
                        font_weight="600",
                        color=rx.color("slate", 11),
                    ),
                    justify="between",
                    width="100%",
                ),
                rx.progress(
                    value=DCBMState.cap_percent_used,
                    color_scheme="amber",
                    radius="full",
                    size="2",
                    width="100%",
                ),
                spacing="2",
                width="100%",
            ),
            justify="between",
            height="100%",
            width="100%",
            spacing="3",
        ),
        style=HERO_CARD_STYLE,
        flex="1.3",
    )


def headroom_card() -> rx.Component:
    """Card 2: Spend headroom before hitting cap."""
    return rx.box(
        rx.vstack(
            rx.vstack(
                rx.text(
                    "Remaining Spend Headroom",
                    font_size="11px",
                    font_weight="700",
                    text_transform="uppercase",
                    letter_spacing="0.06em",
                    color=rx.color("slate", 11),
                ),
                rx.text(
                    "Spend buffer before hitting 10,000 RP cap",
                    font_size="13px",
                    color=rx.color("slate", 10),
                ),
                spacing="0",
                align_items="start",
            ),
            rx.vstack(
                # Flights Headroom
                rx.box(
                    rx.hstack(
                        rx.vstack(
                            rx.text(
                                "✈️ SmartBuy Flights (5X)",
                                font_size="12px",
                                font_weight="600",
                                color=rx.color("slate", 11),
                            ),
                            rx.text(
                                DCBMState.formatted_flight_capacity,
                                font_size="19px",
                                font_weight="800",
                                color=GOLD_ACCENT,
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        rx.text(
                            "4X bonus\n(20 RP / ₹150)",
                            font_size="11px",
                            color=rx.color("slate", 10),
                            text_align="right",
                        ),
                        justify="between",
                        align="center",
                        width="100%",
                    ),
                    style=SUB_BOX_STYLE,
                    width="100%",
                ),
                # Hotels Headroom
                rx.box(
                    rx.hstack(
                        rx.vstack(
                            rx.text(
                                "🏨 SmartBuy Hotels (10X)",
                                font_size="12px",
                                font_weight="600",
                                color=rx.color("slate", 11),
                            ),
                            rx.text(
                                DCBMState.formatted_hotel_capacity,
                                font_size="19px",
                                font_weight="800",
                                color="#784708",
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        rx.text(
                            "9X bonus\n(45 RP / ₹150)",
                            font_size="11px",
                            color=rx.color("slate", 10),
                            text_align="right",
                        ),
                        justify="between",
                        align="center",
                        width="100%",
                    ),
                    style=SUB_BOX_STYLE,
                    width="100%",
                ),
                spacing="2",
                width="100%",
            ),
            justify="between",
            height="100%",
            width="100%",
            spacing="3",
        ),
        style=CARD_STYLE,
        flex="1.1",
    )


def portfolio_card() -> rx.Component:
    """Card 3: Net points balance & reward rate."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.text(
                        "Reward Points Details",
                        font_size="11px",
                        font_weight="700",
                        text_transform="uppercase",
                        letter_spacing="0.06em",
                        color=rx.color("slate", 11),
                    ),
                    rx.text(
                        "Net Balance & Portfolio Value",
                        font_size="13px",
                        color=rx.color("slate", 10),
                    ),
                    spacing="0",
                    align_items="start",
                ),
                rx.badge(
                    "1 RP = ₹1.00",
                    variant="surface",
                    color_scheme="green",
                    radius="full",
                    font_size="11px",
                    font_weight="700",
                ),
                justify="between",
                width="100%",
                align="start",
            ),
            rx.vstack(
                # Lifetime Points
                rx.box(
                    rx.hstack(
                        rx.vstack(
                            rx.text("Lifetime RP", font_size="11px", font_weight="700", color=rx.color("slate", 11)),
                            rx.text("Total earned to date", font_size="10.5px", color=rx.color("slate", 10)),
                            spacing="0",
                            align_items="start",
                        ),
                        rx.text(f"{DCBMState.lifetime_earned} RP", font_size="16px", font_weight="800", color=GOLD_ACCENT),
                        justify="between",
                        align="center",
                        width="100%",
                    ),
                    style=SUB_BOX_STYLE,
                    width="100%",
                ),
                # Current Available
                rx.box(
                    rx.hstack(
                        rx.vstack(
                            rx.text("Available Balance", font_size="11px", font_weight="700", color=rx.color("slate", 11)),
                            rx.text(f"Worth ₹{DCBMState.current_available} on SmartBuy", font_size="10.5px", color=rx.color("slate", 10)),
                            spacing="0",
                            align_items="start",
                        ),
                        rx.text(f"{DCBMState.current_available} RP", font_size="16px", font_weight="800", color="#b45309"),
                        justify="between",
                        align="center",
                        width="100%",
                    ),
                    style=SUB_BOX_STYLE,
                    width="100%",
                ),
                # Reward Rate
                rx.box(
                    rx.hstack(
                        rx.vstack(
                            rx.text("My Reward Rate", font_size="11px", font_weight="700", color=rx.color("slate", 11)),
                            rx.text("Realized points return", font_size="10.5px", color=rx.color("slate", 10)),
                            spacing="0",
                            align_items="start",
                        ),
                        rx.text(f"{DCBMState.lifetime_reward_rate}%", font_size="16px", font_weight="800", color="#15803d"),
                        justify="between",
                        align="center",
                        width="100%",
                    ),
                    style=SUB_BOX_STYLE,
                    width="100%",
                ),
                spacing="2",
                width="100%",
            ),
            justify="between",
            height="100%",
            width="100%",
            spacing="3",
        ),
        style=CARD_STYLE,
        flex="1.2",
    )


def hero_section() -> rx.Component:
    """Combine the 3 hero cards into a responsive grid."""
    return rx.flex(
        cap_card(),
        headroom_card(),
        portfolio_card(),
        gap="4",
        direction=rx.breakpoints(initial="column", md="row"),
        width="100%",
    )
