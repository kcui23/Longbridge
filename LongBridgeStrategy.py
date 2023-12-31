from datetime import datetime
from decimal import Decimal
from longbridge.openapi import TradeContext, Config, OrderStatus, OrderType, OrderSide, Market, TimeInForceType


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


ctx = init()

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
