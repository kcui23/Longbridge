import pytz
from app import models as md
from datetime import datetime

if __name__ == "__main__":

    # trade_day = '2023-11-08'
    trade_day = datetime.now(pytz.timezone('America/Chicago'))
    principal = 1480.00

    for ticker, _ in md.ticker_exchanges.items():
        if ticker[-2:] == "HK":
            principal = 1480.00 * 7.8
            market = "HK"
            # 转换trade day到香港时间
            trade_day = str(trade_day.astimezone(pytz.timezone('Asia/Hong_Kong'))).split(" ")[0]
        else:
            principal = 1480.00
            market = "US"
            # 转换trade day到美东时间
            trade_day = str(trade_day.astimezone(pytz.timezone('America/New_York'))).split(" ")[0]
        for interval, value in md.interval_type.items():
            # print ticker and interval
            print("\n\n", "Ticker: {}".format(ticker).center(99, '-'), sep="")
            print("Interval: {}".format(interval).center(99, '-'), sep="")
            df = md.get_df_interval(ticker, trade_day, interval, value, market)

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
