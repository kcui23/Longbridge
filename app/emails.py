import smtplib
import hashlib
from datetime import datetime
from tradingview_ta import TA_Handler
from beingRich.app import models as md
from beingRich.app import database as db


def generate_email_notification_id(ticker, signal, last_updated_datetime, last_price, interval):
    cnx = db.connect_to_db()
    cursor = cnx.cursor()

    notification_id = ""

    cursor.execute('''
        SELECT COUNT(*)
        FROM notification_email
        WHERE ticker = %s AND signal = %s AND last_updated_datetime = %s AND last_price = %s AND interval = %s;
    ''', (ticker, signal, last_updated_datetime, last_price, interval))
    count = cursor.fetchone()[0]

    if count == 0:
        cursor.execute('''
                    SELECT TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || LPAD(CAST(COUNT(*) + 1 AS TEXT), 4, '0')
                    FROM notification_email
                    WHERE last_updated_datetime >= CURRENT_DATE;
                ''')
        notification_id = cursor.fetchone()[0]
        notification_id += f"({hashlib.md5((ticker + interval).encode()).hexdigest()[:4]})"

        cursor.execute('''
                    INSERT INTO notification_email (id, ticker, signal, last_updated_datetime, last_price, interval)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (notification_id, ticker, signal, last_updated_datetime, last_price, interval))
    else:
        print("Duplicated", ticker, signal, last_updated_datetime, last_price, interval)

    cnx.commit()
    cursor.close()
    cnx.close()

    return notification_id


def email_notification(ticker, interval, email):
    def send_email(receiver_email, message):
        sender_email = "asta_test_lightwing@outlook.com"
        password = "04^kI3-CYGbhL-b%SHDL"

        server = smtplib.SMTP("smtp-mail.outlook.com", 587)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message)
        server.quit()

    try:
        handler = TA_Handler(
            symbol=ticker,
            exchange=md.ticker_exchanges.get(ticker),
            screener="america",
        )

        handler.interval = md.intervals.get(interval)
        analysis = handler.get_analysis()

        today_string = datetime.now().strftime("%Y-%m-%d")
        df = md.get_df_interval(ticker, today_string, interval, md.interval_type.get(interval))

        signal_buy, price_buy, datetime_buy = False, 0.00, ""
        signal_sell, price_sell, datetime_sell = False, 0.00, ""
        price_close = analysis.indicators["close"]
        recent_cycle = 26

        for i in range(len(df) - 1, max(len(df) - recent_cycle, -1), -1):
            current, price, datetime_last = df["BuyIndex"][i], df["Close"][i], df["Datetime"][i]
            if current == "PotentialBuy" and not signal_buy:
                signal_buy, price_buy, datetime_buy = True, price, datetime_last
            elif current == "PotentialSell" and not signal_sell:
                signal_sell, price_sell, datetime_sell = True, price, datetime_last
            elif signal_buy and signal_sell:
                break

        if signal_buy:
            print(f"{ticker:5s} Buy  {datetime_buy} {price_buy:,.2f}")
        if signal_sell:
            print(f"{ticker:5s} Sell {datetime_sell} {price_sell:,.2f}")

        recommendation = analysis.summary["RECOMMENDATION"]
        if (recommendation == "STRONG_BUY") and (signal_buy and price_close <= price_buy):
            notification_id = generate_email_notification_id(ticker, "Strong buy", datetime_buy, f"{price_buy:,.2f}", interval)

            if len(notification_id) > 0:
                subject = f"Strong buy {ticker} at ${price_close:,.2f}"
                body = f"Interval: {interval}\nLast updated: {datetime_buy}\nBelow: ${price_buy :,.2f}\n\nReference ID: {notification_id}"
                message = f"Subject: {subject}\n\n{body}"
                send_email(email, message)

    except Exception as e:
        print(f"Error ({e}): {ticker}")