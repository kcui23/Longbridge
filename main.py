import numpy as np
from datetime import datetime
from flask import Flask, render_template, request
from tradingview_ta import TA_Handler, Interval
import YahooFinanceLibrary


def test_single_stock(ticker):
    for key, interval in interval_type.items():
        df = YahooFinanceLibrary.get_df_interval(ticker, "2023-07-14", key, interval)
        df = YahooFinanceLibrary.paper_trade(df, principal)
        YahooFinanceLibrary.print_trade_records(df)
        print("\n%-5s %18s (%s)" % (
            ticker,
            f"{YahooFinanceLibrary.print_trade_records(df):,.2f}",
            YahooFinanceLibrary.distinguish_interval(df)))
        YahooFinanceLibrary.plot_stock_screener(df, ticker)


def test_all_stocks(trade_day, principal):
    for ticker, _ in ticker_exchanges.items():
        for key, value in interval_type.items():
            df = YahooFinanceLibrary.get_df_interval(ticker, trade_day, key, value)
            df = YahooFinanceLibrary.paper_trade(df, principal)
            YahooFinanceLibrary.print_realtime_ratting(df)
            YahooFinanceLibrary.plot_stock_screener(df, ticker)

            print("\n%-5s (%s)\nFrom %s\nTo   %s\nEarning %13s" % (
                ticker,
                YahooFinanceLibrary.distinguish_interval(df),
                str(df["Datetime"][0])[:16],
                str(df["Datetime"][len(df) - 1])[:16],
                f"{YahooFinanceLibrary.print_trade_records(df) - principal:,.2f}",
            ))


ticker_exchanges = {
    ticker: "NASDAQ" if ticker in [
        "MSFT", "NVDA", "GOOGL", "AMZN", "META",
        "AMD", "ADBE", "QCOM", "NFLX", "ASML",
        "AVGO", "TSLA", "PEP", "QQQ"]
    else "NYSE" for ticker in [
        "MSFT", "NVDA", "GOOGL", "TSM", "AMZN",
        "META", "ORCL", "AMD", "ADBE", "QCOM",
        "NFLX", "ASML", "AVGO", "VZ", "GS",
        "JPM", "MS", "WFC", "BAC", "C",
        "V", "MA", "AXP", "XOM", "CVX",
        "TSLA", "MCD", "KO", "PEP", "PG",
        "ABBV", "MRK", "LLY", "UNH", "PFE",
        "JNJ", "QQQ"]}

interval_type = {
    "1m": 3, "15m": 30, "30m": 59, "60m": 180, "1d": 365
}

intervals = {
    "1m": Interval.INTERVAL_1_MINUTE,
    "5m": Interval.INTERVAL_5_MINUTES,
    "15m": Interval.INTERVAL_15_MINUTES,
    "30m": Interval.INTERVAL_30_MINUTES,
    "1h": Interval.INTERVAL_1_HOUR,
    "1d": Interval.INTERVAL_1_DAY,
}

today = datetime.today()
date_string = today.strftime("%Y-%m-%d")
date_string_today = today.strftime("%Y-%m-%d")
principal = 10000

# 1. Single test
test_single_stock("NVDA")

# 2. All test
test_all_stocks(date_string_today, principal)


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

    for ticker, _ in ticker_exchanges.items():
        now = datetime.now()
        print("Trade date: %s\tTicker: %-5s\tCalculation date: %s" % (
            trade_date, ticker, now.strftime("%d/%m/%y %H:%M:%S")))

        df = YahooFinanceLibrary.get_df_interval(ticker, trade_date, "1m", interval_type.get("1m"))
        current = [
            ticker, f"{df['CRSI'][len(df) - 1]:,.2f}", f"{df['Close'][len(df) - 1]:,.2f}",
            "", "", "", "", "", "", "", "", "", ""]
        current[3], current[4] = find_timing(df)

        df = YahooFinanceLibrary.get_df_interval(ticker, trade_date, "15m", interval_type.get("15m"))
        current[5], current[6] = find_timing(df)

        df = YahooFinanceLibrary.get_df_interval(ticker, trade_date, "30m", interval_type.get("30m"))
        current[7], current[8] = find_timing(df)

        df = YahooFinanceLibrary.get_df_interval(ticker, trade_date, "60m", interval_type.get("60m"))
        current[9], current[10] = find_timing(df)

        df = YahooFinanceLibrary.get_df_interval(ticker, trade_date, "1d", interval_type.get("1d"))
        current[11], current[12] = find_timing(df)

        res = np.append(res, [current], axis=0)

    return res[1:]


def prepare_tradingview(interval):
    res = np.array([["APPL", "", "", "", "", ""]])

    for ticker, exchange in ticker_exchanges.items():
        handler = TA_Handler(
            symbol=ticker,
            exchange=exchange,
            screener="america",
        )

        handler.interval = intervals.get(interval)
        current = [ticker, "", "", "", "", ""]

        try:
            now = datetime.now()
            print("Ticker: %-5s\t%4s\ton: %s" % (
                ticker, interval, now.strftime("%d/%m/%y %H:%M:%S")))

            analysis = handler.get_analysis()
            latest_price = analysis.indicators["close"]
            latest_change = analysis.indicators["change"]
            ratting = analysis.summary
            current[1] = f"{latest_price:,.2f}" + f" {latest_change:,.2f}"
            current[2] = ratting.get('RECOMMENDATION')
            current[3] = ratting.get('BUY')
            current[4] = ratting.get('NEUTRAL')
            current[5] = ratting.get('SELL')
        except Exception as e:
            print(f"Error retrieving data for {ticker} at {interval}: {e}")

        res = np.append(res, [current], axis=0)

    return res[1:]


app = Flask(__name__, template_folder="template", static_folder="template")


@app.route("/query", methods=["GET", "POST"])
def handle_query():
    if request.method == "POST":
        trade_date = request.form["trade_date"]
        return render_template("trade_view_price.html", data=prepare_web_content(trade_date))
    else:
        return render_template("trade_view_price.html")


@app.route("/queryTradingview", methods=["GET", "POST"])
def handle_tradingview():
    if request.method == "POST":
        interval = request.form["interval"]
        return render_template("trade_view_screener.html", data=prepare_tradingview(interval))
    else:
        return render_template("trade_view_screener.html")


@app.route("/")
def home():
    handle_query()
    handle_tradingview()


if __name__ == "__main__":
    app.run(host="localhost", port=8088, debug=None)
    # app.run(host="194.233.83.43", port=8088, debug=None)
    # app.run(host="109.123.236.116", port=8088, debug=None)
