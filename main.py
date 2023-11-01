from app import models as md

if __name__ == "__main__":

    trade_day = '2023-10-31'
    principal = 1480.00

    for ticker, _ in md.ticker_exchanges.items():
        for interval, value in md.interval_type.items():
            df = md.get_df_interval(ticker, trade_day, interval, value)

            df = md.paper_trade(df, principal)
            md.print_realtime_ratting(df)
            md.plot_stock_screener(df, ticker)

            print("\n{:<5} ({})\nFrom {}\nTo   {}\nEarning {:>13}".format(
                ticker,
                md.distinguish_interval(df),
                str(df["Datetime"].iloc[0])[:16],
                str(df["Datetime"].iloc[len(df) - 1])[:16],
                "{:,.2f}".format(md.print_trade_records(df) - principal)
            ))
