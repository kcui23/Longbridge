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
start_date = "2022/01/01"
end_date = "2023/06/20"
ticker = "NVDA"

# Write the URL as a variable using string formatting
url = f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}?period1={date_to_timestamp(start_date)}&period2={date_to_timestamp(end_date)}&interval=1d&events=history&includeAdjustedClose=true"

df = pd.read_csv(url)

# Convert date column to datetime format
df["Date"] = pd.to_datetime(df["Date"])

# Calculate RSI using ta
rsi = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()

# Create a figure and three subplots
fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(12, 8), dpi=300)

# Plot the closing price on the first subplot
ax1.plot(df["Date"], df["Close"], color="#042e6f", label=ticker)

# Add title and labels
plt.title("%s Stock Price from %s to %s" % (ticker, start_date, end_date))
ax1.set_ylabel("Price (USD)")
ax1.legend()

# Plot the RSI on the second subplot
ax2.plot(df["Date"], rsi, color="green", label="RSI")

# Add labels and horizontal lines
ax2.set_xlabel("Date")
ax2.set_ylabel("RSI")
ax2.axhline(80, color="#FF2F92", linestyle="--")
ax2.axhline(20, color="#FF2F92", linestyle="--")
ax2.legend()

# Show the plot
plt.show(format="png", transparent=True)