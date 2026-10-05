"""Create a one-page bivariate analysis PDF from a prepared DataFrame."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.image import imread
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter


BG = "#F5FEFD"
TEAL = "#97FCE4"
DARK = "#0F3933"
GREEN = "#20b958"
TEXT = "#04060C"
SENTIMENT_ORDER = ["Fear", "Neutral", "Greed"]
SENTIMENT_COLORS = {
    "Fear": TEAL,
    "Neutral": DARK,
    "Greed": GREEN,
}
DIRECTION_ORDER = [
    "Buy",
    "Sell",
    "Open Long",
    "Close Long",
    "Open Short",
    "Close Short",
]
DIRECTION_COLORS = [
    "#97FCE4",
    "#0F3933",
    "#20b958",
    "#66C2A5",
    "#2E8B57",
    "#B7E4C7",
]
REPORT_DIRECTORY = Path(__file__).resolve().parent / "reports"
LOGO_PATH = Path(__file__).resolve().parent / "hyperliquid_logo.webp"
REQUIRED_COLUMNS = {
    "classification",
    "Closed PnL",
    "Is Profitable",
    "Is Loss",
    "Size USD",
    "Direction",
}


def _add_logo_watermark(fig: plt.Figure) -> None:
    if not LOGO_PATH.exists():
        return

    logo = imread(LOGO_PATH)
    target_width = max(1, int(fig.bbox.width * 0.16))
    target_height = max(1, int(target_width * logo.shape[0] / logo.shape[1]))

    from PIL import Image

    logo_image = Image.fromarray((logo * 255).astype(np.uint8))
    logo_image = logo_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
    fig.figimage(
        np.asarray(logo_image),
        xo=int(fig.bbox.width * 0.82),
        yo=int(fig.bbox.height * 0.025),
        alpha=0.07,
        zorder=-1,
    )


def _money(value: float) -> str:
    if pd.isna(value):
        return "N/A"
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000:
        return f"{sign}${value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{sign}${value / 1_000:.2f}K"
    return f"{sign}${value:,.2f}"


def _pnl_tick(value: float, _position: int) -> str:
    if value == 0:
        return "$0"
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000:
        return f"{sign}${value / 1_000_000:.0f}M"
    if value >= 1_000:
        return f"{sign}${value / 1_000:.0f}K"
    return f"{sign}${value:.0f}"


def _draw_table(ax: plt.Axes, data: pd.DataFrame) -> None:
    ax.axis("off")
    table = ax.table(
        cellText=data.values,
        rowLabels=data.index,
        colLabels=data.columns,
        cellLoc="center",
        rowLoc="center",
        bbox=[0, 0, 1, 1],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)

    for (row, _column), cell in table.get_celld().items():
        cell.set_edgecolor(BG)
        cell.set_linewidth(2)
        if row == 0:
            cell.set_facecolor(DARK)
            cell.get_text().set_color("white")
            cell.get_text().set_weight("bold")
        else:
            sentiment = data.index[row - 1]
            cell.set_facecolor(SENTIMENT_COLORS[sentiment])
            cell.get_text().set_color("white" if sentiment == "Neutral" else TEXT)


def create_bivariate_analysis_report(
    df: pd.DataFrame,
    output_directory: str | Path = REPORT_DIRECTORY,
) -> Path:
    """Create the bivariate analysis PDF and return its path."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    missing_columns = REQUIRED_COLUMNS.difference(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"DataFrame is missing required columns: {missing}")
    if df.empty:
        raise ValueError("Cannot create a report from an empty DataFrame")

    data = df.copy()
    data["classification"] = data["classification"].replace(
        {"Extreme Greed": "Greed", "Extreme Fear": "Fear"}
    )
    data["Is Profitable"] = data["Is Profitable"].fillna(False)
    data["Is Loss"] = data["Is Loss"].fillna(False)

    realized = data.loc[
        data["Closed PnL"].notna() & data["Closed PnL"].ne(0)
    ].copy()
    pnl_stats = (
        realized.groupby("classification")["Closed PnL"]
        .agg(Average="mean", Median="median")
        .reindex(SENTIMENT_ORDER)
    )

    win = (
        data.groupby("classification")
        .agg(
            Profitable=("Is Profitable", "sum"),
            Loss=("Is Loss", "sum"),
        )
        .reindex(SENTIMENT_ORDER)
    )
    win["Realized"] = win["Profitable"] + win["Loss"]
    win["Win Rate"] = (
        win["Profitable"]
        .div(win["Realized"].replace(0, np.nan))
        .mul(100)
    )

    pnl_sd = (
        realized.groupby("classification")["Closed PnL"]
        .std()
        .reindex(SENTIMENT_ORDER)
    )
    size_stats = (
        data.groupby("classification")["Size USD"]
        .agg(Total="sum", Average="mean", Median="median")
        .reindex(SENTIMENT_ORDER)
    )

    direction_counts = pd.crosstab(data["classification"], data["Direction"])
    sentiment_totals = direction_counts.reindex(index=SENTIMENT_ORDER).sum(axis=1)
    direction_pct = (
        direction_counts
        .reindex(index=SENTIMENT_ORDER, columns=DIRECTION_ORDER, fill_value=0)
        .div(sentiment_totals.replace(0, np.nan), axis=0)
        .mul(100)
        .fillna(0)
    )

    table1 = pnl_stats.copy()
    table1["Win Rate"] = win["Win Rate"]
    table1.columns = ["Average Realized PnL", "Median Realized PnL", "Win Rate"]
    table1["Average Realized PnL"] = table1["Average Realized PnL"].map(_money)
    table1["Median Realized PnL"] = table1["Median Realized PnL"].map(_money)
    table1["Win Rate"] = table1["Win Rate"].map(
        lambda value: f"{value:.2f}%" if pd.notna(value) else "N/A"
    )

    table2 = size_stats.copy()
    table2.columns = ["Total Trade Size", "Average Trade Size", "Median Trade Size"]
    table2 = table2.apply(lambda column: column.map(_money))

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    report_path = output_directory / "bivarient_analysis_report.pdf"

    with plt.rc_context({
        "font.family": "DejaVu Sans",
        "text.color": TEXT,
        "axes.labelcolor": TEXT,
        "axes.titlecolor": TEXT,
        "xtick.color": TEXT,
        "ytick.color": TEXT,
        "figure.facecolor": BG,
        "axes.facecolor": BG,
    }), PdfPages(report_path) as pdf:
        fig = plt.figure(figsize=(11.69, 8.27), facecolor=BG)
        _add_logo_watermark(fig)
        fig.text(
            0.5, 0.965,
            "BIVARIATE ANALYSIS - TRADER BEHAVIOUR",
            ha="center", fontsize=18, fontweight="bold", color=TEXT,
        )

        fig.text(
            0.05, 0.885,
            "Does Trader Profitability Vary Across Market Sentiment?",
            fontsize=11, fontweight="bold",
        )
        _draw_table(fig.add_axes([0.05, 0.685, 0.43, 0.16]), table1)

        fig.text(
            0.05, 0.625,
            "Does Trading Volume Vary Across Market Sentiment?",
            fontsize=11, fontweight="bold",
        )
        _draw_table(fig.add_axes([0.05, 0.425, 0.43, 0.16]), table2)

        fig.text(
            0.54, 0.885,
            "Does Trading Risk Vary Across Sentiment?",
            fontsize=11, fontweight="bold",
        )
        ax_risk = fig.add_axes([0.55, 0.49, 0.40, 0.33], facecolor=BG)
        if not realized.empty:
            sns.boxplot(
                data=realized,
                x="classification",
                y="Closed PnL",
                hue="classification",
                order=SENTIMENT_ORDER,
                hue_order=SENTIMENT_ORDER,
                palette=SENTIMENT_COLORS,
                dodge=False,
                legend=False,
                whis=(10, 90),
                showfliers=False,
                ax=ax_risk,
            )
            ax_risk.set_yscale("symlog", linthresh=10)
            ax_risk.yaxis.set_major_formatter(FuncFormatter(_pnl_tick))
            ax_risk.axhline(0, color=TEXT, linestyle="--", linewidth=0.8, alpha=0.7)
        else:
            ax_risk.text(0.5, 0.5, "No realized PnL", ha="center", va="center")
        ax_risk.set_xlabel("")
        ax_risk.set_ylabel("Realized PnL (USD)", fontsize=8)
        ax_risk.tick_params(labelsize=8)
        ax_risk.grid(False)
        ax_risk.spines["top"].set_visible(False)
        ax_risk.spines["right"].set_visible(False)

        sd_text = "   |   ".join(
            f"{sentiment}: {_money(pnl_sd[sentiment])}"
            for sentiment in SENTIMENT_ORDER
        )
        fig.text(0.55, 0.425, f"PnL standard deviation: {sd_text}", fontsize=8, color=DARK)

        fig.text(
            0.05, 0.395,
            "How Does Trader Behaviour Change Across Sentiment?",
            fontsize=12, fontweight="bold",
        )
        pie_positions = [
            [0.04, 0.115, 0.27, 0.25],
            [0.365, 0.115, 0.27, 0.25],
            [0.69, 0.115, 0.27, 0.25],
        ]

        for sentiment, position in zip(SENTIMENT_ORDER, pie_positions):
            ax_pie = fig.add_axes(position, facecolor=BG)
            values = direction_pct.loc[sentiment]
            nonzero = values > 0
            if nonzero.any():
                ax_pie.pie(
                    values[nonzero],
                    colors=[
                        DIRECTION_COLORS[DIRECTION_ORDER.index(direction)]
                        for direction in values.index[nonzero]
                    ],
                    autopct=lambda pct: f"{pct:.1f}%" if pct >= 5 else "",
                    startangle=140,
                    textprops={"fontsize": 7, "color": TEXT},
                    wedgeprops={"edgecolor": BG, "linewidth": 1},
                )
            else:
                ax_pie.text(0.5, 0.5, "No trades", ha="center", va="center")
            ax_pie.set_title(sentiment, fontsize=10, fontweight="bold")

        legend_handles = [
            Patch(facecolor=color, label=direction)
            for direction, color in zip(DIRECTION_ORDER, DIRECTION_COLORS)
        ]
        fig.legend(
            handles=legend_handles,
            title="Direction",
            loc="lower center",
            bbox_to_anchor=(0.5, 0.055),
            ncol=3,
            frameon=False,
            fontsize=8,
            title_fontsize=8,
        )
        fig.text(
            0.08, 0.018,
            "Note: Each pie shows the trade-direction share within that sentiment.",
            fontsize=7.5, color=DARK,
        )

        try:
            pdf.savefig(fig, facecolor=BG, bbox_inches=None)
        finally:
            plt.close(fig)

    return report_path


if __name__ == "__main__":
    from transforme_df import df

    print(f"Created report: {create_bivariate_analysis_report(df)}")