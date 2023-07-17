from flask import Flask, render_template, request
from app import views

myApp = Flask(__name__, template_folder="app/templates/", static_folder="app/static/")


@myApp.route("/query", methods=["GET", "POST"])
def handle_query():
    if request.method == "POST":
        trade_date = request.form["trade_date"]
        return render_template("trade_view_price.html", data=views.prepare_web_content(trade_date))
    else:
        return render_template("trade_view_price.html")


@myApp.route("/queryTradingview", methods=["GET", "POST"])
def handle_tradingview():
    if request.method == "POST":
        interval = request.form["interval"]
        return render_template("trade_view_screener.html", data=views.prepare_tradingview(interval))
    else:
        return render_template("trade_view_screener.html")


@myApp.route("/")
def home():
    handle_query()
    handle_tradingview()


if __name__ == "__main__":
    myApp.run(host="localhost", port=8088, debug=None)
    # app.run(host="194.233.83.43", port=8088, debug=None)
    # app.run(host="109.123.236.116", port=8088, debug=None)
