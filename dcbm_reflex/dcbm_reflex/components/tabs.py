"""Interactive Tabs section: Live Transactions, Monthly History, and Points Redemptions."""

import reflex as rx
from dcbm_reflex.state import DCBMState, TxItem, MonthHistoryItem, RedemptionItem
from dcbm_reflex.styles import CARD_STYLE, SUB_BOX_STYLE, GOLD_ACCENT, GREEN_ACCENT, AMBER_ACCENT


def render_tx_row(tx: TxItem) -> rx.Component:
    """Render a single transaction row in the Radix Table."""
    return rx.table.row(
        rx.table.cell(rx.text(tx.date, font_size="13px", color=rx.color("slate", 11))),
        rx.table.cell(
            rx.vstack(
                rx.text(tx.merchant, font_weight="600", font_size="13.5px"),
                rx.cond(
                    tx.description != "",
                    rx.text(tx.description, font_size="11px", color=rx.color("slate", 10)),
                    rx.fragment(),
                ),
                spacing="0",
                align_items="start",
            )
        ),
        rx.table.cell(
            rx.badge(
                f"{tx.icon} {tx.category}",
                variant="surface",
                color_scheme=rx.cond(tx.is_smartbuy, "amber", "gray"),
                radius="medium",
                font_size="11px",
            )
        ),
        rx.table.cell(rx.text(tx.formatted_amount, font_weight="700", font_size="13.5px")),
        rx.table.cell(rx.text(f"{tx.base_points} RP", font_size="13px", color=rx.color("slate", 11))),
        rx.table.cell(
            rx.cond(
                tx.raw_accelerated_points > 0,
                rx.badge(f"+{tx.raw_accelerated_points} RP", color_scheme="amber", radius="full", font_size="11px"),
                rx.text("-", color=rx.color("slate", 9), font_size="13px"),
            )
        ),
        rx.table.cell(rx.text(f"{tx.total_points} RP", font_weight="700", font_size="13.5px", color=GREEN_ACCENT)),
        rx.table.cell(
            rx.badge(
                f"{tx.multiplier}X ({tx.reward_rate}%)",
                variant="soft",
                color_scheme=rx.cond(tx.multiplier > 1, "green", "gray"),
                radius="full",
                font_size="11px",
            )
        ),
        align="center",
    )


def transactions_tab() -> rx.Component:
    """Tab 1: Live Transactions with search, category pills, and ledger."""
    return rx.vstack(
        # Filter controls
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.input(
                        rx.input.slot(rx.icon("search", size=16)),
                        placeholder="Search merchant or note...",
                        value=DCBMState.search_query,
                        on_change=DCBMState.set_search_query,
                        size="2",
                        radius="medium",
                        flex="2",
                    ),
                    rx.select(
                        DCBMState.period_options,
                        value=DCBMState.selected_period,
                        on_change=DCBMState.set_period,
                        size="2",
                        radius="medium",
                        flex="1.2",
                    ),
                    width="100%",
                    spacing="3",
                ),
                # Category Pills
                rx.hstack(
                    rx.text("Category:", font_size="12px", font_weight="600", color=rx.color("slate", 11)),
                    rx.hstack(
                        rx.foreach(
                            DCBMState.categories,
                            lambda cat: rx.button(
                                cat,
                                variant=rx.cond(DCBMState.selected_category == cat, "solid", "surface"),
                                color_scheme="amber",
                                size="1",
                                radius="full",
                                cursor="pointer",
                                on_click=DCBMState.set_category(cat),
                            ),
                        ),
                        wrap="wrap",
                        spacing="2",
                    ),
                    align="center",
                    spacing="2",
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),
            style=SUB_BOX_STYLE,
            width="100%",
            margin_bottom="12px",
        ),
        # Summary Metric Chips
        rx.hstack(
            rx.badge(f"COUNT: {DCBMState.filtered_count}", variant="surface", color_scheme="gray", radius="medium", padding="6px 12px", font_size="12px"),
            rx.badge(f"SPEND: {DCBMState.filtered_spend_formatted}", variant="surface", color_scheme="amber", radius="medium", padding="6px 12px", font_size="12px", font_weight="700"),
            rx.badge(f"BASE RP: {DCBMState.filtered_base_rp} RP", variant="surface", color_scheme="gray", radius="medium", padding="6px 12px", font_size="12px"),
            rx.badge(f"ACCELERATED RP: {DCBMState.filtered_acc_rp} RP", variant="surface", color_scheme="amber", radius="medium", padding="6px 12px", font_size="12px"),
            rx.badge(f"TOTAL RP: {DCBMState.filtered_total_rp} RP", variant="surface", color_scheme="green", radius="medium", padding="6px 12px", font_size="12px", font_weight="700"),
            wrap="wrap",
            spacing="2",
            margin_bottom="8px",
        ),
        # Transactions Table
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Date"),
                        rx.table.column_header_cell("Merchant / Description"),
                        rx.table.column_header_cell("Category"),
                        rx.table.column_header_cell("Amount"),
                        rx.table.column_header_cell("Base RP"),
                        rx.table.column_header_cell("Accelerated RP"),
                        rx.table.column_header_cell("Total RP"),
                        rx.table.column_header_cell("Multiplier"),
                    )
                ),
                rx.table.body(
                    rx.foreach(DCBMState.filtered_transactions, render_tx_row)
                ),
                variant="surface",
                size="2",
                width="100%",
            ),
            border_radius="12px",
            overflow="hidden",
            border=f"1px solid {rx.color('slate', 5)}",
            width="100%",
        ),
        spacing="3",
        width="100%",
    )


def render_history_row(h: MonthHistoryItem) -> rx.Component:
    """Render a monthly history row in the Radix Table."""
    return rx.table.row(
        rx.table.cell(rx.text(h.label, font_weight="700", font_size="13.5px")),
        rx.table.cell(rx.text(h.formatted_spend, font_weight="600", font_size="13px")),
        rx.table.cell(rx.text(f"{h.base_points:,} RP", font_size="13px", color=rx.color("slate", 11))),
        rx.table.cell(rx.text(f"{h.accelerated_points:,} RP", font_size="13px", color=AMBER_ACCENT, font_weight="600")),
        rx.table.cell(
            rx.hstack(
                rx.progress(value=h.cap_percent_used, color_scheme="amber", radius="full", width="70px"),
                rx.text(f"{h.cap_percent_used_float:.1f}%", font_size="11.5px", font_weight="600"),
                align="center",
                spacing="2",
            )
        ),
        rx.table.cell(rx.text(f"{h.accelerated_remaining:,} RP", font_size="13px", color=rx.color("slate", 11))),
        rx.table.cell(rx.text(f"{h.total_points:,} RP", font_weight="700", font_size="13.5px", color=GREEN_ACCENT)),
        rx.table.cell(rx.text(h.formatted_value, font_weight="600", font_size="13px")),
        rx.table.cell(rx.badge(h.smartbuy_txs, variant="soft", color_scheme="amber", radius="full", font_size="11px")),
        align="center",
    )


def history_tab() -> rx.Component:
    """Tab 2: Historical Monthly Reward Points & SmartBuy Cap Utilization."""
    return rx.vstack(
        rx.text(
            "Historical Monthly Reward Points & SmartBuy Cap Utilization",
            font_size="14px",
            font_weight="600",
            color=rx.color("slate", 11),
            margin_bottom="8px",
        ),
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Month"),
                        rx.table.column_header_cell("Total Spend"),
                        rx.table.column_header_cell("Base RP"),
                        rx.table.column_header_cell("Accelerated RP"),
                        rx.table.column_header_cell("10k Cap Used"),
                        rx.table.column_header_cell("Cap Left"),
                        rx.table.column_header_cell("Total Earned"),
                        rx.table.column_header_cell("SmartBuy Value"),
                        rx.table.column_header_cell("SmartBuy Txs"),
                    )
                ),
                rx.table.body(
                    rx.foreach(DCBMState.monthly_history, render_history_row)
                ),
                variant="surface",
                size="2",
                width="100%",
            ),
            border_radius="12px",
            overflow="hidden",
            border=f"1px solid {rx.color('slate', 5)}",
            width="100%",
        ),
        spacing="3",
        width="100%",
    )


def render_redemption_row(r: RedemptionItem) -> rx.Component:
    """Render a redemption row in the Radix Table."""
    return rx.table.row(
        rx.table.cell(rx.text(r.date, font_size="13px", color=rx.color("slate", 11))),
        rx.table.cell(rx.badge(r.type, color_scheme="amber", radius="medium", font_size="11px")),
        rx.table.cell(rx.text(r.description, font_weight="600", font_size="13px")),
        rx.table.cell(rx.code(r.order_reference, font_size="11.5px")),
        rx.table.cell(rx.text(f"{r.points_redeemed:,} RP", font_weight="700", color=AMBER_ACCENT, font_size="13.5px")),
        rx.table.cell(rx.text(r.formatted_cash, font_size="13px", color=GOLD_ACCENT, font_weight="600")),
        rx.table.cell(rx.text(r.formatted_fare, font_size="13px", font_weight="600")),
        rx.table.cell(rx.text(r.formatted_saved, font_size="13.5px", font_weight="800", color=GREEN_ACCENT)),
        rx.table.cell(rx.badge(f"₹{r.redemption_rate:.2f}/pt", color_scheme="green", radius="full", font_size="11px")),
        align="center",
    )


def redemptions_tab() -> rx.Component:
    """Tab 3: SmartBuy Points Redemptions."""
    return rx.vstack(
        # Summary Header Banner
        rx.box(
            rx.flex(
                rx.vstack(
                    rx.text("Points Burned", font_size="10.5px", font_weight="700", text_transform="uppercase", color=rx.color("slate", 10)),
                    rx.text(f"{DCBMState.total_pts_burned:,} RP", font_size="18px", font_weight="800", color=AMBER_ACCENT),
                    spacing="0",
                    align_items="start",
                ),
                rx.vstack(
                    rx.text("Direct Savings", font_size="10.5px", font_weight="700", text_transform="uppercase", color=rx.color("slate", 10)),
                    rx.text(DCBMState.formatted_savings, font_size="18px", font_weight="800", color=GREEN_ACCENT),
                    spacing="0",
                    align_items="start",
                ),
                rx.vstack(
                    rx.text("Total Booking Value", font_size="10.5px", font_weight="700", text_transform="uppercase", color=rx.color("slate", 10)),
                    rx.text(DCBMState.formatted_booking_val, font_size="18px", font_weight="800"),
                    spacing="0",
                    align_items="start",
                ),
                rx.vstack(
                    rx.text("Cash Paid (DCBM)", font_size="10.5px", font_weight="700", text_transform="uppercase", color=rx.color("slate", 10)),
                    rx.text(DCBMState.formatted_cash_paid, font_size="18px", font_weight="800", color=GOLD_ACCENT),
                    spacing="0",
                    align_items="start",
                ),
                justify="between",
                align="center",
                width="100%",
                gap="4",
            ),
            style=SUB_BOX_STYLE,
            width="100%",
            margin_bottom="12px",
        ),
        # Redemptions Table
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Date"),
                        rx.table.column_header_cell("Category"),
                        rx.table.column_header_cell("Booking Description"),
                        rx.table.column_header_cell("Order Reference #"),
                        rx.table.column_header_cell("Points Burned"),
                        rx.table.column_header_cell("Cash Paid (DCBM)"),
                        rx.table.column_header_cell("Booking Value"),
                        rx.table.column_header_cell("Value Saved"),
                        rx.table.column_header_cell("Redemption Rate"),
                    )
                ),
                rx.table.body(
                    rx.foreach(DCBMState.redemptions, render_redemption_row)
                ),
                variant="surface",
                size="2",
                width="100%",
            ),
            border_radius="12px",
            overflow="hidden",
            border=f"1px solid {rx.color('slate', 5)}",
            width="100%",
        ),
        spacing="3",
        width="100%",
    )


def tabs_section() -> rx.Component:
    """Tabs section containing Transactions, History, and Redemptions."""
    return rx.box(
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger(
                    rx.hstack(rx.icon("receipt-text", size=15), rx.text("Live Transactions")),
                    value="transactions",
                ),
                rx.tabs.trigger(
                    rx.hstack(rx.icon("bar-chart-3", size=15), rx.text("Monthly History & Caps")),
                    value="history",
                ),
                rx.tabs.trigger(
                    rx.hstack(rx.icon("ticket", size=15), rx.text("Points Redemptions")),
                    value="redemptions",
                ),
                size="2",
            ),
            rx.tabs.content(transactions_tab(), value="transactions", padding_top="16px"),
            rx.tabs.content(history_tab(), value="history", padding_top="16px"),
            rx.tabs.content(redemptions_tab(), value="redemptions", padding_top="16px"),
            default_value="transactions",
            width="100%",
        ),
        style=CARD_STYLE,
        width="100%",
    )
