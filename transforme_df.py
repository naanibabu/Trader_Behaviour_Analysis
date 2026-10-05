"""Load and prepare the joined trader and market sentiment data."""

from pathlib import Path

import pandas as pd


DATA_DIRECTORY = Path(__file__).resolve().parent / "csv_files"
ALLOWED_DIRECTIONS = (
    "Open Long",
    "Close Long",
    "Open Short",
    "Close Short",
    "Sell",
    "Buy",
)
POSITION_TYPES = {
    "Open Long": "LONG",
    "Short > Long": "LONG",
    "Open Short": "SHORT",
    "Long > Short": "SHORT",
}


def load_analysis_data(data_directory: Path = DATA_DIRECTORY) -> pd.DataFrame:
    """Load, merge, and prepare the datasets through the notebook's new columns."""
    data_directory = Path(data_directory)
    sentiment_data = pd.read_csv(data_directory / "fear_greed_index.csv")
    trader_data = pd.read_csv(data_directory / "historical_data.csv")

    sentiment_data["date"] = pd.to_datetime(sentiment_data["date"])
    trader_data["date"] = pd.to_datetime(
        trader_data["Timestamp IST"],
        format="mixed",
        dayfirst=True,
    ).dt.normalize()

    trader_data = trader_data.loc[
        trader_data["Direction"].isin(ALLOWED_DIRECTIONS)
    ].reset_index(drop=True)

    df = trader_data.merge(sentiment_data, on="date", how="left")
    df = df.drop(
        columns=["timestamp", "Order ID", "Transaction Hash", "Trade ID", "Timestamp"]
    )
    df["classification"] = df["classification"].replace(
        {"Extreme Greed": "Greed", "Extreme Fear": "Fear"}
    )

    account_map = {
        account: f"P{index}"
        for index, account in enumerate(df["Account"].unique())
    }
    df["proxy_name"] = df["Account"].map(account_map)
    df["Is Profitable"] = df["Closed PnL"] > 0
    df["Is Loss"] = df["Closed PnL"] < 0
    df["trade_type"] = df["Direction"].isin(["Buy", "Sell"]).map(
        {True: "Spot", False: "Perptual"}
    )
    df["position_type"] = df["Direction"].map(POSITION_TYPES).fillna("IGNORE")

    return df


df = load_analysis_data()


if __name__ == "__main__":
    print(f"Prepared DataFrame: {df.shape[0]:,} rows x {df.shape[1]} columns")
    print(df.head())