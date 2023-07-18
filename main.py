import time
from flask import Flask, render_template, request
from app import views
from app import models as md

app = Flask(__name__, template_folder="app/templates/", static_folder="app/static/")


@app.route("/queryPrices", methods=["GET", "POST"])
def handle_query():
    if request.method == "POST":
        trade_date = request.form["trade_date"]
        return render_template("trade_view_price.html", data=views.prepare_web_content(trade_date))
    else:
        return render_template("trade_view_price.html")


@app.route("/queryTradingview", methods=["GET", "POST"])
def handle_tradingview():
    if request.method == "POST":
        interval = request.form["interval"]
        return render_template("trade_view_screener.html", data=views.prepare_tradingview(interval))
    else:
        return render_template("trade_view_screener.html")


@app.route("/startEmailNotification", methods=["GET", "POST"])
def start_email_notification():
    if request.method == "POST":
        email = request.form["email"]
        interval = request.form["interval"]

        while True:
            for ticker, _ in md.ticker_exchanges.items():
                views.email_notification(ticker, interval, email)

            time.sleep(30)
    else:
        return render_template("start_email_notification.html")


@app.route("/thank-you")
def load_successfully_subscribed():
    return render_template("successfully_subscribed.html")


@app.route("/")
def home():
    handle_query()
    handle_tradingview()
    start_email_notification()
    load_successfully_subscribed()


if __name__ == "__main__":
    app.run(host="localhost", port=8088, debug=None)
    # app.run(host="194.233.83.43", port=8088, debug=None)
    # app.run(host="109.123.236.116", port=8088, debug=None)
