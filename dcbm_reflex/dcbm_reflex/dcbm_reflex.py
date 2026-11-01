"""Main application entry point for Multi-Card Reflex Control Center."""

import reflex as rx

from dcbm_reflex.components.footer import footer
from dcbm_reflex.components.header import header_bar
from dcbm_reflex.components.hero import hero_section
from dcbm_reflex.components.milestones import milestones_section
from dcbm_reflex.components.tabs import tabs_section
from dcbm_reflex.components.hsbc_hero import hsbc_hero_section
from dcbm_reflex.components.hsbc_milestones import hsbc_milestones_section
from dcbm_reflex.components.hsbc_tabs import hsbc_tabs_section
from dcbm_reflex.state import DCBMState


def index() -> rx.Component:
    """Dashboard homepage with dynamic multi-card switching."""
    return rx.box(
        rx.box(
            rx.vstack(
                header_bar(),
                rx.cond(
                    DCBMState.active_card == "HDFC",
                    rx.vstack(
                        hero_section(),
                        milestones_section(),
                        tabs_section(),
                        spacing="5",
                        width="100%",
                    ),
                    rx.vstack(
                        hsbc_hero_section(),
                        hsbc_milestones_section(),
                        hsbc_tabs_section(),
                        spacing="5",
                        width="100%",
                    ),
                ),
                footer(),
                spacing="5",
                width="100%",
            ),
            width="100%",
            max_width="1600px",
            margin_x="auto",
            padding_x=rx.breakpoints(initial="12px", sm="20px", md="32px", lg="40px"),
            padding_y="24px",
        ),
        background=rx.color_mode_cond(
            light="radial-gradient(ellipse 75% 35% at 50% -5%, rgba(217, 119, 6, 0.05), transparent 70%), #f8fafc",
            dark="radial-gradient(ellipse 75% 35% at 50% -5%, rgba(217, 119, 6, 0.09), transparent 70%), #0b0f19",
        ),
        min_height="100vh",
        width="100%",
    )


# Configure Reflex App
app = rx.App()

app.add_page(
    index,
    route="/",
    title="Premium Cards Control Center | HDFC DCBM & HSBC Live+",
    on_load=DCBMState.load_data,
)

