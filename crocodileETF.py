import yfinance as yf
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.patches import Rectangle

tickers = {
    "0998.HK": {"name": "中信銀行", "holding": 2000, "currency": "HKD", "original": 3.53},
    "601333.SS": {"name": "廣深鐵路", "holding": 50, "currency": "CNY", "original": 3.23},
    "003013.SZ": {"name": "地鐵設計", "holding": 100, "currency": "CNY", "original": 18.62},
    "0005.HK": {"name": "滙豐控股", "holding": 40, "currency": "HKD", "original": 61.70},
    "0014.HK": {"name": "希慎興業", "holding": 250, "currency": "HKD", "original": 16.92},
    "0066.HK": {"name": "港鐵公司", "holding": 10, "currency": "HKD", "original": 33.80},
    "2388.HK": {"name": "中銀香港", "holding": 50, "currency": "HKD", "original": 21.90}
}

total_stock = 0.00
principal = 21000.00
cash_in_hand = 3093.20
values, labels = [], []
now = datetime.now()

table_data = [["Ticker", "Holding", "Price", "Currency", "HKD", "Total", "P/L"]]

for ticker, info in tickers.items():
    name = info["name"]
    holding = info["holding"]
    currency = info["currency"]
    stock = yf.Ticker(ticker)
    df = yf.download(ticker, interval="1m", progress=False)

    priceClose = df['Close'][-1]
    priceCloseHKD = df['Close'][-1] if currency == 'HKD' else df['Close'][-1] * 1.08
    total_sub = priceCloseHKD * holding
    total_stock += total_sub

    change = (priceClose - info["original"]) * 100 / info["original"]

    values.append(total_sub)
    labels.append(f"{ticker}\n{total_sub: ,.2f}")

    table_data.append([
        ticker + f"\n{name}",
        f"{holding: ,}",
        f"{priceClose: .2f}",
        currency,
        f"{priceCloseHKD: .2f}",
        f"{total_sub: ,.2f}",
        f"{change:.2f}%"])

values.append(cash_in_hand)
labels.append(f"Cash\n{cash_in_hand: ,.2f}")
table_data.append(["Cash", "", "", "HKD", "", format(f"{cash_in_hand: ,.2f}"), "0.00%"])
table_data.append(["ETF Total", "", "", "HKD", "", format(f"{total_stock + cash_in_hand: ,.2f}"),
                   f"{(total_stock + cash_in_hand - principal) * 100 / principal  : .2f}%"])

base_color = colors.hex2color('#1D6F42')
color_scheme = [colors.rgb2hex((base_color[0] * (1 - shade), base_color[1] * (1 - shade), base_color[2] * (1 - shade)))
                for shade in [0.00, 0.10, 0.20, 0.30, 0.40]]

fig, (ax1, ax2) = plt.subplots(nrows=2, figsize=(6, 8), dpi=300)
ax1.pie(values, labels=labels, colors=color_scheme, startangle=90, wedgeprops={'edgecolor': 'white'},
        textprops={'color': '#1D6F42', 'fontname': 'Arial'})
ax1.axis('equal')

circle = plt.Circle((0, 0), 0.88, color='white')
ax1.add_artist(circle)

table = ax2.table(cellText=table_data, loc='center', edges='open')
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 1.5)
ax2.axis('off')

for row in range(len(table_data)):
    for col in range(len(table_data[0])):

        cell = table[row, col]

        if col == 0 and row > 0:
            cell.set_text_props(ha='left', va='center', fontsize=8)
        if row == 0:
            cell.set_text_props(ha='center', weight='bold')

        if row > 0 and "-" in table_data[row][6]:
            cell.set_text_props(color='#ff173e', fontname='PingFang HK')
        elif "-" not in table_data[row][6]:
            cell.set_text_props(color='#1d6f42', fontname='PingFang HK')

        if row == len(table_data) - 1 and col >= 5:
            cell.set_text_props(fontsize=12, weight='bold')

now = datetime.now()

ax1.text(0, 1, 'Matsuda Benjamin ETF Daily Report\n松田本傑明追蹤指數基金持倉報告', fontname='Source Han Serif TC',
         fontsize=18,
         color='#1d6f42', transform=ax1.transAxes)
rect = Rectangle((0, 0.85), 0.28, 0.13, facecolor='#1d6f42', transform=ax1.transAxes)
ax1.text(0, 0.87, ' Updated on\n' + now.strftime(' %d/%m/%Y %H:%M'), fontsize=10, color='#ffffff',
         transform=ax1.transAxes)
ax1.add_patch(rect)

fig.subplots_adjust(hspace=0)

plt.show()
