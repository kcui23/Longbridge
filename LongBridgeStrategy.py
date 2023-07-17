from datetime import datetime
from decimal import Decimal
import time
from longbridge.openapi import TradeContext, Config, OrderStatus, OrderType, OrderSide, Market, TimeInForceType, QuoteContext
from tradingview_ta import TA_Handler, Interval


def init():
    config = Config.from_env()
    return TradeContext(config)


def get_max_purchase_quantity(ticker):
    return ctx.estimate_max_purchase_quantity(
        symbol=ticker,
        order_type=OrderType.LO,
        side=OrderSide.Buy)


def get_history_order(ticker):
    resp = ctx.history_executions(
        symbol=ticker,
        start_at=datetime(2023, 1, 1),
        end_at=datetime.now(),
    )

    print("ID\t\t\t\t\tTrade done at\t\tTicker\tPrice\tQuantity")
    for i in range(len(resp)):
        current = resp[i]
        print("%s\t%s\t%s\t%6s\t%3s" % (current.order_id, current.trade_done_at, current.symbol, f"{current.price:,.2f}", current.quantity))

    return resp


def submit_order(ticker, quantity, price, direction):
    if direction == "Buy":
        return ctx.submit_order(
            ticker,
            OrderType.LO,
            OrderSide.Buy,
            quantity,
            TimeInForceType.Day,
            submitted_price=Decimal(price),
            remark=""
        )
    elif direction == "Sell":
        return ctx.submit_order(
            ticker,
            OrderType.LO,
            OrderSide.Sell,
            quantity,
            TimeInForceType.Day,
            submitted_price=Decimal(price),
            remark=""
        )


def get_today_order(ticker):
    resp = ctx.today_orders(
        symbol=ticker,
        status=[OrderStatus.Filled, OrderStatus.New],
        side=OrderSide.Buy,
        market=Market.US,
    )

    return resp


def get_order_details(order_id):
    return ctx.order_detail(
        order_id=order_id
    )


def amend_order(order_id, quantity, price):
    ctx.replace_order(
        order_id=order_id,
        quantity=quantity,
        price=Decimal(price)
    )


def withdraw_order(order_id):
    ctx.cancel_order(order_id)


def get_account_balance():
    return ctx.account_balance()


def get_stock_positions():
    return ctx.stock_positions()


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

intervals = {
    "1m": Interval.INTERVAL_1_MINUTE,
    "5m": Interval.INTERVAL_5_MINUTES,
    "15m": Interval.INTERVAL_15_MINUTES,
    "30m": Interval.INTERVAL_30_MINUTES,
    "1h": Interval.INTERVAL_1_HOUR,
    "1d": Interval.INTERVAL_1_DAY,
}


def auto_trade(ticker, interval):
    while True:
        try:
            handler = TA_Handler(
                symbol=ticker,
                exchange=ticker_exchanges.get(ticker),
                screener="america",
            )

            handler.interval = intervals.get(interval)
            analysis = handler.get_analysis()

            if analysis.summary["RECOMMENDATION"] == "STRONG_BUY":
                print(datetime.now(), ticker, analysis.summary["RECOMMENDATION"], analysis.indicators["close"])
            elif analysis.summary["RECOMMENDATION"] == "STRONG_SELL":
                print(datetime.now(), ticker, analysis.summary["RECOMMENDATION"], analysis.indicators["close"])
        except Exception as e:
            print(f"Error retrieving data for: {e}")

        time.sleep(30)


ctx = init()

auto_trade("NVDA", "1m")

# print(get_max_purchase_quantity("VZ.US"))
# withdraw_order("865278546859069440")
# print(get_today_order("NVDA.US"))
# print(submit_order("TSM.US", 100, "0.99", "Buy"))
# 865278546859069440
# get_history_order("")
# print(get_order_details("864157105848643584"))
# print(get_today_order("TSM.US"))
# print(get_account_balance())
# print(get_stock_positions())
