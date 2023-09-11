import time
from datetime import datetime
from decimal import Decimal
from tradingview_ta import TA_Handler
from longbridge.openapi import TradeContext, Config, OrderStatus, OrderType, OrderSide, Market, TimeInForceType
from app import models as md
from app import database as db


def init():
    config = Config.from_env()
    return TradeContext(config)


def update_longbridge_record(ticker, interval, position, ta_recommendation, yf_signal):
    cnx = db.connect_to_db()
    cursor = cnx.cursor()
    now = datetime.utcnow()

    sql = "INSERT INTO longbridge_trading (datetime, ticker, interval, position, ta_recommendation, yf_signal) VALUES (%s, %s, %s, %s, %s, %s);"

    cursor.execute(sql, (now, ticker, interval, position, ta_recommendation, yf_signal))
    cnx.commit()


def day_trade(email, ticker, interval, quantity):
    ctx = init()
    today = datetime.today()

    while True:
        try:
            handler = TA_Handler(
                symbol=ticker,
                exchange=md.ticker_exchanges.get(ticker),
                screener="america",
            )

            now = datetime.now()
            handler.interval = md.intervals.get(interval)
            analysis = handler.get_analysis()

            recommendation = analysis.summary["RECOMMENDATION"]

            df = md.get_df_interval(ticker, today.strftime("%Y-%m-%d"), interval, md.interval_type[interval])

            print(f"%s\tTicker: %5s\tInterval: %3s\tTA: %10s\tMACD: %10s" % (
                now.strftime("%Y-%m-%d %H:%M:%S"), ticker, interval, recommendation, df["BuyIndex"][len(df) - 1]))

            # df                PotentialBuy PotentialSell Hold
            # recommendation    STRONG_BUY BUY NEUTRAL SELL STRONG_SELL

            update_longbridge_record(ticker, interval, 10, recommendation, df["BuyIndex"][len(df) - 1])


        except Exception as e:
            print(f"Error ({e}): {ticker}")

        time.sleep(20)
