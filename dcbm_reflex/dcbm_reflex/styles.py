"""Styling tokens and themes for the Modern Dual-Card Reflex Control Center."""

import reflex as rx

# Haute Metal Palette: Champagne Bronze Gold & Slate
GOLD_ACCENT = "#b47820"
GOLD_HOVER = "#925f12"
GOLD_BG = "rgba(180, 120, 32, 0.09)"
GOLD_BORDER = "rgba(180, 120, 32, 0.28)"

# Vibrant Emerald Accent
GREEN_ACCENT = "#059669"
GREEN_BG = "rgba(5, 150, 105, 0.09)"
GREEN_BORDER = "rgba(5, 150, 105, 0.25)"

# Amber Warning Accent
AMBER_ACCENT = "#d97706"
AMBER_BG = "rgba(217, 119, 6, 0.09)"
AMBER_BORDER = "rgba(217, 119, 6, 0.25)"

# HSBC Live+ Palette (Vibrant Crimson Ruby)
HSBC_RED = "#e11d48"
HSBC_RED_HOVER = "#be123c"
HSBC_RED_BG = "rgba(225, 29, 72, 0.09)"
HSBC_RED_BORDER = "rgba(225, 29, 72, 0.28)"

# Modern Floating Header Navbar Style
HEADER_STYLE = {
    "background_color": rx.color_mode_cond(light="#ffffff", dark=rx.color("slate", 1)),
    "border": rx.color_mode_cond(
        light="1px solid rgba(226, 232, 240, 0.9)",
        dark=f"1px solid {rx.color('slate', 4)}",
    ),
    "border_radius": "22px",
    "padding": "16px 24px",
    "box_shadow": rx.color_mode_cond(
        light="0 1px 3px 0 rgba(15, 23, 42, 0.03), 0 8px 20px -4px rgba(15, 23, 42, 0.05)",
        dark="0 4px 20px rgba(0, 0, 0, 0.35)",
    ),
    "width": "100%",
}

# Standard Modern Fintech Card Style (Linear / Stripe / Apple aesthetic)
CARD_STYLE = {
    "background_color": rx.color_mode_cond(light="#ffffff", dark=rx.color("slate", 1)),
    "border": rx.color_mode_cond(
        light="1px solid rgba(226, 232, 240, 0.9)",
        dark=f"1px solid {rx.color('slate', 4)}",
    ),
    "border_radius": "22px",
    "padding": "24px",
    "box_shadow": rx.color_mode_cond(
        light="0 1px 3px 0 rgba(15, 23, 42, 0.03), 0 10px 24px -4px rgba(15, 23, 42, 0.05)",
        dark="0 4px 20px rgba(0, 0, 0, 0.3)",
    ),
    "transition": "all 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
    "_hover": {
        "border_color": rx.color_mode_cond(light="rgba(203, 213, 225, 1)", dark=rx.color("slate", 6)),
        "box_shadow": rx.color_mode_cond(
            light="0 4px 6px -1px rgba(15, 23, 42, 0.04), 0 16px 32px -4px rgba(15, 23, 42, 0.08)",
            dark="0 8px 28px rgba(0, 0, 0, 0.45)",
        ),
        "transform": "translateY(-2px)",
    },
}

# HSBC Card Style
HSBC_CARD_STYLE = {
    "background_color": rx.color_mode_cond(light="#ffffff", dark=rx.color("slate", 1)),
    "border": rx.color_mode_cond(
        light="1px solid rgba(226, 232, 240, 0.9)",
        dark=f"1px solid {rx.color('slate', 4)}",
    ),
    "border_radius": "22px",
    "padding": "24px",
    "box_shadow": rx.color_mode_cond(
        light="0 1px 3px 0 rgba(15, 23, 42, 0.03), 0 10px 24px -4px rgba(15, 23, 42, 0.05)",
        dark="0 4px 20px rgba(0, 0, 0, 0.3)",
    ),
    "transition": "all 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
    "_hover": {
        "border_color": HSBC_RED_BORDER,
        "box_shadow": rx.color_mode_cond(
            light="0 4px 6px -1px rgba(15, 23, 42, 0.04), 0 16px 32px -4px rgba(225, 29, 72, 0.08)",
            dark="0 8px 28px rgba(225, 29, 72, 0.16)",
        ),
        "transform": "translateY(-2px)",
    },
}

# HDFC Hero Bento Card Style (Subtle Gold Sheen & Elevation)
HERO_CARD_STYLE = {
    "background_color": rx.color_mode_cond(light="#ffffff", dark=rx.color("slate", 1)),
    "border": rx.color_mode_cond(
        light="1px solid rgba(217, 119, 6, 0.28)",
        dark=f"1px solid {rx.color('amber', 6)}",
    ),
    "border_radius": "22px",
    "padding": "26px",
    "box_shadow": rx.color_mode_cond(
        light="0 2px 4px 0 rgba(15, 23, 42, 0.02), 0 12px 30px -4px rgba(217, 119, 6, 0.09)",
        dark="0 6px 24px rgba(217, 119, 6, 0.14)",
    ),
    "transition": "all 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
    "_hover": {
        "border_color": rx.color_mode_cond(light="rgba(217, 119, 6, 0.5)", dark=rx.color("amber", 8)),
        "box_shadow": rx.color_mode_cond(
            light="0 6px 14px -2px rgba(15, 23, 42, 0.04), 0 18px 40px -4px rgba(217, 119, 6, 0.14)",
            dark="0 10px 32px rgba(217, 119, 6, 0.22)",
        ),
        "transform": "translateY(-2px)",
    },
}

# HSBC Hero Bento Card Style (Subtle Ruby Sheen & Elevation)
HSBC_HERO_CARD_STYLE = {
    "background_color": rx.color_mode_cond(light="#ffffff", dark=rx.color("slate", 1)),
    "border": rx.color_mode_cond(
        light="1px solid rgba(225, 29, 72, 0.28)",
        dark=f"1px solid {rx.color('ruby', 6)}",
    ),
    "border_radius": "22px",
    "padding": "26px",
    "box_shadow": rx.color_mode_cond(
        light="0 2px 4px 0 rgba(15, 23, 42, 0.02), 0 12px 30px -4px rgba(225, 29, 72, 0.09)",
        dark="0 6px 24px rgba(225, 29, 72, 0.14)",
    ),
    "transition": "all 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
    "_hover": {
        "border_color": rx.color_mode_cond(light="rgba(225, 29, 72, 0.5)", dark=rx.color("ruby", 8)),
        "box_shadow": rx.color_mode_cond(
            light="0 6px 14px -2px rgba(15, 23, 42, 0.04), 0 18px 40px -4px rgba(225, 29, 72, 0.14)",
            dark="0 10px 32px rgba(225, 29, 72, 0.22)",
        ),
        "transform": "translateY(-2px)",
    },
}

# Inset KPI Stats Box / Glass Panel
SUB_BOX_STYLE = {
    "background_color": rx.color_mode_cond(light="rgba(241, 245, 249, 0.75)", dark=rx.color("slate", 2)),
    "border": rx.color_mode_cond(
        light="1px solid rgba(226, 232, 240, 0.9)",
        dark=f"1px solid {rx.color('slate', 4)}",
    ),
    "border_radius": "16px",
    "padding": "14px 18px",
}
