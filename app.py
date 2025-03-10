import yfinance as yf
import streamlit as st
from streamlit_searchbox import st_searchbox
import time
import pandas as pd
from streamlit_option_menu import option_menu
import numpy as np
from datetime import date, datetime, timedelta
from plotly import graph_objs as go
from prophet import Prophet


st.set_page_config(page_title="My Portfolio", page_icon=":moneybag:", layout="wide")
# st.title("")
st.subheader("My Portfolio", divider="rainbow")

if "investment" not in st.session_state:
    st.session_state["investment"] = float(0)
if "current_value" not in st.session_state:
    st.session_state["current_value"] = float(0)
if "profit" not in st.session_state:
    st.session_state["profit"] = float(0)


def find_stock(search_term: str):
    if search_term and len(search_term) < 3:
        return []
    else:
        return [
            f"{quote['shortname']}:{quote['exchange']}:::{quote['symbol']}"
            for quote in yf.Search(search_term, include_cb=False).quotes
        ]


def find_stock_price(symbol: str):
    return yf.Ticker(symbol)


def get_prices(df):
    symbols = df["symbol"]
    prices = yf.Tickers(" ".join(symbols))
    # st.write(prices.tickers)
    return prices.tickers


def load_csv():
    df = pd.read_csv("./data/stocks.csv")
    df["buy_date"] = pd.to_datetime(df["buy_date"], yearfirst=True).dt.date
    return df


def calculate_prices(df):
    tickers = get_prices(df)
    for index, symbol in df["symbol"].items():
        price = tickers[symbol].info.get("currentPrice")
        buy_price = df.at[index, "buy_price"]
        quantity = df.at[index, "quantity"]
        investment = buy_price * quantity
        current_value = price * quantity
        profit = current_value - investment

        df.at[index, "price"] = price
        df.at[index, "investment"] = investment
        df.at[index, "current_value"] = current_value
        df.at[index, "profit"] = profit

        st.session_state["investment"] = df["investment"].sum()
        st.session_state["current_value"] = df["current_value"].sum()
        st.session_state["profit"] = df["profit"].sum()

    return df


if "df" not in st.session_state:
    df = load_csv()
    st.session_state["df"] = calculate_prices(df)
# st.write(st.session_state["df"])


if "selected_stock_name" not in st.session_state:
    st.session_state["selected_stock_name"] = None
if "selected_stock" not in st.session_state:
    st.session_state["selected_stock"] = None


def add_stock(
    symbol: str, stock_name: str, buy_date: date, buy_price: float, quantity: int
):
    df = st.session_state["df"].filter(
        ["symbol", "stock_name", "buy_date", "buy_price", "quantity"], axis=1
    )
    new_row = [symbol, stock_name, buy_date, buy_price, quantity]
    new_df = pd.DataFrame(
        columns=df.columns,
        data=[new_row],
    )
    df = pd.concat([df, new_df], axis=0, ignore_index=True)
    save(df)
    st.session_state["selected_stock_name"] = None
    st.session_state["selected_stock"] = None


def set_changed(changed: bool):
    st.session_state["is_changed"] = changed


def save(changed_df):
    df_to_save = changed_df.filter(
        ["symbol", "stock_name", "buy_date", "buy_price", "quantity"], axis=1
    )
    df_to_save.to_csv("./data/stocks.csv", index=False)
    st.session_state["df"] = calculate_prices(df_to_save)
    set_changed(False)


if not st.session_state["selected_stock_name"]:

    @st.dialog("Search and add stock")
    def open_add_stock():
        st.session_state["selected_stock_name"] = st_searchbox(
            find_stock, "\n\nSearch for a stock", rerun_scope="fragment"
        )
        selected_stock_name = st.session_state["selected_stock_name"]
        if selected_stock_name:
            st.write(selected_stock_name)
            symbol = selected_stock_name.split(":::")[1]
            quote_name = selected_stock_name.split(":::")[0]
            st.session_state["selected_stock"] = find_stock_price(symbol)
            selected_stock = st.session_state["selected_stock"]
            if selected_stock:
                st.write(f"Name: {selected_stock.info.get('shortName', 'N/A')}")
                st.write(f"Price: {selected_stock.info.get('currentPrice')}")
                # st.write(
                # "{:.2f}".format(selected_stock.history(period="1d", interval="1m")["Close"][0])
                # )

                stocks_form = st.form(key="Add stocks")
                stock_name = stocks_form.text_input(
                    "Stock Name", value=quote_name, disabled=True
                )
                buy_date = stocks_form.date_input(
                    "Stock buy date",
                    value="today",
                    help="When did you buy this?",
                    min_value="2000-01-01",
                    max_value=date.today(),
                    format="YYYY-MM-DD",
                )
                buy_price = stocks_form.number_input(
                    "Stock buy price",
                    step=0.01,
                    min_value=0.01,
                    format="%.2f",
                )
                quantity = stocks_form.number_input("Quantity", step=1, min_value=1)
                if stocks_form.form_submit_button("Add"):
                    add_stock(symbol, stock_name, buy_date, buy_price, quantity)
                    st.rerun()


col1, col2, col3, col4 = st.columns(4, border=True, vertical_alignment="bottom")
if col1.button("Add stock"):
    open_add_stock()

col2.text(f"Total Investment\n{'Rs {:,.2f}'.format(st.session_state['investment'])}")
col3.text(f"Current Value\n{'Rs {:,.2f}'.format(st.session_state['current_value'])}")
col4.html(
    f"""
    <div style='background-color: #f0794c'>
        <p><span style='font-weight: bold;'>Total Profit/Loss</span></p>
        <p><span style='font-weight: bold;'>{'Rs {:,.2f}'.format(st.session_state['profit'])}</span></p>
    </div>
    """
)

st.subheader("", divider="rainbow")
if "is_changed" not in st.session_state:
    set_changed(False)

if len(st.session_state["df"]) > 0:
    edited_df = st.data_editor(
        st.session_state["df"],
        column_config={
            "symbol": "Symbol",
            "stock_name": "Stock Name",
            "buy_date": st.column_config.DateColumn(
                "Buy Date",
                help="When did you buy this?",
                min_value=date(2000, 1, 1),
                max_value=date.today(),
                format="YYYY-MM-DD",
                step=1,
            ),
            "buy_price": st.column_config.NumberColumn(
                "Buy Price",
                help="Stock buy price",
                step=0.01,
                min_value=0.01,
                format="%.2f",
                required=True,
            ),
            "price": "Price",
            "investment": "Investment",
            "current_value": "Current Value",
            "profit": "Profit/Loss",
            "Unnamed": "S.No.",
            "quantity": st.column_config.NumberColumn(
                "Quantity", help="Quantity?", step=1, min_value=1, required=True
            ),
        },
        disabled=[
            "symbol",
            "stock_name",
            "price",
            "investment",
            "current_value",
            "profit",
            "Unnamed",
        ],
        hide_index=True,
        on_change=set_changed,
        args=(True,),
    )

    if st.session_state["is_changed"]:
        save(edited_df)
