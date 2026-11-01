"""Interactive Transactions tab and ledger for HSBC Live+ dashboard."""

import reflex as rx
from dcbm_reflex.state import DCBMState, HSBCTxItem
from dcbm_reflex.styles import CARD_STYLE, GREEN_ACCENT, HSBC_CARD_STYLE, HSBC_RED, SUB_BOX_STYLE


def render_hsbc_tx_row(tx: HSBCTxItem) -> rx.Component:
    """Render a single HSBC transaction row in the Radix Table."""
    return rx.table.row(
        rx.table.cell(rx.text(tx.date, font_size="13px", color=rx.color("slate", 11))),
        rx.table.cell(
            rx.vstack(
                rx.text(tx.merchant, font_weight="600", font_size="13.5px"),
                rx.cond(
                    tx.source != "",
                    rx.text(tx.source, font_size="11px", color=rx.color("slate", 10)),
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
                color_scheme=rx.cond(tx.is_accelerated, "ruby", "gray"),
                radius="medium",
                font_size="11px",
            )
        ),
        rx.table.cell(rx.text(tx.formatted_amount, font_weight="700", font_size="13.5px")),
        rx.table.cell(
            rx.badge(
                f"MCC {tx.mcc}",
                variant="outline",
                color_scheme="gray",
                radius="medium",
                font_family="monospace",
                font_size="11px",
            )
        ),
        rx.table.cell(
            rx.badge(
                tx.rate,
                variant="soft",
                color_scheme=rx.cond(tx.is_accelerated, "green", "gray"),
                radius="full",
                font_size="11px",
                font_weight="700",
            )
        ),
        rx.table.cell(
            rx.text(
                tx.formatted_cashback,
                font_weight="700",
                font_size="13.5px",
                color=GREEN_ACCENT,
            )
        ),
        rx.table.cell(
            rx.badge(
                tx.evidence,
                variant="surface",
                color_scheme=rx.cond(tx.evidence == "confirmed", "green", "amber"),
                radius="full",
                font_size="10.5px",
            )
        ),
        align="center",
    )


def hsbc_tabs_section() -> rx.Component:
    """Live Transactions Ledger section for HSBC Live+."""
    return rx.box(
        rx.vstack(
            # Header with search and period filter
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.input(
                            rx.input.slot(rx.icon("search", size=16)),
                            placeholder="Search merchant (Swiggy, Blinkit, Royal Mart, MCC)...",
                            value=DCBMState.hsbc_search_query,
                            on_change=DCBMState.set_hsbc_search_query,
                            size="2",
                            radius="medium",
                            flex="2",
                        ),
                        rx.select(
                            DCBMState.hsbc_period_options,
                            value=DCBMState.hsbc_selected_period,
                            on_change=DCBMState.set_hsbc_period,
                            size="2",
                            radius="medium",
                            flex="1.2",
                        ),
                        width="100%",
                        spacing="3",
                    ),
                    # Category Filter Pills
                    rx.hstack(
                        rx.text("Category:", font_size="12px", font_weight="600", color=rx.color("slate", 11)),
                        rx.hstack(
                            rx.foreach(
                                DCBMState.hsbc_categories,
                                lambda cat: rx.button(
                                    cat,
                                    variant=rx.cond(DCBMState.hsbc_selected_category == cat, "solid", "surface"),
                                    color_scheme="ruby",
                                    size="1",
                                    radius="full",
                                    cursor="pointer",
                                    on_click=DCBMState.set_hsbc_category(cat),
                                ),
                            ),
                            wrap="wrap",
                            spacing="2",
                        ),
                        align="center",
                        spacing="2",
                        wrap="wrap",
                        width="100%",
                    ),
                    # Summary Metric Badges
                    rx.hstack(
                        rx.badge(
                            rx.hstack(
                                rx.text("Transactions:", font_size="11.5px", color=rx.color("slate", 11)),
                                rx.text(DCBMState.hsbc_filtered_count, font_weight="700", font_size="12px"),
                                spacing="1",
                            ),
                            variant="surface",
                            color_scheme="gray",
                            radius="full",
                            padding_x="10px",
                        ),
                        rx.badge(
                            rx.hstack(
                                rx.text("Spend:", font_size="11.5px", color=rx.color("slate", 11)),
                                rx.text(DCBMState.hsbc_filtered_spend_formatted, font_weight="700", font_size="12px"),
                                spacing="1",
                            ),
                            variant="surface",
                            color_scheme="gray",
                            radius="full",
                            padding_x="10px",
                        ),
                        rx.badge(
                            rx.hstack(
                                rx.text("Cashback Earned:", font_size="11.5px", color=rx.color("slate", 11)),
                                rx.text(DCBMState.hsbc_filtered_cashback_formatted, font_weight="700", font_size="12px", color=GREEN_ACCENT),
                                spacing="1",
                            ),
                            variant="surface",
                            color_scheme="green",
                            radius="full",
                            padding_x="10px",
                        ),
                        wrap="wrap",
                        spacing="2",
                    ),
                    spacing="3",
                    width="100%",
                ),
                style=SUB_BOX_STYLE,
                width="100%",
            ),
            # Transactions Table
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(rx.text("Date", font_weight="700", font_size="12.5px")),
                            rx.table.column_header_cell(rx.text("Merchant & Source", font_weight="700", font_size="12.5px")),
                            rx.table.column_header_cell(rx.text("Category", font_weight="700", font_size="12.5px")),
                            rx.table.column_header_cell(rx.text("Amount", font_weight="700", font_size="12.5px")),
                            rx.table.column_header_cell(rx.text("MCC Code", font_weight="700", font_size="12.5px")),
                            rx.table.column_header_cell(rx.text("Rate", font_weight="700", font_size="12.5px")),
                            rx.table.column_header_cell(rx.text("Cashback", font_weight="700", font_size="12.5px")),
                            rx.table.column_header_cell(rx.text("Verification", font_weight="700", font_size="12.5px")),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(DCBMState.hsbc_filtered_transactions, render_hsbc_tx_row)
                    ),
                    variant="surface",
                    size="2",
                    width="100%",
                ),
                overflow_x="auto",
                width="100%",
            ),
            spacing="4",
            width="100%",
        ),
        style=CARD_STYLE,
        width="100%",
    )
