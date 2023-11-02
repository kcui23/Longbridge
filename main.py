from app import models as md

if __name__ == "__main__":

    trade_day = '2023-11-01'
    principal = 1480.00

    for ticker, _ in md.ticker_exchanges.items():
        if ticker[-2:] == "HK":
            principal = 1480.00 * 7.8
            market = "HK"
        else:
            principal = 1480.00
            market = "US"
        for interval, value in md.interval_type.items():
            # print ticker and interval
            print("\n\n", "Ticker: {}".format(ticker).center(99, '-'), sep="")
            print("Interval: {}".format(interval).center(99, '-'), sep="")
            df = md.get_df_interval(ticker, trade_day, interval, value)

            df = md.paper_trade(df, principal, market)
            print("\n", "Signals".center(62, '-'), sep="")
            md.print_realtime_ratting(df)
            md.plot_stock_screener(df, ticker)

            print("\n", "Trade".center(99, '-'), sep="")
            print("\n", "Result".center(21, '-'), "\n{:<5} ({})\nFrom {}\nTo   {}\nEarning {:>13}".format(
                ticker,
                md.distinguish_interval(df),
                str(df["Datetime"].iloc[0])[:16],
                str(df["Datetime"].iloc[len(df) - 1])[:16],
                "{:,.2f}".format(md.print_trade_records(df) - principal)
            ), sep="")
