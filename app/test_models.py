from datetime import datetime
from beingRich.app import models as md


def test_single_stock(ticker):
    for key, interval in md.interval_type.items():
        df = md.get_df_interval(ticker, "2023-07-19", key, interval)
        df = md.paper_trade(df, principal)
        md.print_trade_records(df)
        print("\n%-5s %18s (%s)" % (
            ticker,
            f"{md.print_trade_records(df):,.2f}",
            md.distinguish_interval(df)))
        md.plot_stock_screener(df, ticker)


def test_all_stocks(trade_day, principal):
    for ticker, _ in md.ticker_exchanges.items():
        for interval, value in md.interval_type.items():
            df = md.get_df_interval(ticker, trade_day, interval, value)
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
date_string = today.strftime("%Y-%m-%d")
date_string_today = today.strftime("%Y-%m-%d")
principal = 10000.00

if __name__ == "__main__":
    test_single_stock("NVDA")
    # test_all_stocks("2023-07-19", principal)
