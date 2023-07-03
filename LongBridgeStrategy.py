import pandas as pd
import yfinance as yf
import ta
import pendulum
from datetime import datetime


def print_realtime_ratting(df):
    for i in range(len(df)):
        current = df["BuyIndex"][i]
        if current == "Buy" or current == "PotentialBuy":
            print("%s\tBuy   \t%.2f\tRSI: %5.2f" % (df["Datetime"][i], df["Low"][i], df["RSI"][i]))
        elif current == "Sell" or current == "PotentialSell":
            print("%s\tSell  \t%.2f\tRSI: %5.2f" % (df["Datetime"][i], df["High"][i], df["RSI"][i]))


def calculate_commission(price, position, direction):
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
    # Initialize an empty column for signals
    df["BuyIndex"] = ""
    flag_can_start = False  # Can visit df["DIF"][i - 1]
    buy_tick = True  # True: to buy, False: to hold or sell

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

            if (DIF > DEM and DIF_last < DEM_last) and (DIF < 0 and DEM < 0) and (RSI <= 100):
                if buy_tick:
                    df.iloc[i, df.columns.get_loc("BuyIndex")] = "Buy"
                    buy_tick = False
                elif not buy_tick:
                    df.iloc[i, df.columns.get_loc("BuyIndex")] = "PotentialBuy"
            elif (DIF < DEM and DIF_last > DEM_last) and (DIF > 0 and DEM > 0) and (RSI >= 50):
                if not buy_tick:
                    df.iloc[i, df.columns.get_loc("BuyIndex")] = "Sell"
                    buy_tick = True
                elif buy_tick:
                    df.iloc[i, df.columns.get_loc("BuyIndex")] = "PotentialSell"
            else:
                df.iloc[i, df.columns.get_loc("BuyIndex")] = "Hold"

        if pd.notna(DIF) and pd.notna(DEM):
            flag_can_start = True
            continue

    # Return the data frame with signals
    return df


def print_day_trade(df, principle):
    df["Balance"] = principle
    df["Position"] = 0
    df["Commission"] = 0.00

    for i in range(len(df)):
        direction = df["BuyIndex"][i]
        balance = df["Balance"][i - 1]
        position = 0

        if direction == "Buy":
            price = df["Low"][i]
            position = calculate_buy_position(price, balance, direction)
            commission = calculate_commission(price, position, direction)
            balance = balance - price * position - commission

            df.iloc[i, df.columns.get_loc("Balance")] = balance
            df.iloc[i, df.columns.get_loc("Position")] = position
            df.iloc[i, df.columns.get_loc("Commission")] = commission
        elif direction == "Sell":
            price = df["High"][i]
            position = df["Position"][i - 1]
            commission = calculate_commission(price, position, direction)
            balance = balance + price * position - commission

            df.iloc[i, df.columns.get_loc("Balance")] = balance
            df.iloc[i, df.columns.get_loc("Position")] = 0
            df.iloc[i, df.columns.get_loc("Commission")] = commission
        else:
            df.iloc[i, df.columns.get_loc("Balance")] = df["Balance"][i - 1]
            df.iloc[i, df.columns.get_loc("Position")] = df["Position"][i - 1]

        if direction == "Buy" or direction == "Sell":
            print("%s\t%-4s\t%5.2f\t@%4d\tCommission: %4.2f\tBalance: %10s\tTotal: %10s" % (
                df["Datetime"][i], direction, df["Low"][i], position, df["Commission"][i], f"{balance:,.2f}",
                f"{balance + df['Close'][i] * df['Position'][i]:,.2f}"))

    final_index = len(df) - 1
    final_asset = df["Balance"][final_index]
    if df["Position"][final_index] > 0:
        final_asset += df["Close"][final_index] * df["Position"][final_index]
    print(f"{final_asset:,.2f}")

    return df


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


def plotOneDay(ticker, start_time, end_time):
    # get data using download method
    df = yf.download(ticker, start=start_time, end=end_time, interval="1d", progress=False)
    df = calculate_df(df)
    df = find_signals(df)
    print_realtime_ratting(df)

    return df


def plotOneMinute(ticker, trade_day):
    # get data using download method
    start_time = pendulum.parse(trade_day + " 00:00")
    end_time = pendulum.parse(trade_day + " 23:59")
    df = yf.download(ticker, start=start_time, end=end_time, interval="1m", progress=False)

    # convert the index to Eastern Time and remove the timezone
    df.index = pd.DatetimeIndex(df.index).tz_convert("US/Eastern").tz_localize(None)
    df = calculate_df(df)
    df = find_signals(df)
    print_realtime_ratting(df)

    return df


tickers = ["NVDA", "MSFT", "META", "TSM", "GOOGL", "AMZN", "QCOM", "AMD", "ORCL", "VZ", "NFLX", "JPM", "GS",
           "MS", "WFC", "BAC", "V", "MA", "AXP", "CVX", "XOM", "MCD", "PEP", "KO", "PG", "ABBV", "MRK",
           "LLY", "UNH", "PFE", "JNJ", "SPY", "SPLG"]

today = datetime.today()
date_string = today.strftime("%Y-%m-%d")
date_string_today = today.strftime("%Y-%m-%d")
principal = 10000.00

# For all stocks in the list
for x in tickers:
    now = datetime.now()
    print("%-5s %s" % (x, now.strftime("%d/%m/%y %H:%M:%S")))
    plotOneMinute(x, "2023-06-30")
    plotOneDay(x, "2020-01-01", date_string_today)
