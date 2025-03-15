import yfinance as yf
import streamlit as st
from streamlit_searchbox import st_searchbox
import time
import pandas as pd
from streamlit_option_menu import option_menu
import numpy as np
from datetime import date, datetime, timedelta
from plotly import graph_objs as go


st.set_page_config(page_title="My Portfolio", page_icon=":moneybag:", layout="wide")
# st.title("")
st.subheader("My Portfolio", divider="rainbow")

if "investment" not in st.session_state:
    st.session_state["investment"] = float(0)
if "current_value" not in st.session_state:
    st.session_state["current_value"] = float(0)
if "profit" not in st.session_state:
    st.session_state["profit"] = float(0)
if "profit_today" not in st.session_state:
    st.session_state["profit_today"] = float(0)
if "profit_percentage" not in st.session_state:
    st.session_state["profit_percentage"] = float(0)
if "previous_investment" not in st.session_state:
    st.session_state["previous_investment"] = float(0)
if "profit_percentage_today" not in st.session_state:
    st.session_state["profit_percentage_today"] = float(0)


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


def color_profit_loss(val):
    color = "green" if val >= 0 else "red"
    return f"color: {color}"


def calculate_prices(df):
    tickers = get_prices(df)
    for index, symbol in df["symbol"].items():
        info = tickers[symbol].info
        price = info.get("currentPrice")
        previous_close = info.get("previousClose")
        buy_price = df.at[index, "buy_price"]
        quantity = df.at[index, "quantity"]
        investment = buy_price * quantity
        current_value = price * quantity
        st.session_state["previous_investment"] = st.session_state[
            "previous_investment"
        ] + (previous_close * quantity)
        profit = current_value - investment
        profit_percentage = profit * 100 / investment
        profit_today = (price - previous_close) * quantity
        profit_percentage_today = (price - previous_close) * 100 / previous_close

        df.at[index, "price"] = price
        df.at[index, "investment"] = investment
        df.at[index, "current_value"] = current_value
        df.at[index, "profit"] = profit
        df.at[index, "profit_percentage"] = profit_percentage
        df.at[index, "profit_today"] = profit_today
        df.at[index, "profit_percentage_today"] = profit_percentage_today

    st.session_state["investment"] = df["investment"].sum()
    st.session_state["current_value"] = df["current_value"].sum()
    st.session_state["profit"] = df["profit"].sum()
    st.session_state["profit_percentage"] = (
        st.session_state["profit"] * 100 / st.session_state["investment"]
    )
    st.session_state["profit_today"] = df["profit_today"].sum()
    st.session_state["profit_percentage_today"] = (
        st.session_state["profit_today"] * 100 / st.session_state["previous_investment"]
    )

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
    # st.session_state["selected_stock"] = None


def save_stock(buy_date: date, buy_price: float, quantity: int, row_num: int):
    df = st.session_state["df"].filter(
        ["symbol", "stock_name", "buy_date", "buy_price", "quantity"], axis=1
    )
    # st.write(df.iloc[row_num])
    df.loc[row_num, "buy_date"] = buy_date
    df.loc[row_num, "buy_price"] = buy_price
    df.loc[row_num, "quantity"] = quantity
    # st.write(df.iloc[row_num])
    # df.iloc[row_num][4]
    save(df)


def delete_stock(row_num: int):
    df = st.session_state["df"].filter(
        ["symbol", "stock_name", "buy_date", "buy_price", "quantity"], axis=1
    )
    df.drop([row_num], inplace=True)
    # st.write(df.iloc[row_num])
    df.iloc[row_num]
    df.reset_index()
    # st.write(df.iloc[row_num])
    save(df)


def save(changed_df):
    df_to_save = changed_df.filter(
        ["symbol", "stock_name", "buy_date", "buy_price", "quantity"], axis=1
    )
    df_to_save.to_csv("./data/stocks.csv", index=False)
    st.session_state["df"] = calculate_prices(df_to_save)


if not st.session_state["selected_stock_name"]:

    @st.dialog("Search and add stock")
    def open_add_stock():
        st.session_state["selected_stock_name"] = st_searchbox(
            find_stock, "\n\nSearch for a stock", rerun_scope="fragment"
        )
        selected_stock_name = st.session_state["selected_stock_name"]
        if selected_stock_name:
            # st.write(selected_stock_name)
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


col1, col2, col3, col4 = st.columns(
    4, border=False, vertical_alignment="bottom", gap="large"
)

col1.html(
    f"""
    Total Investment
    <p style='margin-bottom: auto; font-weight: bold; color: darkblue'>
        {'Rs {:,.2f}'.format(st.session_state['investment'])}
    </div>
    """
)
col2.html(
    f"""
    Current Value
    <p style='margin-bottom: auto; font-weight: bold; color: blue'>
        {'Rs {:,.2f}'.format(st.session_state['current_value'])}
    </div>
    """
)
col3.html(
    f"""
    Total Profit/Loss
    <p style='margin-bottom: auto; font-weight: bold; {color_profit_loss(st.session_state['profit'])}'>
        {'Rs {:,.2f}'.format(st.session_state['profit'])}
    </div>
    """
)
col3.html(
    f"""
    Total Profit/Loss %
    <p style='margin-bottom: auto; font-weight: bold; {color_profit_loss(st.session_state['profit_percentage'])}'>
        {'{:,.2f} %'.format(st.session_state['profit_percentage'])}
    </div>
    """
)

col4.html(
    f"""
    Today's Profit/Loss
    <p style='margin-bottom: auto; font-weight: bold; {color_profit_loss(st.session_state['profit_today'])}'>
        {'Rs {:,.2f}'.format(st.session_state['profit_today'])}
    </div>
    """
)
col4.html(
    f"""
    Today's Profit/Loss %
    <p style='margin-bottom: auto; font-weight: bold; {color_profit_loss(st.session_state['profit_percentage_today'])}'>
        {'{:,.2f} %'.format(st.session_state['profit_percentage_today'])}
    </div>
    """
)

# st.subheader("", divider="rainbow")

if len(st.session_state["df"]) > 0:

    @st.dialog("Edit a stock")
    def open_edit_stock(row_num: int):
        selected_row = st.session_state["df"].iloc[row_num]
        # st.write(selected_row)
        if not selected_row.empty:
            quote_name = selected_row["stock_name"]
            stocks_edit_form = st.form(key="Edit stock")
            stocks_edit_form.text_input("Stock Name", value=quote_name, disabled=True)
            buy_date = stocks_edit_form.date_input(
                "Stock buy date",
                value=selected_row["buy_date"],
                help="When did you buy this?",
                min_value="2000-01-01",
                max_value=date.today(),
                format="YYYY-MM-DD",
            )
            buy_price = stocks_edit_form.number_input(
                "Stock buy price",
                step=0.01,
                min_value=0.01,
                format="%.2f",
                value=selected_row["buy_price"],
            )
            quantity = stocks_edit_form.number_input(
                "Quantity", step=1, min_value=1, value=selected_row["quantity"]
            )
            if stocks_edit_form.form_submit_button("Save"):
                save_stock(buy_date, buy_price, quantity, row_num)
                st.rerun()

    @st.dialog("Delete a stock")
    def open_delete_stock(row_num: int):
        selected_row = st.session_state["df"].iloc[row_num]
        # st.write(selected_row)
        if not selected_row.empty:
            quote_name = selected_row["stock_name"]
            stocks_delete_form = st.form(key="Delete stock")
            stocks_delete_form.text_input("Stock Name", value=quote_name, disabled=True)
            stocks_delete_form.date_input(
                "Stock buy date",
                value=selected_row["buy_date"],
                help="When did you buy this?",
                min_value="2000-01-01",
                max_value=date.today(),
                format="YYYY-MM-DD",
                disabled=True,
            )
            stocks_delete_form.number_input(
                "Stock buy price",
                step=0.01,
                min_value=0.01,
                format="%.2f",
                value=selected_row["buy_price"],
                disabled=True,
            )
            stocks_delete_form.number_input(
                "Quantity",
                step=1,
                min_value=1,
                value=selected_row["quantity"],
                disabled=True,
            )
            if stocks_delete_form.form_submit_button("Delete"):
                delete_stock(row_num)
                st.rerun()

    event = st.dataframe(
        st.session_state.df.style.map(
            color_profit_loss,
            subset=[
                "profit",
                "profit_percentage",
                "profit_today",
                "profit_percentage_today",
            ],
        ),
        # st.session_state.df,
        key="data",
        on_select="rerun",
        selection_mode=["single-row"],
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
            "profit_percentage": "Profit/Loss %",
            "profit_today": "Today's Profit/Loss",
            "profit_percentage_today": "Today's Profit/Loss %",
            "quantity": st.column_config.NumberColumn(
                "Quantity", help="Quantity?", step=1, min_value=1, required=True
            ),
        },
        hide_index=True,
    )

    st.html(
        """
        <hr color="linear-gradient(to right, #ff6c6c, #ffbd45, #3dd56d, #3d9df3, #9a5dff)">
        """
    )
    # st.subheader("", divider="rainbow")
    is_disabled = len(event.selection.rows) == 0
    par_button_col1, par_button_col2 = st.columns(
        2, border=False, vertical_alignment="top", gap="large"
    )
    button_col1, button_col2 = par_button_col1.columns(
        2, border=False, vertical_alignment="top", gap="small"
    )
    button_col3, button_col4 = par_button_col2.columns(
        2, border=False, vertical_alignment="top", gap="small"
    )
    if button_col3.button(
        "Add", key="add", icon="➕", help="Click to search and add a stock"
    ):
        open_add_stock()

    if button_col1.button(
        "Edit", key="edit", disabled=is_disabled, icon="✍️", help="Select a row to edit"
    ):
        open_edit_stock(event.selection.rows[0])

    if button_col2.button(
        "Delete",
        key="delete",
        disabled=is_disabled,
        icon="🗑️",
        help="Select a row to delete",
    ):
        open_delete_stock(event.selection.rows[0])
