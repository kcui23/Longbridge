import sys
import matplotlib.pyplot as plt
import mplfinance as mpf
import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
import yfinance as yf
import ta
import pendulum
from datetime import datetime, timedelta
from flask import Flask, render_template, request


def print_realtime_ratting(df):
    print("\nDatetime\t\t\tDIR\t\tPrice\tCRSI\tDIF\t\tDEM\t\tKDJ\t\tAO")
    for i in range(len(df)):
        current = df["BuyIndex"][i]
        if current == "Buy" or current == "PotentialBuy":
            print("%s\t\033[31mBuy \t%.2f\033[0m\t%5.2f\t%6.2f\t%6.2f\t%6.2f\t%6.2f" % (
                str(df["Datetime"][i])[:16],
                df["Low"][i],
                df["CRSI"][i],
                df["DIF"][i],
                df["DEM"][i],
                df["KDJ"][i],
                df["AO"][i]))
        elif current == "Sell" or current == "PotentialSell":
            print("%s\t\033[34mSell\t%.2f\033[0m\t%5.2f\t%6.2f\t%6.2f\t%6.2f\t%6.2f" % (
                str(df["Datetime"][i])[:16],
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
                str(df["Datetime"][i])[:16],
                df["BuyIndex"][i],
                df["Low"][i] if df["BuyIndex"][i] == "Buy" else df["High"][i],
                df["Position"][i] if df["Position"][i] > 0 else df["Position"][i - 1],
                df["Commission"][i],
                f"{df['Balance'][i]:,.2f}",
                f"{df['TotalAssets'][i]:,.2f}",
                df["Remarks"][i]))

    return df["TotalAssets"][len(df) - 1]


def distinguish_interval(df):
    res = {60: "1m", 900: "15m", 1800: "30m", 3600: "60m", 86400: "1d"}

    datetime_first = datetime.strptime(str(df["Datetime"][0])[:19], "%Y-%m-%d %H:%M:%S")
    datetime_second = datetime.strptime(str(df["Datetime"][1])[:19], "%Y-%m-%d %H:%M:%S")
    difference = int((datetime_second - datetime_first).total_seconds())

    return res.get(difference, None)


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


def paper_trade(df, principal):
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
        df.iloc[i, df.columns.get_loc("Cost")] = current_price + commission / max(position, 1)

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
        df.iloc[i, df.columns.get_loc("Cost")] = current_price - commission / max(position, 1)

    take_profit_limit = 0.005
    stop_loss_limit = 0.005
    buy_lower_limit = 0.01
    df["Balance"] = principal
    df["Position"] = 0
    df["Commission"] = 0.00
    df["Cost"] = sys.float_info.max
    df["TotalAssets"] = 0.00
    df["Remarks"] = ""

    count_operation = 0  # Mark to make first buy in PotentialBuy

    for i in range(len(df)):
        df.iloc[i, df.columns.get_loc("Balance")] = df["Balance"][i - 1]
        df.iloc[i, df.columns.get_loc("Position")] = df["Position"][i - 1]
        df.iloc[i, df.columns.get_loc("Cost")] = df["Cost"][i - 1]

        position = df["Position"][i]
        direction = df["BuyIndex"][i]
        current_price = df["High"][i]
        last_buy_price = df["Cost"][i]

        if position == 0:
            if direction == "PotentialBuy":
                buy(i)
                count_operation += 1
                df.iloc[i, df.columns.get_loc("Remarks")] = "(%d)" % count_operation
            elif current_price <= last_buy_price * (1 - buy_lower_limit) and count_operation > 0:
                buy(i)
                count_operation += 1
                res = last_buy_price * (1 - buy_lower_limit)
                df.iloc[i, df.columns.get_loc("Remarks")] = "(%d) <= %.2f Second buy" % (count_operation, res)
        elif position > 0:
            if direction == "PotentialSell" and current_price >= last_buy_price * (1 + take_profit_limit):
                sell(i)
                count_operation += 1
                res = last_buy_price * (1 + take_profit_limit)
                df.iloc[i, df.columns.get_loc("Remarks")] = "(%d) >= %.2f Take profit" % (
                    count_operation, res)
            elif current_price <= last_buy_price * (1 - stop_loss_limit):
                sell(i)
                count_operation += 1
                res = last_buy_price * (1 - stop_loss_limit)
                df.iloc[i, df.columns.get_loc("Remarks")] = "(%d) <= %.2f Stop loss" % (count_operation, res)

        df.iloc[i, df.columns.get_loc("TotalAssets")] = \
            df["Balance"][i] if df["Position"][i] == 0 else df["Balance"][i] + df["Close"][i] * df["Position"][i]

    return df


def calculate_df(df):
    df["Datetime"] = pd.to_datetime(df.index)

    df["DIF"] = ta.trend.MACD(df["Close"], window_slow=26, window_fast=12).macd()
    df["DEM"] = df["DIF"].ewm(span=9).mean()
    df["Histogram"] = df["DIF"] - df["DEM"].ewm(span=9).mean()

    df["KDJ"] = ta.momentum.StochasticOscillator(df["High"], df["Low"], df["Close"]).stoch()
    df["K"] = ta.momentum.StochasticOscillator(df["High"], df["Low"], df["Close"], window=9).stoch()
    df["D"] = df["K"].ewm(com=2).mean()
    df["J"] = 3 * df["K"] - 2 * df["D"]

    df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()
    df["CRSI"] = (df["RSI"] + 2 * df["RSI"].shift(1) + 3 * df["RSI"].shift(2) + 4 * df["RSI"].shift(3)) / 10

    vwap = ta.volume.VolumeWeightedAveragePrice(
        high=df["High"], low=df["Low"], close=df["Close"], volume=df["Volume"],
        window=14)
    df["VWAP"] = vwap.volume_weighted_average_price()

    return df


def plot_stock_screener(df, ticker):
    def plot_configuration():
        [ax1.spines[s].set_visible(False) for s in ["top", "right", "bottom", "left"]]
        [ax2.spines[s].set_visible(False) for s in ["top", "right", "bottom", "left"]]
        [ax3.spines[s].set_visible(False) for s in ["top", "right", "bottom", "left"]]
        [ax4.spines[s].set_visible(False) for s in ["top", "right", "bottom", "left"]]
        [ax5.spines[s].set_visible(False) for s in ["top", "right", "bottom", "left"]]

        ax1.margins(x=0, y=0)
        ax1.tick_params(bottom=False)
        ax1.tick_params(labelbottom=False)
        ax1.tick_params(right=False)

        ax2.tick_params(bottom=False)
        ax2.tick_params(labelbottom=False)
        ax2.set_yticklabels([])
        ax2.set_yticks([])

        ax3.set_ylim(0, 100)
        ax3.tick_params(bottom=False)
        ax3.tick_params(labelbottom=False)
        ax3.set_yticklabels([])
        ax3.set_yticks([])
        ax3.fill_between(np.arange(len(df)), 30, 70, color='#0055cc', edgecolor='none', alpha=0.15)

        ax4.set_ylim(-100, 200)
        ax4.tick_params(bottom=False)
        ax4.tick_params(labelbottom=False)
        ax4.set_yticklabels([])
        ax4.set_yticks([])

        ax5.set_ylabel("")
        ax5.set_yticklabels([])
        ax5.set_yticks([])
        ax5.tick_params(bottom=False)

        plt.rcParams['font.family'] = 'Menlo'

    def add_vertical_lines(ax):
        for i in range(len(df)):
            current = df["BuyIndex"][i]
            if current == "Buy" or current == "PotentialBuy":
                ax.axvline(x=i, ymin=0, ymax=5.5, c="#ff2f92", linewidth=0.25, alpha=0.65, zorder=0, clip_on=False)
            elif current == "Sell" or current == "PotentialSell":
                ax.axvline(x=i, ymin=0, ymax=5.5, c="#0055cc", linewidth=0.25, alpha=0.65, zorder=0, clip_on=False)

    def add_buy_and_sell(ax):

        height = int(max(df["High"]) - min(df["Low"]))
        height_offset = 10
        alpha_value = 0.8

        for i in range(len(df)):
            current = df["BuyIndex"][i]
            if current == "Buy":
                text = "B\n" + f"{df['Low'][i]:,.2f}"
                ax.annotate(
                    text, xy=(i, df['Low'][i]),
                    xytext=(i, df["Low"][i] - height / height_offset), color="#ffffff", fontsize=8,
                    bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.25", facecolor="#ff2f92",
                              edgecolor="none", alpha=alpha_value))
            elif current == "PotentialBuy":
                ax.annotate(
                    f"{df['Low'][i]:,.2f}",
                    xy=(i, df['Low'][i]),
                    xytext=(i, df["Low"][i] - height / height_offset), color="#ffffff", fontsize=7,
                    bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.25", facecolor="#ff2f92",
                              edgecolor="none", alpha=alpha_value))
            elif current == "Sell":
                text = "S\n" + f"{df['High'][i]:,.2f}"
                ax.annotate(
                    text,
                    xy=(i, df['High'][i]),
                    xytext=(i, df["High"][i] + height / height_offset), color="#ffffff", fontsize=8,
                    bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.25", facecolor="#0055cc",
                              edgecolor="none", alpha=alpha_value))
            elif current == "PotentialSell":
                ax.annotate(
                    f"{df['High'][i]:,.2f}",
                    xy=(i, df['Low'][i]),
                    xytext=(i, df["Low"][i] + height / height_offset), color="#ffffff", fontsize=7,
                    bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.25", facecolor="#0055cc",
                              edgecolor="none", alpha=alpha_value))

            if current == "Buy" or current == "PotentialBuy":
                ax.axvline(
                    x=i,
                    ymin=(df["Low"][i] - min(df["Low"]) - (height / height_offset) / 2) / height,
                    ymax=(df["Low"][i] - min(df["Low"]) - (height / height_offset) / 5) / height,
                    c="#ff2f92",
                    linewidth=0.25,
                    alpha=alpha_value, zorder=0, clip_on=False)
            elif current == "Sell" or current == "PotentialSell":
                ax.axvline(
                    x=i,
                    ymin=(df["High"][i] - min(df["High"]) + (height / height_offset) / 5) / height,
                    ymax=(df["High"][i] - min(df["High"]) + (height / height_offset) / 2) / height,
                    c="#0055cc",
                    linewidth=0.25,
                    alpha=alpha_value, zorder=0, clip_on=False)

    fig = plt.figure(figsize=(20, 9), dpi=300)

    ax1 = plt.subplot2grid((9, 1), (0, 0), rowspan=4)
    ax2 = plt.subplot2grid((9, 1), (4, 0), rowspan=2, sharex=ax1)
    ax3 = plt.subplot2grid((9, 1), (6, 0), rowspan=1, sharex=ax1)
    ax4 = plt.subplot2grid((9, 1), (7, 0), rowspan=1, sharex=ax1)
    ax5 = plt.subplot2grid((9, 1), (8, 0), rowspan=3, sharex=ax1)

    mc = mpf.make_marketcolors(
        up="#0055cc",
        down="#ff2f92",
        edge="inherit",
        wick="inherit",
        volume={"up": "#006d21", "down": "#ff2f92"}
    )

    s = mpf.make_mpf_style(
        base_mpf_style="starsandstripes",
        marketcolors=mc,
        rc={},
        gridstyle="",
    )

    line_width = 0.85

    vwap = mpf.make_addplot(df["VWAP"], ax=ax1, color="#006d21", width=line_width, alpha=0.35)

    macd_DIF = mpf.make_addplot(df["DIF"], ax=ax2, color="#0055cc", width=line_width)
    macd_DEM = mpf.make_addplot(df["DEM"], ax=ax2, color="#ffa500", width=line_width)
    macd_Histogram = mpf.make_addplot(
        df["Histogram"], type="bar", ax=ax2,
        color=["#006d21" if h >= 0 else "#ff2f92" for h in df["Histogram"]])

    rsi = mpf.make_addplot(df["RSI"], ax=ax3, color="#ff2f92", width=line_width)
    crsi = mpf.make_addplot(df["CRSI"], ax=ax3, color="#0055cc", width=line_width)

    kdj_k = mpf.make_addplot(df["K"], ax=ax4, color="#ff2f92", width=line_width)
    kdj_d = mpf.make_addplot(df["D"], ax=ax4, color="#0055cc", width=line_width)
    kdj_j = mpf.make_addplot(df["J"], ax=ax4, color="#ffa500", width=line_width)

    plots = [vwap, macd_DIF, macd_DEM, macd_Histogram, rsi, crsi, kdj_k, kdj_d, kdj_j]

    file_name = "images/" + distinguish_interval(df) + " " + ticker + " " + str(df["Datetime"][0])[:10] + " " + str(
        df["Datetime"][len(df) - 1])[:10]

    mpf.plot(
        df, type="candle", ax=ax1, style=s, addplot=plots,
        volume=ax5,
        ylabel=file_name,
        ylabel_lower="",
        tight_layout=True,
        datetime_format="%y/%m/%d\n%H:%M",
        xrotation=0,
        returnfig=False,
        **(dict(warn_too_much_data=len(df) + 1)),
    )

    add_buy_and_sell(ax1)
    add_vertical_lines(ax5)
    plot_configuration()

    fig.savefig(file_name + ".png", transparent=False, bbox_inches='tight')


def get_df_interval(ticker, trade_date, interval, days):
    current_date = datetime.now()
    start_date = (current_date - timedelta(days=days)).strftime("%Y-%m-%d")
    start_time = pendulum.parse(start_date + " 00:00:00")
    end_time = pendulum.parse(trade_date + " 23:59:59")

    df = yf.download(ticker, start=start_time, end=end_time, interval=interval, progress=False)
    if interval == "1m":
        df.index = pd.DatetimeIndex(df.index).tz_convert("US/Eastern").tz_localize(None)
    else:
        df.index = df.index.tz_localize("UTC")
        df.index = df.index.tz_convert("US/Eastern")

    df = calculate_df(df)
    df = find_signals(df)

    return df


def test_all_stocks(trade_day, principal):
    for ticker in tickers:
        for key, value in interval_type.items():
            df = get_df_interval(ticker, trade_day, key, value)
            df = paper_trade(df, principal)
            # print_realtime_ratting(df)
            plot_stock_screener(df, ticker)

            print("\n%-5s (%s)\nFrom %s\nTo   %s\nEarning %13s" % (
                ticker,
                distinguish_interval(df),
                str(df["Datetime"][0])[:16],
                str(df["Datetime"][len(df) - 1])[:16],
                f"{print_trade_records(df) - principal:,.2f}",
            ))


tickers = [
    # "2800.hk", "0005.hk", "0700.hk", "2388.hk", "2888.hk",
    "MSFT", "NVDA", "GOOGL", "TSM", "AMZN",
    "META", "ORCL", "AMD", "ADBE", "QCOM",
    "NFLX", "ASML", "AVGO", "VZ", "GS",
    "JPM", "MS", "WFC", "BAC", "C",
    "V", "MA", "AXP", "XOM", "CVX",
    "TSLA", "MCD", "KO", "PEP", "PG",
    "ABBV", "MRK", "LLY", "UNH", "PFE",
    "JNJ", "SPLG", "QQQ"
]

interval_type = {
    "1m": 3, "15m": 59, "30m": 59, "60m": 180, "1d": 500
}

today = datetime.today()
date_string = today.strftime("%Y-%m-%d")
date_string_today = today.strftime("%Y-%m-%d")
principal = 10000

# # 1. Single test
# for key, value in interval_type.items():
#     df = get_df_interval("0700.hk", "2023-07-12", key, value)
#     df = paper_trade(df, principal)
#     print_realtime_ratting(df)
#     print("\n%-5s %18s (%s)" % (ticker, f"{print_trade_records(df):,.2f}", distinguish_interval(df)))
#     plot_stock_screener(df, "0700.hk")

# 2. All test
test_all_stocks("2023-07-11", principal)


# Start of web
def prepare_web_content(trade_date):
    def find_timing(df):
        buyTime, sellTime = "", ""
        buyPrice, sellPrice = 0.00, 0.00
        for i in range(len(df) - 1, -1, -1):
            if df["BuyIndex"][i] == "PotentialBuy" and buyTime == "":
                buyTime = datetime.strftime(df["Datetime"][i], "%d/%m %H:%M")
                buyPrice = df["Low"][i]
            elif df["BuyIndex"][i] == "PotentialSell" and sellTime == "":
                sellTime = datetime.strftime(df["Datetime"][i], "%d/%m %H:%M")
                sellPrice = df["High"][i]

        return f"%s\n%s" % (buyTime, f"{buyPrice:,.2f}"), f"%s\n%s" % (sellTime, f"{sellPrice:,.2f}")

    res = np.array([["APPL", 0.00, 0.00, "", "", "", "", "", "", "", "", "", ""]])

    for ticker in tickers:
        now = datetime.now()
        print("Trade date: %s\tTicker: %-5s\tCalculation date: %s" % (
            trade_date, ticker, now.strftime("%d/%m/%y %H:%M:%S")))

        df = get_df_interval(ticker, trade_date, "1m", interval_type.get("1m"))
        current = [
            ticker, f"{df['CRSI'][len(df) - 1]:,.2f}", f"{df['Close'][len(df) - 1]:,.2f}",
            "", "", "", "", "", "", "", "", "", ""]
        current[3], current[4] = find_timing(df)

        df = get_df_interval(ticker, trade_date, "15m", interval_type.get("15m"))
        current[5], current[6] = find_timing(df)

        df = get_df_interval(ticker, trade_date, "30m", interval_type.get("30m"))
        current[7], current[8] = find_timing(df)

        df = get_df_interval(ticker, trade_date, "60m", interval_type.get("60m"))
        current[9], current[10] = find_timing(df)

        df = get_df_interval(ticker, trade_date, "1d", interval_type.get("1d"))
        current[11], current[12] = find_timing(df)

        res = np.append(res, [current], axis=0)

    return res[1:]


app = Flask(__name__, template_folder="template")


@app.route("/query", methods=["GET", "POST"])
def handle_query():
    if request.method == "POST":
        trade_date = request.form["trade_date"]
        return render_template("home.html", data=prepare_web_content(trade_date))
    else:
        return render_template("home.html")


@app.route("/")
def home():
    handle_query()


if __name__ == "__main__":
    app.run(host="localhost", port=8088, debug=None)
    # app.run(host="194.233.83.43", port=8088, debug=None)
    # app.run(host="109.123.236.116", port=8088, debug=None)
