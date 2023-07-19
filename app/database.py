import psycopg2
from datetime import datetime

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
