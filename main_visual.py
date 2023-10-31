from app import models as md

if __name__ == "__main__":

    trade_day = '2023-10-30'
    principal = 10000.00

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
