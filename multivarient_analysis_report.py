"""Create a one-page multivariate analysis PDF from a prepared DataFrame."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.image import imread
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
TRADE_TYPE_ORDER = ["Spot", "Perpetual"]
POSITION_DIRECTIONS = ["Close Long", "Close Short", "Sell"]
REPORT_DIRECTORY = Path(__file__).resolve().parent / "reports"
LOGO_PATH = Path(__file__).resolve().parent / "hyperliquid_logo.webp"
REQUIRED_COLUMNS = {"classification", "Closed PnL", "trade_type", "Direction"}


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


def create_multivariate_analysis_report(
    df: pd.DataFrame,
    output_directory: str | Path = REPORT_DIRECTORY,
) -> Path:
    """Create the multivariate analysis PDF and return its path."""
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
    data["trade_type"] = data["trade_type"].replace({"Perptual": "Perpetual"})
    realized = data.loc[
        data["Closed PnL"].notna() & data["Closed PnL"].ne(0)
    ].copy()
    position_data = realized.loc[
        realized["Direction"].isin(POSITION_DIRECTIONS)
    ].copy()

    if realized.empty:
        win_rate_table = pd.DataFrame(
            np.nan,
            index=SENTIMENT_ORDER,
            columns=TRADE_TYPE_ORDER,
        )
    else:
        win_rate_table = (
            realized
            .groupby(["classification", "trade_type"], observed=True)["Closed PnL"]
            .apply(lambda pnl: pnl.gt(0).mean() * 100)
            .unstack("trade_type")
            .reindex(index=SENTIMENT_ORDER, columns=TRADE_TYPE_ORDER)
        )

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    report_path = output_directory / "multivarient_analysis_report.pdf"

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
            "MULTIVARIATE ANALYSIS - TRADER BEHAVIOUR",
            ha="center", fontsize=18, fontweight="bold", color=TEXT,
        )
        fig.text(
            0.5, 0.935,
            "Realized profitability, win rate, and position-closure outcomes",
            ha="center", fontsize=9, color=DARK,
        )

        ax_pnl = fig.add_axes([0.09, 0.56, 0.35, 0.30], facecolor="none")
        if not realized.empty:
            sns.boxplot(
                data=realized,
                x="classification",
                y="Closed PnL",
                hue="trade_type",
                order=SENTIMENT_ORDER,
                hue_order=TRADE_TYPE_ORDER,
                palette={"Spot": TEAL, "Perpetual": DARK},
                showfliers=False,
                ax=ax_pnl,
            )
            ax_pnl.set_yscale("symlog", linthresh=10)
            ax_pnl.yaxis.set_major_formatter(FuncFormatter(_pnl_tick))
            ax_pnl.axhline(0, color=TEXT, linestyle="--", linewidth=0.8, alpha=0.7)
            ax_pnl.legend(
                loc="upper left",
                bbox_to_anchor=(1.02, 1),
                frameon=False,
                fontsize=8,
                borderaxespad=0,
            )
        else:
            ax_pnl.text(0.5, 0.5, "No realized PnL", ha="center", va="center")
        ax_pnl.set_title("Realized PnL by Sentiment and Trade Type", fontweight="bold")
        ax_pnl.set_xlabel("Market Sentiment", fontsize=8)
        ax_pnl.set_ylabel("Realized PnL (USD, symmetric log scale)", fontsize=8)
        ax_pnl.spines["top"].set_visible(False)
        ax_pnl.spines["right"].set_visible(False)
        ax_pnl.tick_params(axis="both", labelsize=8)

        ax_win = fig.add_axes([0.56, 0.56, 0.38, 0.30], facecolor="none")
        sns.heatmap(
            win_rate_table,
            annot=True,
            fmt=".1f",
            mask=win_rate_table.isna(),
            cmap=sns.light_palette(GREEN, as_cmap=True),
            vmin=0,
            vmax=100,
            linewidths=1,
            linecolor=BG,
            cbar_kws={"label": "Win rate (%)"},
            ax=ax_win,
        )
        ax_win.set_title("Win Rate by Sentiment and Trade Type", fontweight="bold")
        ax_win.set_xlabel("Trade Type", fontsize=8)
        ax_win.set_ylabel("Market Sentiment", fontsize=8)
        ax_win.tick_params(axis="both", labelsize=8)
        ax_win.collections[0].colorbar.ax.tick_params(labelsize=8)

        ax_position = fig.add_axes([0.09, 0.12, 0.72, 0.31], facecolor="none")
        if not position_data.empty:
            sns.boxplot(
                data=position_data,
                x="Direction",
                y="Closed PnL",
                hue="classification",
                order=POSITION_DIRECTIONS,
                hue_order=SENTIMENT_ORDER,
                palette=SENTIMENT_COLORS,
                showfliers=False,
                ax=ax_position,
            )
            ax_position.legend(
                loc="upper left",
                bbox_to_anchor=(1.02, 1),
                frameon=False,
                fontsize=8,
                borderaxespad=0,
            )
        else:
            ax_position.text(0.5, 0.5, "No position closures", ha="center", va="center")
        ax_position.set_yscale("symlog", linthresh=10)
        ax_position.yaxis.set_major_formatter(FuncFormatter(_pnl_tick))
        ax_position.axhline(0, color=TEXT, linestyle="--", linewidth=0.8, alpha=0.7)
        ax_position.set_title(
            "Realized Outcomes from Long/Short Position Closures by Sentiment",
            fontweight="bold",
        )
        ax_position.set_xlabel("Position Direction", fontsize=8)
        ax_position.set_ylabel("Realized PnL (USD, symmetric log scale)", fontsize=8)
        ax_position.spines["top"].set_visible(False)
        ax_position.spines["right"].set_visible(False)
        ax_position.tick_params(axis="both", labelsize=8)

        try:
            pdf.savefig(fig, facecolor=BG, bbox_inches=None)
        finally:
            plt.close(fig)

    return report_path


if __name__ == "__main__":
    from transforme_df import df

    print(f"Created report: {create_multivariate_analysis_report(df)}")