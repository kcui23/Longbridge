# import libraries
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
import pandas as pd
import yfinance as yf
import ta
from datetime import datetime, timedelta
import pendulum


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


def print_day_trade(df, principle):
    """
     This function takes a dataframe of stock prices and a principle amount as inputs
    and prints the details of each buy and sell transaction based on the BuyIndex column
    It also updates the Balance, Position and Commission columns in the dataframe
    """

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
            print("%s\t%4s\t%5.2f\t@%4d\tCommission: %4.2f\tBalance: %10s\tTotal: %10s" % (
                df["Datetime"][i], direction, df["Low"][i], position, df["Commission"][i], f"{balance:,.2f}",
                f"{balance + df['Close'][i] * df['Position'][i]:,.2f}"))


def plotVerticalLines(df, ax):
    for i in range(len(df)):
        x = df["Datetime"][i]
        if df["BuyIndex"][i] == "Buy":
            ax.axvline(x=x, ymin=0, ymax=3.5, c="#ff2f92", linewidth=0.5, alpha=1, zorder=0, clip_on=False)
        elif df["BuyIndex"][i] == "Sell":
            ax.axvline(x=x, ymin=0.2, ymax=3.5, c="#0055cc", linewidth=0.5, alpha=1, zorder=0, clip_on=False)


def markBuyAndSell(df, ax):
    for i in range(len(df)):
        x = df["Datetime"][i]
        y = -200
        if df["BuyIndex"][i] == "Buy":
            text = "B\n" + f"{df['Low'][i]:,.2f}"
            ax.annotate(text, xy=(x, y), xytext=(
                x, y), color="#ffffff", fontsize=8,
                        bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.15", facecolor="#ff2f92",
                                  edgecolor="none", alpha=1))

        elif df["BuyIndex"][i] == "Sell":
            text = "S\n" + f"{df['High'][i]:,.2f}"
            ax.annotate(text, xy=(x, y), xytext=(
                x, y + 80), color="#ffffff", fontsize=8,
                        bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.15", facecolor="#0055cc",
                                  edgecolor="none", alpha=1))


def find_signals(df):
    # Initialize an empty column for signals
    df["BuyIndex"] = ""
    flag = False
    buy_tick = True  # True: to buy, False: to hold or sell

    for i in range(len(df)):
        if flag:
            if buy_tick and df["DIF"][i] > df["DEM"][i] and df["DIF"][i - 1] < df["DEM"][i - 1] and \
                    df["Histogram"][i] <= 0 and df["DIF"][i] < 0 and df["RSI"][i] <= 100 and (
                    df["J"][i] > df["K"][i] and df["J"][i] > df["D"][i]):

                df.iloc[i, df.columns.get_loc("BuyIndex")] = "Buy"
                buy_tick = False
            elif not buy_tick and df["DIF"][i] < df["DEM"][i] and df["DIF"][i - 1] > df["DEM"][i - 1] and \
                    df["Histogram"][i] > 0 and df["DEM"][i] > 0 and df["RSI"][i] >= 0 and (
                    df["J"][i] < df["K"][i] and df["J"][i] < df["D"][i]):

                df.iloc[i, df.columns.get_loc("BuyIndex")] = "Sell"
                buy_tick = True
            else:
                df.iloc[i, df.columns.get_loc("BuyIndex")] = "Hold"

        if pd.notna(df["DIF"][i]) and pd.notna(df["DEM"][i]):
            flag = True
            continue

    # Return the data frame with signals
    return df


def plotCandlestick(df, ax, ticker):
    mc = mpf.make_marketcolors(up='#0055cc', down='#ff2f92', edge='inherit', wick='inherit',
                               volume='inherit')
    s = mpf.make_mpf_style(base_mpf_style='starsandstripes', rc={'font.size': 6},
                           marketcolors=mc)

    # plot the candlestick chart on ax
    mpf.plot(df, type="candle", ax=ax, style=s, warn_too_much_data=10000000)
    ax.set_ylabel("%s" % ticker)
    ax.yaxis.set_label_position("right")
    # ax.yaxis.set_ticks_position("right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.set_xticklabels([])
    ax.set_xticks([])
    ax.margins(x=0)


def plotMACD(df, ax, date_format):
    # plot the MACD, signal and histogram on ax
    ax.set_ylabel("MACD")
    ax.set_xlim(min(df["Datetime"]), max(df["Datetime"]))
    ax.margins(x=0)
    ax.xaxis.set_label_position("top")
    ax.xaxis.set_ticks_position("top")
    ax.yaxis.set_label_position("right")
    ax.yaxis.set_ticks_position("right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.xaxis.set_major_formatter(date_format)
    ax.tick_params(axis="x", top=False)
    ax.plot(df["Datetime"], df["DIF"], color="#0055cc", linewidth=1, label="DIF")
    ax.plot(df["Datetime"], df["DEM"], color="#ffa500", linewidth=1, label="DEM")
    ax.fill_between(df["Datetime"], df["Histogram"], 0, where=(df["Histogram"] > 0), color="#006d21", alpha=1)
    ax.fill_between(df["Datetime"], df["Histogram"], 0, where=(df["Histogram"] <= 0), color="#ff2f92", alpha=1)


def plotRSI(df, ax):
    # plot the RSI on ax3
    ax.set_ylabel("RSI")
    ax.set_xlim(min(df["Datetime"]), max(df["Datetime"]))
    ax.margins(x=0)
    ax.yaxis.set_label_position("right")
    ax.yaxis.set_ticks_position("right")
    ax.plot(df["Datetime"], df["RSI"], label="RSI", color="#ff2f92", linewidth=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.set_xticklabels([])
    ax.set_xticks([])
    ax.set_ylim(0, 100)


def plotKDJ(df, ax):
    # plot the KDJ on ax4
    ax.set_ylabel("KDJ")
    ax.set_xlim(min(df["Datetime"]), max(df["Datetime"]))
    ax.margins(x=0)
    ax.yaxis.set_label_position("right")
    ax.yaxis.set_ticks_position("right")
    ax.plot(df["Datetime"], df["K"], label="K", color="#ff2f92", linewidth=1)
    ax.plot(df["Datetime"], df["D"], label="D", color="#0055cc", linewidth=1)
    ax.plot(df["Datetime"], df["J"], label="J", color="#ffa500", linewidth=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.set_xticklabels([])
    ax.set_xticks([])
    ax.set_ylim(-200, 200)


def calculateDF(df):
    # Convert date column to datetime format
    df["Datetime"] = pd.to_datetime(df.index)

    # Calculate MACD, RSI, KDJ using ta library
    df["DIF"] = ta.trend.MACD(df["Close"], window_slow=26, window_fast=12).macd()
    df["DEM"] = df["DIF"].ewm(span=9).mean()
    df["Histogram"] = df["DIF"] - df["DEM"].ewm(span=9).mean()

    df["KDJ"] = ta.momentum.StochasticOscillator(df["High"], df["Low"], df["Close"]).stoch()
    df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()
    df["K"] = ta.momentum.StochasticOscillator(df["High"], df["Low"], df["Close"], window=9).stoch()
    df["D"] = df["K"].ewm(com=2).mean()
    df["J"] = 3 * df["K"] - 2 * df["D"]

    return df


def plotOneDay(ticker, startTime, endTime):
    # define the ticker symbol
    date_format = mdates.DateFormatter("%d/%m/%y")

    # get data using download method
    df = yf.download(ticker, start=startTime, end=endTime, interval="1d")
    df = calculateDF(df)
    df = find_signals(df)

    # Plot stock price, MACD, KDJ, RSI using matplotlib
    plt.rcParams["font.family"] = "Menlo"
    fig = plt.figure(figsize=(16, 8), dpi=300)

    ax1 = plt.subplot2grid((8, 1), (0, 0), rowspan=4)
    ax2 = plt.subplot2grid((8, 1), (4, 0), rowspan=2)
    ax3 = plt.subplot2grid((8, 1), (6, 0), rowspan=1)
    ax4 = plt.subplot2grid((8, 1), (7, 0), rowspan=1)

    plotCandlestick(df, ax1, ticker)
    plotMACD(df, ax2, date_format)
    plotRSI(df, ax3)
    plotKDJ(df, ax4)

    plotVerticalLines(df, ax2)
    plotVerticalLines(df, ax3)
    plotVerticalLines(df, ax4)
    markBuyAndSell(df, ax4)

    # save the figure
    fig.savefig("1d %-5s %s %s.png" % (ticker, startTime, endTime), transparent=True)
    return df


def plotOneMinute(ticker, tradeDay):
    # define the ticker symbol
    date_format = mdates.DateFormatter("%H:%M")

    # get data using download method

    startTime = pendulum.parse(tradeDay + " 00:00")
    endTime = pendulum.parse(tradeDay + " 23:59")
    df = yf.download(ticker, start=startTime, end=endTime, interval="1m")

    # convert the index to Eastern Time and remove the timezone
    df.index = pd.DatetimeIndex(df.index).tz_convert("US/Eastern").tz_localize(None)
    df = calculateDF(df)
    df = find_signals(df)

    # Plot stock price, MACD, KDJ, RSI using matplotlib
    plt.rcParams["font.family"] = "Menlo"
    fig = plt.figure(figsize=(16, 8), dpi=300)

    ax1 = plt.subplot2grid((8, 1), (0, 0), rowspan=4)
    ax2 = plt.subplot2grid((8, 1), (4, 0), rowspan=2)
    ax3 = plt.subplot2grid((8, 1), (6, 0), rowspan=1)
    ax4 = plt.subplot2grid((8, 1), (7, 0), rowspan=1)

    plotCandlestick(df, ax1, ticker)
    plotMACD(df, ax2, date_format)
    plotRSI(df, ax3)
    plotKDJ(df, ax4)

    plotVerticalLines(df, ax2)
    plotVerticalLines(df, ax3)
    plotVerticalLines(df, ax4)
    markBuyAndSell(df, ax4)

    # save the figure
    fig.savefig("1m %-5s %s.png" % (ticker, tradeDay), transparent=True)
    return df


today = datetime.today()
date_string = today.strftime("%Y-%m-%d")

tickers = ["NVDA", "MSFT", "META", "TSM", "GOOGL", "AMZN", "QCOM", "AMD", "ORCL", "VZ", "NFLX", "JPM", "GS", "MS",
           "WFC", "BAC",
           "V", "MA", "AXP", "CVX", "XOM", "MCD", "PEP", "KO", "PG", "ABBV", "MRK", "LLY", "UNH", "PFE", "JNJ", "SPY",
           "SPLG"]

today = datetime.today()
yesterday = today - timedelta(days=1)
date_string_today = today.strftime("%Y-%m-%d")
date_string_yesterday = today.strftime("%Y-%m-%d")

print_day_trade(plotOneDay("NVDA", "2020-01-01", date_string_today), 10000)
print_day_trade(plotOneMinute("NVDA", "2023-06-28"), 10000)

# for x in tickers:
#     print(date_string_today, x)
#     print_day_trade(plotOneMinute(x, "2023-06-28"), 10000)
#     print_day_trade(plotOneDay(x, "2021-01-01", date_string_today), 10000)
