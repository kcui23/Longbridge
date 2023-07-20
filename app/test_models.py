import time
from datetime import datetime
from beingRich.app import models as md
from beingRich.app import database as db


def test_single_stock(ticker: str, trade_day: str, principal: float) -> None:
    for key, interval in md.interval_type.items():
        df = md.get_df_interval(ticker, trade_day, key, interval)

        db.update_yahoofinance_data(ticker, df)

        df = md.paper_trade(df, principal)
        md.print_trade_records(df)
        print("\n%-5s %18s (%s)" % (
            ticker,
            f"{md.print_trade_records(df):,.2f}",
            md.distinguish_interval(df)))
        md.plot_stock_screener(df, ticker)


def test_all_stocks(trade_day: str, principal: float) -> None:
    for ticker, _ in md.ticker_exchanges.items():
        for interval, value in md.interval_type.items():
            df = md.get_df_interval(ticker, trade_day, interval, value)

            db.update_yahoofinance_data(ticker, df)

            df = md.paper_trade(df, principal)
            md.print_realtime_ratting(df)
            md.plot_stock_screener(df, ticker)

            print("\n%-5s (%s)\nFrom %s\nTo   %s\nEarning %13s" % (
                ticker,
                md.distinguish_interval(df),
                str(df["Datetime"][0])[:16],
                str(df["Datetime"][len(df) - 1])[:16],
                f"{md.print_trade_records(df) - principal:,.2f}",
            ))


today = datetime.today()
date_string_today = today.strftime("%Y-%m-%d")

if __name__ == "__main__":
    # test_single_stock("NVDA", date_string_today, 10000.00)
    start_time = time.time()
    test_all_stocks(date_string_today, 10000.00)
    print(f"Elapsed time: {time.time() - start_time:.2f} seconds")
