import psycopg2
from beingRich.app import models as md

user = "lightwing"
password = "canton0520"
host = "localhost"
database = "beingRich"
port = 5432


def connect_to_db():
    cnx = psycopg2.connect(
        user=user,
        password=password,
        host=host,
        database=database,
        port=port)
    return cnx


def update_yahoofinance_data(ticker, df):
    cnx = connect_to_db()
    cursor = cnx.cursor()

    sql_insert = ""

    for i in range(len(df)):
        sql_insert += f"""INSERT INTO yahoo_finance_data ("ticker", "Datetime", "Interval", "Open", "High", "Low", "Close", "Adj Close", "Volume", "BuyIndex") SELECT '{ticker}', '{df["Datetime"][i]}', '{md.distinguish_interval(df)}', {df["Open"][i]}, {df["High"][i]}, {df["Low"][i]}, {df["Close"][i]}, {df["Adj Close"][i]}, {df["Volume"][i]}, '{df["BuyIndex"][i]}' WHERE NOT EXISTS (SELECT 1 FROM yahoo_finance_data WHERE "ticker" = '{ticker}' AND "Datetime" = '{df["Datetime"][i]}' AND "Interval" = '{md.distinguish_interval(df)}');"""

    cursor.execute(sql_insert)
    cnx.commit()
    cursor.close()
    cnx.close()


def update_tradingview_data(analysis):
    cnx = connect_to_db()
    cursor = cnx.cursor()

    columns = ", ".join([f'"{column}"' for column in analysis.indicators.keys()])
    placeholders = ", ".join(["%s"] * len(analysis.indicators))
    sql_insert = f"INSERT INTO tradingview_analysis (\"ticker\", \"datetime\", \"interval\", {columns}) VALUES (\'{analysis.symbol}\', \'{analysis.time}\', \'{analysis.interval}\', {placeholders});"

    cursor.execute(sql_insert, list(analysis.indicators.values()))
    cnx.commit()
    cursor.close()
    cnx.close()


def remove_tradingview_duplicates():
    cnx = connect_to_db()
    cursor = cnx.cursor()

    cursor.execute(
        f"""DELETE FROM tradingview_analysis WHERE datetime NOT IN (SELECT MIN(datetime) FROM tradingview_analysis GROUP BY ticker, interval, "Recommend.Other", "Recommend.All", "Recommend.MA", volume, change, open, low, high) OR (datetime::TIME > '04:00'::TIME AND datetime::TIME < '21:30'::TIME);""")

    cnx.commit()
    cursor.close()
    cnx.close()
