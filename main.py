import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
import pandas as pd
import pandas_market_calendars as mcal
import yfinance as yf
import ta
import pendulum
from datetime import datetime
from scipy.interpolate import make_interp_spline
import sys


def print_realtime_ratting(df):
    print("Datetime\t\t\tDIR\t\tPrice\tRSI\t\tDIF\t\tDEM")
    for i in range(len(df)):
        current = df["BuyIndex"][i]
        if current == "Buy" or current == "PotentialBuy":
            print("%s\t\033[31mBuy \t%.2f\033[0m\t%5.2f\t%6.2f\t%6.2f" % (
                df["Datetime"][i], df["Low"][i], df["RSI"][i], df["DIF"][i], df["DEM"][i]))
        elif current == "Sell" or current == "PotentialSell":
            print("%s\t\033[34mSell\t%.2f\033[0m\t%5.2f\t%6.2f\t%6.2f" % (
                df["Datetime"][i], df["High"][i], df["RSI"][i], df["DIF"][i], df["DEM"][i]))


def generate_US_trade_days(start_date, end_date):
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

            if (DIF > DEM and DIF_last < DEM_last) and DIF <= 0 and (RSI <= 60) and (J >= K and J >= D):
                df.iloc[i, df.columns.get_loc("BuyIndex")] = "PotentialBuy"
            elif (DIF < DEM and DIF_last > DEM_last) and DIF >= 0 and (RSI >= 40) and (J <= K and J <= D):
                df.iloc[i, df.columns.get_loc("BuyIndex")] = "PotentialSell"
            else:
                df.iloc[i, df.columns.get_loc("BuyIndex")] = "Hold"

        if not flag_can_start and pd.notna(DIF) and pd.notna(DEM):
            flag_can_start = True
            continue

    return df


def print_trade(df, principal):
    margin_limit = 0.00
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
            if current_price >= last_buy_price * (1 + margin_limit):
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
            print("%s\t%-4s\t%5.2f\t%5d\t%6.2f\t%10s\t%10s" % (
                df["Datetime"][i],
                df["BuyIndex"][i],
                df["Low"][i] if df["BuyIndex"][i] == "Buy" else df["High"][i],
                df["Position"][i] if df["Position"][i] > 0 else df["Position"][i - 1],
                df["Commission"][i],
                f"{df['Balance'][i]:,.2f}",
                f"{df['TotalAssets'][i]:,.2f}"))

    return df["TotalAssets"][len(df) - 1]


def plot_vertical_lines(df, ax):
    for i in range(len(df)):
        x_trade = df["Datetime"][i]
        current = df["BuyIndex"][i]
        if current == "Buy" or current == "PotentialBuy":
            ax.axvline(x=x_trade, ymin=0, ymax=3.2, c="#ff2f92", linewidth=0.5, alpha=1, zorder=0, clip_on=False)
        elif current == "Sell" or current == "PotentialSell":
            ax.axvline(x=x_trade, ymin=0, ymax=3.2, c="#0055cc", linewidth=0.5, alpha=1, zorder=0, clip_on=False)


def mark_buy_and_sell(df, ax):
    for i in range(len(df)):
        x_trade = df["Datetime"][i]
        y_trade = -200
        if df["BuyIndex"][i] == "Buy":
            text = "B\n" + f"{df['Low'][i]:,.2f}"
            ax.annotate(text, xy=(x_trade, y_trade), xytext=(
                x_trade, y_trade), color="#ffffff", fontsize=8,
                        bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.15", facecolor="#ff2f92",
                                  edgecolor="none", alpha=1))
        elif df["BuyIndex"][i] == "PotentialBuy":
            text = f"{df['Low'][i]:,.2f}"
            ax.annotate(text, xy=(x_trade, y_trade), xytext=(
                x_trade, y_trade), color="#ffffff", fontsize=7,
                        bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.15", facecolor="#ff2f92",
                                  edgecolor="none", alpha=1))
        elif df["BuyIndex"][i] == "Sell":
            text = "S\n" + f"{df['High'][i]:,.2f}"
            ax.annotate(text, xy=(x_trade, y_trade), xytext=(
                x_trade, y_trade + 80), color="#ffffff", fontsize=8,
                        bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.15", facecolor="#0055cc",
                                  edgecolor="none", alpha=1))
        elif df["BuyIndex"][i] == "PotentialSell":
            text = f"{df['High'][i]:,.2f}"
            ax.annotate(text, xy=(x_trade, y_trade), xytext=(
                x_trade, y_trade), color="#ffffff", fontsize=7,
                        bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.15", facecolor="#0055cc",
                                  edgecolor="none", alpha=1))


def plot_candlestick(df, ax, ticker):
    # plot the candlestick chart on ax
    mc = mpf.make_marketcolors(up='#0055cc', down='#ff2f92', edge='inherit', wick='inherit',
                               volume='inherit')
    s = mpf.make_mpf_style(base_mpf_style='starsandstripes', rc={'font.size': 6},
                           marketcolors=mc)
    mpf.plot(df, type="candle", ax=ax, style=s, warn_too_much_data=10000000)
    ax.set_ylabel("%s @ %s" % (ticker, str(df["Datetime"][len(df) - 1])[:10]))
    ax.yaxis.set_label_position("right")
    [ax.spines[s].set_visible(False) for s in ["top", "right", "bottom", "left"]]
    ax.set_xticklabels([])
    ax.set_xticks([])
    ax.margins(x=0)


def plot_MACD(df, ax, date_format):
    # plot the MACD, signal and histogram on ax
    ax.set_ylabel("MACD")
    ax.set_xlim(min(df["Datetime"]), max(df["Datetime"]))
    ax.margins(x=0)
    ax.xaxis.set_label_position("top")
    ax.xaxis.set_ticks_position("top")
    ax.yaxis.set_label_position("right")
    ax.yaxis.set_ticks_position("right")
    [ax.spines[s].set_visible(False) for s in ["top", "right", "bottom", "left"]]
    ax.xaxis.set_major_formatter(date_format)
    ax.tick_params(axis="x", top=False)
    ax.plot(df["Datetime"], df["DIF"], color="#0055cc", label="DIF", linewidth=1)
    ax.plot(df["Datetime"], df["DEM"], color="#ffa500", label="DEM", linewidth=1)
    ax.bar(df["Datetime"], df["Histogram"], width=[0.0005 if len(df) <= 390 else 2000 / len(df)],
           color=["#006d21" if h >= 0 else "#ff2f92" for h in df["Histogram"]])


def plot_RSI(df, ax):
    # plot the RSI on ax
    ax.set_ylabel("RSI")
    ax.set_xlim(min(df["Datetime"]), max(df["Datetime"]))
    ax.margins(x=0)
    ax.yaxis.set_label_position("right")
    ax.yaxis.set_ticks_position("right")
    ax.plot(df["Datetime"], df["RSI"], label="RSI", color="#0055cc", linewidth=1)
    [ax.spines[s].set_visible(False) for s in ["top", "right", "bottom", "left"]]
    ax.set_xticklabels([])
    ax.set_xticks([])
    ax.set_ylim(0, 100)


def plot_KDJ(df, ax):
    # plot the KDJ on ax
    ax.set_ylabel("KDJ")
    ax.set_xlim(min(df["Datetime"]), max(df["Datetime"]))
    ax.margins(x=0)
    ax.yaxis.set_label_position("right")
    ax.yaxis.set_ticks_position("right")
    ax.plot(df["Datetime"], df["K"], label="K", color="#ff2f92", linewidth=1)
    ax.plot(df["Datetime"], df["D"], label="D", color="#0055cc", linewidth=1)
    ax.plot(df["Datetime"], df["J"], label="J", color="#ffa500", linewidth=1)
    [ax.spines[s].set_visible(False) for s in ["top", "right", "bottom", "left"]]
    ax.set_xticklabels([])
    ax.set_xticks([])
    ax.set_ylim(-200, 200)


def plot_Volume(df, ax):
    ax.set_ylabel("Vol")
    ax.set_xlim(min(df["Datetime"]), max(df["Datetime"]))
    ax.margins(x=0)
    ax.yaxis.set_label_position("right")
    ax.yaxis.set_ticks_position("right")
    [ax.spines[s].set_visible(False) for s in ["top", "right", "bottom", "left"]]
    ax.bar(df["Datetime"], df["Volume"], width=[0.0005 if len(df) <= 390 else 2000 / len(df)], color="#006d21")
    ax.set_ylim(0, max(df["Volume"]))
    ax.set_xticklabels([])
    ax.set_xticks([])

    # Add a smooth fitting line based on df["Volume"]
    x_new = pd.date_range(df["Datetime"].min(), df["Datetime"].max(), periods=300)
    spl = make_interp_spline(df["Datetime"], df["Volume"], k=3)
    volume_smooth = spl(x_new)
    plt.plot(x_new, volume_smooth * 2, color="#ffa500", linewidth=1, alpha=0.8)


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


def plot_stock_screener(df, ticker, type):
    # Plot stock price, MACD, KDJ, RSI using matplotlib
    file_name = ""
    plt.rcParams["font.family"] = "Menlo"
    fig = plt.figure(figsize=(16, 9), dpi=300)

    ax1 = plt.subplot2grid((9, 1), (0, 0), rowspan=4)
    ax2 = plt.subplot2grid((9, 1), (4, 0), rowspan=2)
    ax3 = plt.subplot2grid((9, 1), (6, 0), rowspan=1)
    ax4 = plt.subplot2grid((9, 1), (7, 0), rowspan=1)
    ax5 = plt.subplot2grid((9, 1), (8, 0), rowspan=3)

    plot_candlestick(df, ax1, ticker)
    plot_RSI(df, ax3)
    plot_KDJ(df, ax4)
    plot_Volume(df, ax5)

    plot_vertical_lines(df, ax2)
    plot_vertical_lines(df, ax3)
    plot_vertical_lines(df, ax4)

    mark_buy_and_sell(df, ax4)

    if type == "1d":
        file_name = "1d %-5s %s-%s.png" % (
            ticker, str(df["Datetime"][0])[:10],
            str(df["Datetime"][len(df) - 1])[:10])
        date_format = mdates.DateFormatter("%d/%m/%y")
        plot_MACD(df, ax2, date_format)

    elif type == "1m":
        file_name = "1m %-5s %s.png" % (
            ticker, str(df["Datetime"][len(df) - 1])[:10])
        date_format = mdates.DateFormatter("%H:%M")
        plot_MACD(df, ax2, date_format)
        plot_vertical_lines(df, ax5)

    # save the figure
    fig.savefig(file_name, transparent=True, bbox_inches="tight")


def plotOneDay(ticker, start_time, end_time, principal):
    # get data using download method
    df = yf.download(ticker, start=start_time, end=end_time, interval="1d", progress=False)
    df = calculate_df(df)
    df = find_signals(df)
    df = print_trade(df, principal)

    plot_stock_screener(df, ticker, "1d")

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

    plot_stock_screener(df, ticker, "1m")

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

# 1. For single stock
df = plotOneMinute("NVDA", "2023-06-30", principal)
print_realtime_ratting(df)
print_trade_records(df)

df = plotOneDay("NVDA", "2020-01-01", date_string_today, principal)
print_realtime_ratting(df)
print_trade_records(df)

# # 2. For all stocks in the list
# for x in tickers:
#     now = datetime.now()
#     print("\n%-5s %s" % (x, now.strftime("%d/%m/%y %H:%M:%S")))
#
#     df = plotOneMinute(x, "2023-06-28", principal)
#     print_realtime_ratting(df)
#     print_trade_records(df)
#
#     df = plotOneDay(x, "2020-01-01", date_string_today, principal)
#     print_realtime_ratting(df)
#     print_trade_records(df)

# # 3. Day trade in recent 30 days
# trade_days = generate_US_trade_days("2023-06-04", date_string_today)
#
# for i in trade_days:
#     trade_day = str(i)[:10]
#     df = plotOneMinute("NVDA", trade_day, principal)
#     # print_realtime_ratting(df)
#     principal = print_trade_records(df)
#
# print("Total: %10s" % f"{principal:,.2f}")
