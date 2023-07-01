import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
import pandas as pd
import pandas_market_calendars as mcal
import yfinance as yf
import ta
from datetime import datetime
import pendulum


def generateUSTradeDays(start_date, end_date):
    # Get NYSE and Nasdaq calendars
    nyse = mcal.get_calendar('NYSE')
    nasdaq = mcal.get_calendar('NASDAQ')

    # Get NYSE and Nasdaq schedules
    nyse_schedule = nyse.schedule(start_date=start_date, end_date=end_date)
    nasdaq_schedule = nasdaq.schedule(start_date=start_date, end_date=end_date)

    # Get the intersection of NYSE and Nasdaq schedules
    trade_days = nyse_schedule.index.intersection(nasdaq_schedule.index)

    return trade_days


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

            if DIF > DEM and DIF_last < DEM_last and Histogram <= 0 and DIF < 0 and RSI <= 100 and (J > K and J > D):
                print("%s\tBuy  \t%.2f\t" % (df["Datetime"][i], df["Open"][1]))
                if buy_tick:
                    df.iloc[i, df.columns.get_loc("BuyIndex")] = "Buy"
                    buy_tick = False
                elif not buy_tick:
                    df.iloc[i, df.columns.get_loc("BuyIndex")] = "PotentialBuy"
            elif DIF < DEM and DIF_last > DEM_last and Histogram > 0 and DIF > 0 and RSI >= 0 and (J < K and J < D):
                print("%s\tSell \t%.2f\t" % (df["Datetime"][i], df["Open"][i]))
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
    total = 0.00

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
            total = balance + df['Close'][i] * df['Position'][i]
            print("%s\t%-4s\t%5.2f\t@%4d\tCommission: %4.2f\tBalance: %10s\tTotal: %10s" % (
                df["Datetime"][i], direction, df["Low"][i], position, df["Commission"][i], f"{balance:,.2f}",
                f"{balance + df['Close'][i] * df['Position'][i]:,.2f}"))

    return total


def plotVerticalLines(df, ax):
    for i in range(len(df)):
        x = df["Datetime"][i]
        current = df["BuyIndex"][i]
        if current == "Buy" or current == "PotentialBuy":
            ax.axvline(x=x, ymin=0, ymax=3.2, c="#ff2f92", linewidth=0.5, alpha=1, zorder=0, clip_on=False)
        elif current == "Sell" or current == "PotentialSell":
            ax.axvline(x=x, ymin=0, ymax=3.2, c="#0055cc", linewidth=0.5, alpha=1, zorder=0, clip_on=False)


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

        elif df["BuyIndex"][i] == "PotentialBuy":
            text = f"{df['Low'][i]:,.2f}"
            ax.annotate(text, xy=(x, y), xytext=(
                x, y), color="#ffffff", fontsize=7,
                        bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.15", facecolor="#ff2f92",
                                  edgecolor="none", alpha=1))

        elif df["BuyIndex"][i] == "Sell":
            text = "S\n" + f"{df['High'][i]:,.2f}"
            ax.annotate(text, xy=(x, y), xytext=(
                x, y + 80), color="#ffffff", fontsize=8,
                        bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.15", facecolor="#0055cc",
                                  edgecolor="none", alpha=1))

        elif df["BuyIndex"][i] == "PotentialSell":
            text = f"{df['High'][i]:,.2f}"
            ax.annotate(text, xy=(x, y), xytext=(
                x, y), color="#ffffff", fontsize=7,
                        bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.15", facecolor="#0055cc",
                                  edgecolor="none", alpha=1))


def plotCandlestick(df, ax, ticker):
    mc = mpf.make_marketcolors(up='#0055cc', down='#ff2f92', edge='inherit', wick='inherit',
                               volume='inherit')
    s = mpf.make_mpf_style(base_mpf_style='starsandstripes', rc={'font.size': 6},
                           marketcolors=mc)

    # plot the candlestick chart on ax
    mpf.plot(df, type="candle", ax=ax, style=s, warn_too_much_data=10000000)
    now = datetime.now()
    ax.set_ylabel("%s @ %s" % (ticker, now.strftime("%d/%m/%y %H:%M:%S")))
    ax.yaxis.set_label_position("right")
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
    # plot the KDJ on ax
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


def plotVolume(df, ax):
    ax.set_ylabel("Vol")
    ax.set_xlim(min(df["Datetime"]), max(df["Datetime"]))
    ax.margins(x=0)
    ax.yaxis.set_label_position("right")
    ax.yaxis.set_ticks_position("right")
    ax.bar(df["Datetime"], df["Volume"], width=0.0005, color="#006d21")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.set_xticklabels([])
    ax.set_xticks([])


def calculateDF(df):
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


def plotOneDay(ticker, startTime, endTime):
    # define the ticker symbol
    date_format = mdates.DateFormatter("%d/%m/%y")

    # get data using download method
    df = yf.download(ticker, start=startTime, end=endTime, interval="1d", progress=False)
    df = calculateDF(df)
    df = find_signals(df)

    # Plot stock price, MACD, KDJ, RSI using matplotlib
    plt.rcParams["font.family"] = "Menlo"
    fig = plt.figure(figsize=(16, 9), dpi=300)

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
    fig.savefig("1d %-5s %s %s.png" % (ticker, startTime, endTime), transparent=True, bbox_inches="tight")
    return df


def plotOneMinute(ticker, tradeDay):
    # define the ticker symbol
    date_format = mdates.DateFormatter("%H:%M")

    # get data using download method
    startTime = pendulum.parse(tradeDay + " 00:00")
    endTime = pendulum.parse(tradeDay + " 23:59")
    df = yf.download(ticker, start=startTime, end=endTime, interval="1m", progress=False)

    # convert the index to Eastern Time and remove the timezone
    df.index = pd.DatetimeIndex(df.index).tz_convert("US/Eastern").tz_localize(None)
    df = calculateDF(df)
    df = find_signals(df)

    # Plot stock price, MACD, KDJ, RSI using matplotlib
    plt.rcParams["font.family"] = "Menlo"
    fig = plt.figure(figsize=(16, 9), dpi=300)

    ax1 = plt.subplot2grid((9, 1), (0, 0), rowspan=4)
    ax2 = plt.subplot2grid((9, 1), (4, 0), rowspan=2)
    ax3 = plt.subplot2grid((9, 1), (6, 0), rowspan=1)
    ax4 = plt.subplot2grid((9, 1), (7, 0), rowspan=1)
    ax5 = plt.subplot2grid((9, 1), (8, 0), rowspan=3)

    plotCandlestick(df, ax1, ticker)
    plotMACD(df, ax2, date_format)
    plotRSI(df, ax3)
    plotKDJ(df, ax4)
    plotVolume(df, ax5)

    plotVerticalLines(df, ax2)
    plotVerticalLines(df, ax3)
    plotVerticalLines(df, ax4)
    plotVerticalLines(df, ax5)
    markBuyAndSell(df, ax4)

    # save the figure
    fig.savefig("1m %-5s %s.png" % (ticker, tradeDay), transparent=True, bbox_inches="tight")
    return df


tickers = ["NVDA", "MSFT", "META", "TSM", "GOOGL", "AMZN", "QCOM", "AMD", "ORCL", "VZ", "NFLX", "JPM", "GS",
           "MS",
           "WFC", "BAC",
           "V", "MA", "AXP", "CVX", "XOM", "MCD", "PEP", "KO", "PG", "ABBV", "MRK", "LLY", "UNH", "PFE", "JNJ", "SPY",
           "SPLG"]

today = datetime.today()
date_string = today.strftime("%Y-%m-%d")
date_string_today = today.strftime("%Y-%m-%d")
principal = 10000.00

# # 1. For single stock
# try:
#     plotOneDay("NVDA", "2022-01-01", date_string_today)
#     plotOneMinute("NVDA", "2023-06-30")
# except ArithmeticError as e:
#     print(e)

# 2. For all stocks in the list
now = datetime.now()
print("%s" % (now.strftime("%d/%m/%y %H:%M:%S")))

for x in tickers:
    print("%s" % x)
    print_day_trade(plotOneMinute(x, "2023-06-30"), principal)
    print_day_trade(plotOneDay(x, "2020-01-01", date_string_today), principal)

# # 3. Day trade in recent 30 days
# total = 0.00
# trade_days = generateUSTradeDays("2023-06-01", "2023-06-29")
#
# for i in trade_days:
#     trade_day = str(i)[:10]
#     total += print_day_trade(plotOneMinute("ORCL", trade_day), principal) - principal
#
# print("Total: %10s" % f"{total:,.2f}")
