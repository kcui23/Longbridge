import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
import yfinance as yf
import ta
import pendulum
from datetime import datetime
from scipy.interpolate import make_interp_spline
from flask import Flask, render_template, request


def print_realtime_ratting(df):
    print("\nDatetime\t\t\tDIR\t\tPrice\tCRSI\tDIF\t\tDEM\t\tKDJ\t\tAO")
    for i in range(len(df)):
        current = df["BuyIndex"][i]
        if current == "Buy" or current == "PotentialBuy":
            print("%s\t\033[31mBuy \t%.2f\033[0m\t%5.2f\t%6.2f\t%6.2f\t%6.2f\t%6.2f" % (
                df["Datetime"][i],
                df["Low"][i],
                df["CRSI"][i],
                df["DIF"][i],
                df["DEM"][i],
                df["KDJ"][i],
                df["AO"][i]))
        elif current == "Sell" or current == "PotentialSell":
            print("%s\t\033[34mSell\t%.2f\033[0m\t%5.2f\t%6.2f\t%6.2f\t%6.2f\t%6.2f" % (
                df["Datetime"][i],
                df["High"][i],
                df["CRSI"][i],
                df["DIF"][i],
                df["DEM"][i],
                df["KDJ"][i],
                df["AO"][i]))


def print_trade_records(df):
    print("\nDatetime\t\t\tDIR\t\tPrice\tPSN\t\tCMS\t\tBalance\t\tTotal\t\tRemarks")
    for i in range(len(df)):
        direction = df["BuyIndex"][i]

        if direction == "Buy" or direction == "Sell":
            print("%s\t%-4s\t%5.2f\t%5d\t%6.2f\t%10s\t%10s\t%s" % (
                df["Datetime"][i],
                df["BuyIndex"][i],
                df["Low"][i] if df["BuyIndex"][i] == "Buy" else df["High"][i],
                df["Position"][i] if df["Position"][i] > 0 else df["Position"][i - 1],
                df["Commission"][i],
                f"{df['Balance'][i]:,.2f}",
                f"{df['TotalAssets'][i]:,.2f}",
                df["Remarks"][i]))

    return df["TotalAssets"][len(df) - 1]


def generate_US_trade_days(start_date, end_date):
    nyse = mcal.get_calendar('NYSE')
    nasdaq = mcal.get_calendar('NASDAQ')

    nyse_schedule = nyse.schedule(start_date=start_date, end_date=end_date)
    nasdaq_schedule = nasdaq.schedule(start_date=start_date, end_date=end_date)

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
        CRSI = df["CRSI"][i]
        K = df["K"][i]
        D = df["D"][i]
        J = df["J"][i]

        if flag_can_start:
            DIF_last = df["DIF"][i - 1]
            DEM_last = df["DEM"][i - 1]

            if (DIF > DEM and DIF_last < DEM_last) and (J >= K and J >= D) and CRSI <= 70:
                df.iloc[i, df.columns.get_loc("BuyIndex")] = "PotentialBuy"
            elif (DIF < DEM and DIF_last > DEM_last) and (J <= K and J <= D) and CRSI >= 40:
                df.iloc[i, df.columns.get_loc("BuyIndex")] = "PotentialSell"
            else:
                df.iloc[i, df.columns.get_loc("BuyIndex")] = "Hold"

        if not flag_can_start and pd.notna(DIF) and pd.notna(DEM):
            flag_can_start = True
            continue

    return df


def print_trade(df, principal):
    def buy(i):
        direction = "Buy"
        balance = df["Balance"][i]
        current_price = df["Low"][i]
        position = calculate_buy_position(current_price, balance, direction)
        commission = calculate_commission(current_price, position, direction)
        balance = balance - current_price * position - commission

        df.iloc[i, df.columns.get_loc("Position")] = position
        df.iloc[i, df.columns.get_loc("Commission")] = commission
        df.iloc[i, df.columns.get_loc("Balance")] = balance
        df.iloc[i, df.columns.get_loc("BuyIndex")] = direction
        df.iloc[i, df.columns.get_loc("Cost")] = current_price + commission / position

    def sell(i):
        direction = "Sell"
        balance = df["Balance"][i]
        current_price = df["High"][i]
        position = df["Position"][i]
        commission = calculate_commission(current_price, position, direction)

        df.iloc[i, df.columns.get_loc("Position")] = 0
        df.iloc[i, df.columns.get_loc("Balance")] = balance + current_price * position - commission
        df.iloc[i, df.columns.get_loc("Commission")] = commission
        df.iloc[i, df.columns.get_loc("BuyIndex")] = direction
        df.iloc[i, df.columns.get_loc("Cost")] = 0

    take_profit_limit = 0.005
    stop_loss_limit = 0.005
    df["Balance"] = principal
    df["Position"] = 0
    df["Commission"] = 0.00
    df["Cost"] = 0.00
    df["TotalAssets"] = 0.00
    df["Remarks"] = ""

    for i in range(len(df)):
        df.iloc[i, df.columns.get_loc("Balance")] = df["Balance"][i - 1]
        df.iloc[i, df.columns.get_loc("Position")] = df["Position"][i - 1]
        df.iloc[i, df.columns.get_loc("Cost")] = df["Cost"][i - 1]
        position = df["Position"][i]
        direction = df["BuyIndex"][i]

        if direction == "PotentialBuy" and position == 0:
            buy(i)
        elif position > 0:
            current_price = df["High"][i]
            last_buy_price = df["Cost"][i]

            if direction == "PotentialSell" and (current_price >= last_buy_price * (1 + take_profit_limit)):
                sell(i)
                res = last_buy_price * (1 + take_profit_limit)
                df.iloc[i, df.columns.get_loc("Remarks")] = ">= %.2f" % res
            elif current_price <= last_buy_price * (1 - stop_loss_limit):
                sell(i)
                res = last_buy_price * (1 - stop_loss_limit)
                df.iloc[i, df.columns.get_loc("Remarks")] = "<= %.2f" % res

        df.iloc[i, df.columns.get_loc("TotalAssets")] = \
            df["Balance"][i] \
                if df["Position"][i] == 0 else df["Balance"][i] + \
                                               df["Close"][i] * \
                                               df["Position"][i]

    return df


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
        y_trade = -100
        if df["BuyIndex"][i] == "Buy":
            text = "Buy\n" + f"{df['Low'][i]:,.2f}"
            ax.annotate(text, xy=(x_trade, y_trade), xytext=(
                x_trade, y_trade), color="#ffffff", fontsize=8,
                        bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.25", facecolor="#ff2f92",
                                  edgecolor="none", alpha=1))
        elif df["BuyIndex"][i] == "PotentialBuy":
            text = f"{df['Low'][i]:,.2f}"
            ax.annotate(text, xy=(x_trade, y_trade), xytext=(
                x_trade, y_trade), color="#ffffff", fontsize=7,
                        bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.25", facecolor="#ff2f92",
                                  edgecolor="none", alpha=1))
        elif df["BuyIndex"][i] == "Sell":
            text = "Sell\n" + f"{df['High'][i]:,.2f}"
            ax.annotate(text, xy=(x_trade, y_trade), xytext=(
                x_trade, y_trade + 80), color="#ffffff", fontsize=8,
                        bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.25", facecolor="#0055cc",
                                  edgecolor="none", alpha=1))
        elif df["BuyIndex"][i] == "PotentialSell":
            text = f"{df['High'][i]:,.2f}"
            ax.annotate(text, xy=(x_trade, y_trade), xytext=(
                x_trade, y_trade), color="#ffffff", fontsize=7,
                        bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.25", facecolor="#0055cc",
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
    ax.tick_params(axis="y", labelsize=7, labelcolor="#0055cc", length=0)
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
    ax.set_yticklabels([])
    ax.set_yticks([])
    [ax.spines[s].set_visible(False) for s in ["top", "right", "bottom", "left"]]
    ax.xaxis.set_major_formatter(date_format)
    ax.tick_params(axis="x", labelsize=7, labelcolor="#0055cc", top=False)

    ax.plot(df["Datetime"], df["DIF"], color="#0055cc", label="DIF", linewidth=1)
    ax.plot(df["Datetime"], df["DEM"], color="#ffa500", label="DEM", linewidth=1)
    ax.bar(df["Datetime"], df["Histogram"], width=[0.0005 if len(df) <= 390 else 2000 / len(df)],
           color=["#006d21" if h >= 0 else "#ff2f92" for h in df["Histogram"]])


def plot_RSI(df, ax):
    # plot the RSI on ax
    ax.set_ylabel("CRSI")
    ax.set_xlim(min(df["Datetime"]), max(df["Datetime"]))
    ax.margins(x=0)
    ax.yaxis.set_label_position("right")
    ax.yaxis.set_ticks_position("right")
    ax.plot(df["Datetime"], df["CRSI"], label="CRSI", color="#0055cc", linewidth=1)
    ax.plot(df["Datetime"], df["RSI"], label="RSI", color="#ff2f92", linewidth=1, alpha=0.5)
    [ax.spines[s].set_visible(False) for s in ["top", "right", "bottom", "left"]]
    ax.set_xticklabels([])
    ax.set_xticks([])
    ax.set_yticklabels([])
    ax.set_yticks([])
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
    ax.set_yticklabels([])
    ax.set_yticks([])
    ax.set_ylim(-100, 200)


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
    ax.set_yticklabels([])
    ax.set_yticks([])

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
    df["K"] = ta.momentum.StochasticOscillator(df["High"], df["Low"], df["Close"], window=9).stoch()
    df["D"] = df["K"].ewm(com=2).mean()
    df["J"] = 3 * df["K"] - 2 * df["D"]

    df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()
    df["CRSI"] = (df["RSI"] + 2 * df["RSI"].shift(1) + 3 * df["RSI"].shift(2) + 4 * df["RSI"].shift(3)) / 10

    df["CCI"] = ta.trend.CCIIndicator(df["High"], df["Low"], df["Close"], window=20, constant=0.015).cci()
    df["AO"] = df[["High", "Low"]].mean(axis=1).rolling(5).mean().sub(
        df[["High", "Low"]].mean(axis=1).rolling(34).mean())
    df["SMA"] = df["Close"].rolling(20).mean()
    df["STD"] = df["Close"].rolling(20).std()
    df["Upper Band"] = df["SMA"].add(df["STD"].mul(2))
    df["Lower Band"] = df["SMA"].sub(df["STD"].mul(2))

    return df


def plot_stock_screener(df, ticker, type):
    # Plot stock price, MACD, KDJ, RSI using matplotlib
    file_name = ""
    plt.rcParams["font.family"] = "Menlo"
    fig = plt.figure(figsize=(20, 9), dpi=300)

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
        file_name = "1d %-5s %s %s.png" % (
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
    fig.savefig(file_name, transparent=False, bbox_inches="tight")


def plotOneDay(ticker, start_time, end_time):
    # get data using download method
    df = yf.download(ticker, start=start_time, end=end_time, interval="1d", progress=False)
    df = calculate_df(df)
    df = find_signals(df)

    return df


def plotOneMinute(ticker, trade_day):
    # get data using download method
    start_time = pendulum.parse(trade_day + " 00:00:00")
    end_time = pendulum.parse(trade_day + " 23:59:59")

    # convert the index to Eastern Time and remove the timezone
    df = yf.download(ticker, start=start_time, end=end_time, interval="1m", progress=False)
    df.index = pd.DatetimeIndex(df.index).tz_convert("US/Eastern").tz_localize(None)

    df = calculate_df(df)
    df = find_signals(df)

    return df


def print_all_stocks(trade_day, principal):
    # For all stocks in the list
    for ticker in tickers:
        now = datetime.now()
        print("\n%-5s %s" % (ticker, now.strftime("%d/%m/%y %H:%M:%S")))

        df = plotOneMinute(ticker, trade_day)
        df = print_trade(df, principal)
        print_realtime_ratting(df)
        print(f"{print_trade_records(df):,.2f}", ticker)
        plot_stock_screener(df, ticker, "1m")

        df = plotOneDay(ticker, "2020-01-01", date_string_today)
        df = print_trade(df, principal)
        print_realtime_ratting(df)
        print(f"{print_trade_records(df):,.2f}", ticker)
        plot_stock_screener(df, ticker, "1d")


def print_stock_recent(ticker, start_date, end_date, principal):
    # For a stock in recent 30 days
    trade_days = generate_US_trade_days(start_date, end_date)

    for i in trade_days:
        trade_day = str(i)[:10]
        df = plotOneMinute(ticker, trade_day)
        df = print_trade(df, principal)
        print_realtime_ratting(df)
        principal = print_trade_records(df)

    print("\nTotal: %10s" % f"{principal:,.2f}")


tickers = [
    # "2800.hk", "0005.hk", "0700.hk", "2388.hk", "2888.hk",
    "MSFT", "NVDA", "TSM", "GOOGL", "META",
    "ORCL", "AMZN", "QCOM", "AMD", "VZ",
    "NFLX", "ASML", "JPM", "GS", "MS",
    "WFC", "BAC", "V", "MA", "AXP",
    "CVX", "XOM", "TSLA", "SPLG"
]

today = datetime.today()
date_string = today.strftime("%Y-%m-%d")
date_string_today = today.strftime("%Y-%m-%d")
principal = 10000

# print_all_stocks("2023-06-28", principal)
# print_stock_recent("AMD", "2020-01-01", "2023-07-06",principal)

# Start of web
app = Flask(__name__, template_folder="template")


@app.route("/query", methods=["GET", "POST"])
def handle_query():
    if request.method == "POST":

        trade_date = request.form["trade_date"]
        res = np.array([["APPL", 0.00, 0.00, 0.00, "", "", "", ""]])

        for ticker in tickers:

            now = datetime.now()
            print("Trade date: %s\tTicker: %-5s\tCalculation date: %s" % (
                trade_date, ticker, now.strftime("%d/%m/%y %H:%M:%S")))

            df = plotOneMinute(ticker, trade_date)
            print_realtime_ratting(df)

            buyTime, sellTime = "", ""
            buyPrice, sellPrice = 0.00, 0.00

            for i in range(len(df) - 1, -1, -1):
                if df["BuyIndex"][i] == "PotentialBuy" and buyTime == "":
                    buyTime = datetime.strftime(df["Datetime"][i], "%d/%m %H:%M")
                    buyPrice = df["Low"][i]
                elif df["BuyIndex"][i] == "PotentialSell" and sellTime == "":
                    sellTime = datetime.strftime(df["Datetime"][i], "%d/%m %H:%M")
                    sellPrice = df["High"][i]

            current = [
                ticker,
                f"{df['CRSI'][len(df) - 1]:,.2f}",
                f"{df['KDJ'][len(df) - 1]:,.2f}",
                f"{df['Close'][len(df) - 1]:,.2f}",
                f"%s\n%s" % (buyTime, f"{buyPrice:,.2f}"),
                f"%s\n%s" % (sellTime, f"{sellPrice:,.2f}"),
                "",
                "",
            ]

            res = np.append(res, [current], axis=0)

        return render_template("home.html", data=res[1:])
    else:
        return render_template("home.html")


@app.route("/")
def home():
    handle_query()


if __name__ == "__main__":
    app.run(host="localhost", port=8088, debug=None)
    # app.run(host="194.233.83.43", port=8088, debug=None)
    # app.run(host="109.123.236.116", port=8088, debug=None)
