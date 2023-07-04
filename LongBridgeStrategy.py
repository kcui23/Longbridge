import pandas as pd
import yfinance as yf
import ta
import pendulum
from datetime import datetime
import sys


def print_realtime_ratting(df):
    print("Datetime\t\t\tDIR\t\tPrice\tRSI\t\tCCI")
    for i in range(len(df)):
        current = df["BuyIndex"][i]
        if current == "Buy" or current == "PotentialBuy":
            print("%s\t\033[31mBuy   \t%.2f\033[0m\t%5.2f\t%5.2f" % (
                df["Datetime"][i], df["Low"][i], df["RSI"][i], df["CCI"][i]))
        elif current == "Sell" or current == "PotentialSell":
            print("%s\t\033[34mSell  \t%.2f\033[0m\t%5.2f\t%5.2f" % (
                df["Datetime"][i], df["High"][i], df["RSI"][i], df["CCI"][i]))


def calculate_commission(price, position, direction):
    # Long Bridge commission free
    res = max(1, 0.005 * position) + 0.003 * position

    if direction == "Sell":
        res += max(0.01, 0.000008 * price * position) + min(7.27, max(0.01, 0.000145 * position))

    return res


def calculate_buy_position(price, balance, direction):
    for i in range(int(balance / price) + 1, -1, -1):
        rest = balance - price * i - calculate_commission(price, i, direction)
        if 0 <= rest < price:
            return i

    return 0


def find_signals(df):
    # Mark all potential buy / sell timings
    df["BuyIndex"] = ""
    flag_can_start = False  # Can visit df["DIF"][i - 1]

    for i in range(len(df)):

        DIF = df["DIF"][i]
        DEM = df["DEM"][i]
        Histogram = df["Histogram"][i]
        RSI = df["RSI"][i]
        K = df["K"][i]
        D = df["D"][i]
        J = df["J"][i]

        if flag_can_start:
            DIF_last = df["DIF"][i - 1]
            DEM_last = df["DEM"][i - 1]

            if (DIF > DEM and DIF_last < DEM_last) and (DIF < 0 and DEM < 0) and (RSI <= 100) and (J >= K and J >= D):
                df.iloc[i, df.columns.get_loc("BuyIndex")] = "PotentialBuy"
            elif (DIF < DEM and DIF_last > DEM_last) and (DIF > 0 and DEM > 0) and (RSI >= 20) and (J <= K and J <= D):
                df.iloc[i, df.columns.get_loc("BuyIndex")] = "PotentialSell"
            else:
                df.iloc[i, df.columns.get_loc("BuyIndex")] = "Hold"

        if not flag_can_start and pd.notna(DIF) and pd.notna(DEM):
            flag_can_start = True
            continue

    return df


def print_trade(df, principal):
    df["Balance"] = principal
    df["Position"] = 0
    df["Commission"] = 0.00
    df["TotalAssets"] = 0.00

    for i in range(len(df)):
        df.iloc[i, df.columns.get_loc("Balance")] = df["Balance"][i - 1]
        df.iloc[i, df.columns.get_loc("Position")] = df["Position"][i - 1]
        position = df["Position"][i]
        balance = df["Balance"][i]
        direction = df["BuyIndex"][i]

        if direction == "PotentialBuy" and position == 0:
            current_price = df["Low"][i]
            direction = "Buy"
            position = calculate_buy_position(current_price, balance, direction)
            commission = calculate_commission(current_price, position, direction)
            balance = balance - current_price * position - commission

            df.iloc[i, df.columns.get_loc("Position")] = position
            df.iloc[i, df.columns.get_loc("Commission")] = commission
            df.iloc[i, df.columns.get_loc("Balance")] = balance
            df.iloc[i, df.columns.get_loc("BuyIndex")] = direction
        elif direction == "PotentialSell" and position > 0:
            last_buy_price = sys.float_info.max
            for j in range(i - 1, -1, -1):
                if df["BuyIndex"][j] == "Buy":
                    last_buy_price = df["Low"][j]
                    break

            current_price = df["High"][i]
            if current_price >= last_buy_price * 1.01:
                direction = "Sell"
                commission = calculate_commission(current_price, position, direction)
                df.iloc[i, df.columns.get_loc("Position")] = 0
                df.iloc[i, df.columns.get_loc("Balance")] = balance + current_price * position - commission
                df.iloc[i, df.columns.get_loc("Commission")] = commission
                df.iloc[i, df.columns.get_loc("BuyIndex")] = direction

        df.iloc[i, df.columns.get_loc("TotalAssets")] = \
            df["Balance"][i] \
                if df["Position"][i] == 0 else df["Balance"][i] + \
                                               df["Close"][i] * \
                                               df["Position"][i]

    return df


def print_trade_records(df):
    print("\nDatetime\t\t\tDIR\t\tPrice\tPSN\t\tCMS\t\tBalance\t\tTotal")
    for i in range(len(df)):
        direction = df["BuyIndex"][i]

        if direction == "Buy" or direction == "Sell":
            print("%s\t%-4s\t%5.2f\t%4d\t%4.2f\t%10s\t%10s" % (
                df["Datetime"][i],
                df["BuyIndex"][i],
                df["Low"][i] if df["BuyIndex"][i] == "Buy" else df["High"][i],
                df["Position"][i] if df["Position"][i] > 0 else df["Position"][i - 1],
                df["Commission"][i],
                f"{df['Balance'][i]:,.2f}",
                f"{df['TotalAssets'][i]:,.2f}"))

    return df["TotalAssets"][len(df) - 1]


def calculate_df(df):
    # Convert date column to datetime format
    df["Datetime"] = pd.to_datetime(df.index)

    # Calculate MACD, RSI, KDJ, CCI using ta library
    df["DIF"] = ta.trend.MACD(df["Close"], window_slow=26, window_fast=12).macd()
    df["DEM"] = df["DIF"].ewm(span=9).mean()
    df["Histogram"] = df["DIF"] - df["DEM"].ewm(span=9).mean()

    df["KDJ"] = ta.momentum.StochasticOscillator(df["High"], df["Low"], df["Close"]).stoch()
    df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()
    df["K"] = ta.momentum.StochasticOscillator(df["High"], df["Low"], df["Close"], window=9).stoch()
    df["D"] = df["K"].ewm(com=2).mean()
    df["J"] = 3 * df["K"] - 2 * df["D"]

    df["CCI"] = ta.trend.CCIIndicator(df["High"], df["Low"], df["Close"], window=20, constant=0.015).cci()

    return df


def plotOneDay(ticker, start_time, end_time, principal):
    # get data using download method
    df = yf.download(ticker, start=start_time, end=end_time, interval="1d", progress=False)
    df = calculate_df(df)
    df = find_signals(df)
    df = print_trade(df, principal)

    return df


def plotOneMinute(ticker, trade_day, principal):
    # get data using download method
    start_time = pendulum.parse(trade_day + " 00:08:00")
    end_time = pendulum.parse(trade_day + " 23:59:59")

    # convert the index to Eastern Time and remove the timezone
    df = yf.download(ticker, start=start_time, end=end_time, interval="1m", progress=False)
    df.index = pd.DatetimeIndex(df.index).tz_convert("US/Eastern").tz_localize(None)
    df = calculate_df(df)
    df = find_signals(df)
    df = print_trade(df, principal)

    return df


tickers = [
    "MSFT", "NVDA", "TSM", "GOOGL", "META", "ORCL", "AMZN", "QCOM", "AMD", "VZ", "NFLX", "ASML",
    "JPM", "GS", "MS", "WFC", "BAC", "V", "MA", "AXP",
    "CVX", "XOM", "TSLA", "SPLG"
]

today = datetime.today()
date_string = today.strftime("%Y-%m-%d")
date_string_today = today.strftime("%Y-%m-%d")
principal = 10000

# For all stocks in the list
for x in tickers:
    now = datetime.now()
    print("\n%-5s %s" % (x, now.strftime("%d/%m/%y %H:%M:%S")))
    df = plotOneMinute(x, "2023-07-03", principal)
    print_realtime_ratting(df)

    df = plotOneDay(x, "2020-01-01", date_string_today, principal)
    print_realtime_ratting(df)
