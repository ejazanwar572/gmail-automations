"""Footer component for the DCBM Reflex dashboard."""

import reflex as rx


def footer() -> rx.Component:
    """Clean minimal footer."""
    return rx.box(
        rx.text(
            "HDFC Diners Club Black Metal Control Center • Reimagined with Reflex & Next.js • Built for Ejaz Anwar",
            font_size="12px",
            color=rx.color("slate", 10),
            text_align="center",
        ),
        padding_y="24px",
        border_top=f"1px solid {rx.color('slate', 4)}",
        width="100%",
        margin_top="30px",
    )
