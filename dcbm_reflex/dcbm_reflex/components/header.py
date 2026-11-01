"""Top Header navigation bar for Multi-Card Reflex Control Center."""

import reflex as rx
from dcbm_reflex.state import DCBMState
from dcbm_reflex.styles import (
    GOLD_ACCENT,
    GOLD_BG,
    GOLD_BORDER,
    HEADER_STYLE,
    HSBC_RED,
    HSBC_RED_BG,
    HSBC_RED_BORDER,
)


def header_bar() -> rx.Component:
    """Header bar with card account switcher, live status, and sync trigger."""
    return rx.box(
        rx.hstack(
            # Left brand & account indicator
            rx.hstack(
                rx.cond(
                    DCBMState.active_card == "HDFC",
                    rx.box(
                        rx.icon("credit-card", size=22, color=GOLD_ACCENT),
                        background_color=GOLD_BG,
                        border=f"1px solid {GOLD_BORDER}",
                        border_radius="12px",
                        padding="10px",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                        box_shadow="0 2px 8px rgba(180, 120, 32, 0.12)",
                    ),
                    rx.box(
                        rx.icon("credit-card", size=22, color=HSBC_RED),
                        background_color=HSBC_RED_BG,
                        border=f"1px solid {HSBC_RED_BORDER}",
                        border_radius="12px",
                        padding="10px",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                        box_shadow="0 2px 8px rgba(225, 29, 72, 0.12)",
                    ),
                ),
                rx.vstack(
                    rx.hstack(
                        rx.cond(
                            DCBMState.active_card == "HDFC",
                            rx.hstack(
                                rx.text(
                                    DCBMState.card_name,
                                    font_weight="800",
                                    font_size="17px",
                                    letter_spacing="-0.02em",
                                    color=rx.color("slate", 12),
                                ),
                                rx.badge(
                                    DCBMState.card_ending,
                                    variant="surface",
                                    color_scheme="amber",
                                    radius="full",
                                    font_weight="600",
                                ),
                                rx.badge(
                                    "Metal Edition",
                                    variant="soft",
                                    color_scheme="amber",
                                    radius="full",
                                    font_weight="600",
                                ),
                                align="center",
                                spacing="2",
                            ),
                            rx.hstack(
                                rx.text(
                                    DCBMState.hsbc_card_name,
                                    font_weight="800",
                                    font_size="17px",
                                    letter_spacing="-0.02em",
                                    color=rx.color("slate", 12),
                                ),
                                rx.badge(
                                    DCBMState.hsbc_card_ending,
                                    variant="surface",
                                    color_scheme="ruby",
                                    radius="full",
                                    font_weight="600",
                                ),
                                rx.badge(
                                    "Visa Platinum",
                                    variant="soft",
                                    color_scheme="ruby",
                                    radius="full",
                                    font_weight="600",
                                ),
                                align="center",
                                spacing="2",
                            ),
                        ),
                        align="center",
                    ),
                    rx.text(
                        "Automated Real-Time Rewards & Spend Tracker from Gmail Alerts",
                        font_size="12px",
                        color=rx.color("slate", 11),
                        font_weight="500",
                    ),
                    spacing="1",
                    align_items="start",
                ),
                align="center",
                spacing="3",
            ),
            # Center: Card Switcher Segmented Control
            rx.box(
                rx.segmented_control.root(
                    rx.segmented_control.item("💳 HDFC Diners Metal", value="HDFC"),
                    rx.segmented_control.item("💳 HSBC Live+", value="HSBC"),
                    value=DCBMState.active_card,
                    on_change=DCBMState.set_active_card,
                    radius="full",
                    size="2",
                ),
            ),
            # Right actions: theme toggle, sync badge, sync button
            rx.hstack(
                rx.badge(
                    rx.hstack(
                        rx.box(
                            width="7px",
                            height="7px",
                            border_radius="full",
                            background_color="#10b981",
                        ),
                        rx.text(
                            rx.cond(
                                DCBMState.active_card == "HDFC",
                                f"● {DCBMState.last_synced}",
                                f"● {DCBMState.hsbc_last_synced}",
                            ),
                            font_size="11.5px",
                            font_weight="700",
                        ),
                        align="center",
                        spacing="1",
                    ),
                    variant="surface",
                    color_scheme="green",
                    radius="full",
                    padding_x="12px",
                    padding_y="5px",
                ),
                rx.button(
                    rx.icon("refresh-cw", size=14),
                    "Sync",
                    loading=rx.cond(
                        DCBMState.active_card == "HDFC",
                        DCBMState.is_syncing,
                        DCBMState.hsbc_is_syncing,
                    ),
                    on_click=DCBMState.trigger_current_sync,
                    color_scheme=rx.cond(DCBMState.active_card == "HDFC", "amber", "ruby"),
                    variant="solid",
                    radius="full",
                    size="2",
                    cursor="pointer",
                    font_weight="600",
                ),
                rx.color_mode.button(radius="full", size="2"),
                align="center",
                spacing="3",
            ),
            justify="between",
            align="center",
            width="100%",
            wrap="wrap",
            gap="3",
        ),
        style=HEADER_STYLE,
    )
