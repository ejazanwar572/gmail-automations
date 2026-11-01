import reflex as rx

config = rx.Config(
    app_name="dcbm_reflex",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(
                appearance="light",
                accent_color="amber",
                gray_color="slate",
                radius="large",
                scaling="100%",
            )
        ),
    ],
)