import pandas as pd
import matplotlib.pyplot as plt
import datetime
import time
import ta




# Define a function to convert a date string to a Unix timestamp
def date_to_timestamp(date):
    # Parse the date string as a datetime object
    date = datetime.datetime.strptime(date, "%Y/%m/%d")
    # Convert the datetime object to a Unix timestamp
    timestamp = int(time.mktime(date.timetuple()))
    # Return the timestamp
    return timestamp


# Define the starting and ending dates as parameters
ticker = "MSFT"
start_date = "2022/01/01"
end_date = "2023/06/28"

# Write the URL as a variable using string formatting
url = f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}?period1={date_to_timestamp(start_date)}&period2={date_to_timestamp(end_date)}&interval=1d&events=history&includeAdjustedClose=true"
df = pd.read_csv(url)

# Convert date column to datetime format
df["Date"] = pd.to_datetime(df["Date"])

# Calculate MACD, KDJ, RSI using ta library
df["MACD"] = ta.trend.MACD(df["Close"], window_slow=26, window_fast=12).macd()
df["KDJ"] = ta.momentum.StochasticOscillator(df["High"], df["Low"], df["Close"]).stoch()
df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()

# Plot stock price, MACD, KDJ, RSI using matplotlib
plt.rcParams["font.family"] = "Arial"
fig, ax = plt.subplots(4, 1, figsize=(12, 12), gridspec_kw={"height_ratios": [4, 1, 1, 1]}, dpi=300)

ax[0].plot(df["Date"], df["Close"], color="#006d21", linewidth=2)
ax[0].set_ylabel("%s Stock Price" % ticker)
ax[0].spines["top"].set_visible(False)
ax[0].spines["right"].set_visible(False)

ax[1].plot(df["MACD"], color="#042e6f", label="DIF")
ax[1].plot(df["MACD"].ewm(span=9).mean(), color="#ffa500", label="DEM")
ax[1].bar(df.index, df["MACD"] - df["MACD"].ewm(span=9).mean(), label="",
          color=["#006d21" if x > 0 else "#ff2f92" for x in df["MACD"] - df["MACD"].ewm(span=9).mean()])
ax[1].set_ylabel("MACD")
ax[1].spines["top"].set_visible(False)
ax[1].spines["right"].set_visible(False)
ax[1].spines["bottom"].set_visible(False)
ax[1].set_xticklabels([])
ax[1].set_xticks([])

ax[2].plot(df["Date"], df["KDJ"], color="#042e6f", label="KDJ")
ax[2].set_ylabel("KDJ")
ax[2].spines["top"].set_visible(False)
ax[2].spines["right"].set_visible(False)
ax[2].spines["bottom"].set_visible(False)
ax[2].set_xticklabels([])
ax[2].set_xticks([])

ax[3].plot(df["Date"], df["RSI"], color="#042e6f", label="RSI")
ax[3].set_ylabel("RSI")
ax[3].axhline(80, color="#ff2f92", linestyle="--", linewidth=1)
ax[3].axhline(20, color="#ff2f92", linestyle="--", linewidth=1)
ax[3].spines["top"].set_visible(False)
ax[3].spines["right"].set_visible(False)
ax[3].spines["bottom"].set_visible(False)
ax[3].set_xticklabels([])
ax[3].set_xticks([])

# Show the plot
plt.show(format="png", transparent=True)
