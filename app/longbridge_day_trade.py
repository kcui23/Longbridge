from datetime import datetime
from decimal import Decimal
from longbridge.openapi import TradeContext, Config, OrderStatus, OrderType, OrderSide, Market, TimeInForceType


def init():
    config = Config.from_env()
    return TradeContext(config)


def day_trade(email, ticker, interval):
    ctx = init()
    print(f"Day trade starts\nEmail: %s\nTicker: %s\nInterval: %s" % (email, ticker, interval))
    print(ctx)
