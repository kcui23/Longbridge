# import libraries
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
import pandas as pd
import yfinance as yf
import ta
from datetime import datetime, timedelta


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

    # Plot stock price, MACD, KDJ, RSI using matplotlib
    plt.rcParams["font.family"] = "Menlo"
    fig = plt.figure(figsize=(16, 8), dpi=300)

    ax1 = plt.subplot2grid((8, 1), (0, 0), rowspan=4)
    ax2 = plt.subplot2grid((8, 1), (4, 0), rowspan=2)
    ax3 = plt.subplot2grid((8, 1), (6, 0), rowspan=1)
    ax4 = plt.subplot2grid((8, 1), (7, 0), rowspan=1)

    # create a custom style using mpf.make_mpf_style
    mc = mpf.make_marketcolors(up='#0055cc', down='#ff2f92', edge='inherit', wick='inherit',
                               volume='inherit')
    s = mpf.make_mpf_style(base_mpf_style='starsandstripes', rc={'font.size': 6},
                           marketcolors=mc)

    # plot the candlestick chart on ax1
    mpf.plot(df, type="candle", ax=ax1, style=s, warn_too_much_data=10000000)

    ax1.set_ylabel("%s (%s %s)" % (ticker, startTime, endTime))
    ax1.yaxis.set_label_position("right")
    ax1.yaxis.set_ticks_position("right")
    ax1.spines["top"].set_visible(False)
    ax1.spines["bottom"].set_visible(False)
    ax1.spines["left"].set_visible(False)
    ax1.set_xticklabels([])
    ax1.set_xticks([])

    # plot the MACD, signal and histogram on ax2
    ax2.set_ylabel("MACD")
    ax2.xaxis.set_label_position("top")
    ax2.xaxis.set_ticks_position("top")
    ax2.yaxis.set_label_position("right")
    ax2.yaxis.set_ticks_position("right")
    ax2.plot(df["Datetime"], df["DIF"], color="#0055cc", label="DIF")
    ax2.plot(df["Datetime"], df["DEM"], color="#ffa500", label="DEM")
    ax2.fill_between(df["Datetime"], df["Histogram"], 0, where=(df["Histogram"] > 0), color="#006d21", alpha=0.5)
    ax2.fill_between(df["Datetime"], df["Histogram"], 0, where=(df["Histogram"] <= 0), color="#ff2f92", alpha=0.5)
    ax2.spines["top"].set_visible(False)
    ax2.spines["bottom"].set_visible(False)
    ax2.spines["left"].set_visible(False)
    ax2.xaxis.set_major_formatter(date_format)
    ax2.tick_params(axis="x", bottom=False)

    # plot the RSI on ax3
    ax3.set_ylabel("RSI")
    ax3.yaxis.set_label_position("right")
    ax3.yaxis.set_ticks_position("right")
    ax3.plot(df["Datetime"], df["RSI"], label="RSI", color="#ff2f92")
    ax3.axhline(70, linestyle="-", color="#ffa500", linewidth=0.5, alpha=0.5)
    ax3.axhline(30, linestyle="-", color="#006d21", linewidth=0.5, alpha=0.5)
    ax3.spines["top"].set_visible(False)
    ax3.spines["bottom"].set_visible(False)
    ax3.spines["left"].set_visible(False)
    ax3.set_xticklabels([])
    ax3.set_xticks([])
    ax3.set_ylim(0, 100)

    # plot the KDJ on ax4
    ax4.set_ylabel("KDJ")
    ax4.yaxis.set_label_position("right")
    ax4.yaxis.set_ticks_position("right")
    ax4.plot(df["Datetime"], df["K"], label="K", color="#ff2f92")
    ax4.plot(df["Datetime"], df["D"], label="D", color="#0055cc")
    ax4.plot(df["Datetime"], df["J"], label="J", color="#ffa500")
    ax4.spines["top"].set_visible(False)
    ax4.spines["bottom"].set_visible(False)
    ax4.spines["left"].set_visible(False)
    ax4.set_xticklabels([])
    ax4.set_xticks([])
    ax4.set_ylim(-100, 200)

    # save the figure
    fig.savefig("%-5s 1d %s %s.png" % (ticker, startTime, endTime), transparent=True)
    return df


def plotOneMinute(ticker, startTime, endTime):
    # define the ticker symbol
    date_format = mdates.DateFormatter("%H:%M")

    # get data using download method
    df = yf.download(ticker, start=startTime, end=endTime, interval="1m")

    # convert the index to Eastern Time and remove the timezone
    df.index = df.index.tz_convert("US/Eastern").tz_localize(None)
    df = calculateDF(df)

    # Plot stock price, MACD, KDJ, RSI using matplotlib
    plt.rcParams["font.family"] = "Menlo"
    fig = plt.figure(figsize=(16, 8), dpi=300)

    ax1 = plt.subplot2grid((8, 1), (0, 0), rowspan=4)
    ax2 = plt.subplot2grid((8, 1), (4, 0), rowspan=2)
    ax3 = plt.subplot2grid((8, 1), (6, 0), rowspan=1)
    ax4 = plt.subplot2grid((8, 1), (7, 0), rowspan=1)

    # create a custom style using mpf.make_mpf_style
    mc = mpf.make_marketcolors(up='#0055cc', down='#ff2f92', edge='inherit', wick='inherit',
                               volume='inherit')
    s = mpf.make_mpf_style(base_mpf_style='starsandstripes', rc={'font.size': 6},
                           marketcolors=mc)

    # plot the candlestick chart on ax1
    mpf.plot(df, type="candle", ax=ax1, style=s)

    ax1.set_ylabel("%s (%s %s)" % (ticker, startTime, endTime))
    ax1.yaxis.set_label_position("right")
    ax1.yaxis.set_ticks_position("right")
    ax1.spines["top"].set_visible(False)
    ax1.spines["bottom"].set_visible(False)
    ax1.spines["left"].set_visible(False)
    ax1.set_xticklabels([])
    ax1.set_xticks([])

    # plot the MACD, signal and histogram on ax2
    ax2.set_ylabel("MACD")
    ax2.xaxis.set_label_position("top")
    ax2.xaxis.set_ticks_position("top")
    ax2.yaxis.set_label_position("right")
    ax2.yaxis.set_ticks_position("right")
    ax2.plot(df["Datetime"], df["DIF"], color="#0055cc", label="DIF")
    ax2.plot(df["Datetime"], df["DEM"], color="#ffa500", label="DEM")
    ax2.fill_between(df["Datetime"], df["Histogram"], 0, where=(df["Histogram"] > 0), color="#006d21", alpha=0.5)
    ax2.fill_between(df["Datetime"], df["Histogram"], 0, where=(df["Histogram"] <= 0), color="#ff2f92", alpha=0.5)
    ax2.spines["top"].set_visible(False)
    ax2.spines["bottom"].set_visible(False)
    ax2.spines["left"].set_visible(False)
    ax2.xaxis.set_major_formatter(date_format)
    ax2.tick_params(axis="x", bottom=False)

    # plot the RSI on ax3
    ax3.set_ylabel("RSI")
    ax3.yaxis.set_label_position("right")
    ax3.yaxis.set_ticks_position("right")
    ax3.plot(df["Datetime"], df["RSI"], label="RSI", color="#ff2f92")
    ax3.axhline(70, linestyle="-", color="#ffa500", linewidth=0.5, alpha=0.5)
    ax3.axhline(30, linestyle="-", color="#006d21", linewidth=0.5, alpha=0.5)
    ax3.spines["top"].set_visible(False)
    ax3.spines["bottom"].set_visible(False)
    ax3.spines["left"].set_visible(False)
    ax3.set_xticklabels([])
    ax3.set_xticks([])
    ax3.set_ylim(0, 100)

    # plot the KDJ on ax4
    ax4.set_ylabel("KDJ")
    ax4.yaxis.set_label_position("right")
    ax4.yaxis.set_ticks_position("right")
    ax4.plot(df["Datetime"], df["K"], label="K", color="#ff2f92")
    ax4.plot(df["Datetime"], df["D"], label="D", color="#0055cc")
    ax4.plot(df["Datetime"], df["J"], label="J", color="#ffa500")
    ax4.spines["top"].set_visible(False)
    ax4.spines["bottom"].set_visible(False)
    ax4.spines["left"].set_visible(False)
    ax4.set_xticklabels([])
    ax4.set_xticks([])
    ax4.set_ylim(-100, 200)

    # save the figure
    fig.savefig("%-5s 1m %s %s.png" % (ticker, startTime, endTime), transparent=True)
    return df


def printDF(df):
    # Open
    # High
    # Low
    # Close
    # Adj
    # Close
    # Volume
    # Date
    # DIF
    # DEM
    # Histogram
    # KDJ
    # RSI
    # K
    # D
    # J

    # "Datetime: %s, Open: %.2f, High %.2f, Low: %.2f, Close: %.2f, Volume: %d, DIF: %.2f, DEM: %.2f, Histogram: %.2f, RSI: .2f" %
    for x in df.index:
        print("Datetime: %s\tOpen: %.2f\tDIF: %.4f\tDEM: %.4f\tHistogram: %.4f\t" % (x, df["Open"][x], df["DIF"][x], df["DEM"][x], df["Histogram"][x]))
        # print(x, df["Open"][x], df["High"][x], df["Low"][x], df["Close"][x], df["Volume"][x], df["DIF"][x],
        #       df["DEM"][x], df["Histogram"][x], df["RSI"][x])


today = datetime.today()
date_string = today.strftime("%Y-%m-%d")

tickers = ["NVDA", "MSFT", "META", "TSM", "GOOGL", "AMZN", "QCOM", "AMD", "ORCL", "VZ", "JPM", "BAC", "GS", "WFC", "MS",
           "V", "MA", "AXP", "CVX", "XOM", "MCD", "PEP", "KO", "PG", "ABBV", "MRK", "LLY", "UNH", "PFE", "JNJ", "SPY",
           "SPLG"]
today = datetime.today()
yesterday = today - timedelta(days=1)
date_string_today = today.strftime("%Y-%m-%d")
date_string_yesterday = today.strftime("%Y-%m-%d")

for x in tickers:
    printDF(plotOneMinute(x, "2023-06-27", date_string_today))
    printDF(plotOneDay(x, "2021-01-01", date_string_today))
