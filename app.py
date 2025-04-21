import yfinance as yf
import streamlit as st
from streamlit_searchbox import st_searchbox
import time
import pandas as pd
from streamlit_option_menu import option_menu
import numpy as np
from datetime import date, datetime, timedelta
from plotly import graph_objs as go
from babel.numbers import format_currency
import pyodbc
from cryptography.fernet import Fernet
import streamlit.components.v1 as components

st.set_page_config(page_title="My Portfolio", page_icon=":moneybag:", layout="wide")

if "show_login" not in st.session_state:
    st.session_state["show_login"] = True
if "login_success" not in st.session_state:
    st.session_state["login_success"] = False
if "user_id" not in st.session_state:
    st.session_state["user_id"] = ""
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
if "profit_percentage_today" not in st.session_state:
    st.session_state["profit_percentage_today"] = float(0)
if "user_name" not in st.session_state:
    st.session_state["user_name"] = None
if "is_refresh" not in st.session_state:
    st.session_state["is_refresh"] = False
if "is_refresh_from_db" not in st.session_state:
    st.session_state["is_refresh_from_db"] = True


@st.cache_resource(show_spinner="Initialising...Please wait!!!")
def init_connection():
    try:
        return pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};SERVER="
            + st.secrets["DB_SERVER"]
            + ";DATABASE="
            + st.secrets["DB"]
            + ";UID="
            + st.secrets["DB_USER"]
            + ";PWD="
            + st.secrets["DB_PASSWORD"],
            timeout=60,
        )
    except Exception as e:
        st.error("Internal Error occurred!!! Try again...")


@st.cache_data(ttl=600)
def execute_query_cached(query, *params):
    conn = init_connection()
    with conn.cursor() as cur:
        try:
            cur.execute(query, params)
            return cur.fetchall()
        except Exception as e:
            st.error("Internal Error occurred!!!")


def execute_query(query, *params):
    conn = init_connection()
    with conn.cursor() as cur:
        try:
            cur.execute(query, params)
            return cur.fetchall()
        except Exception as e:
            st.error("Internal Error occurred!!!")


def execute_update(query, *params):
    conn = init_connection()
    with conn.cursor() as cur:
        try:
            cur.execute(query, params)
            cur.commit()
        except Exception as e:
            st.error("Internal Error occurred!!!")


@st.cache_resource
def init_fernet():
    return Fernet(st.secrets["SECRET_KEY"])


def decrypt_password(encrypted_password: str):
    return init_fernet().decrypt(encrypted_password.encode()).decode()


def encrypt_password(decrypted_password: str):
    return init_fernet().encrypt(decrypted_password.encode()).decode()


def find_stock(search_term: str):
    if search_term and len(search_term) < 3:
        return []
    else:
        return [
            f"{quote['shortname']}:::{quote['exchange']}:::{quote['symbol']}"
            for quote in yf.Search(search_term, include_cb=False).quotes
        ]


def find_stock_price(symbol: str):
    return yf.Ticker(symbol)


def find_prices(symbol: str):
    nifty = yf.Ticker(symbol)
    # current = nifty.history(period="5d")["Close"].iloc[-1]
    # last = nifty.history(period="5d")["Close"].iloc[-2]
    current = nifty.history_metadata["regularMarketPrice"]
    last = nifty.history_metadata["previousClose"]
    change = current - last
    percentage_change = (change / last) * 100
    current_formatted = f"₹{current:.2f}"
    change_formatted = f"{change:.2f}"
    percentage_change_formatted = f"{percentage_change:.2f}%"
    return current_formatted, change_formatted, percentage_change_formatted


def get_prices(df):
    symbols = df["symbol"]
    prices = yf.Tickers(" ".join(symbols))
    # st.write(prices.tickers)
    return prices.tickers


def fetch_stocks(user_id: str):
    df = pd.read_sql(
        con=init_connection(),
        sql="select symbol, stock_name, buy_date, buy_price, quantity from stocks where user_id = ?;",
        params=user_id,
    )
    if len(df) > 0:
        df["buy_date"] = pd.to_datetime(df["buy_date"], yearfirst=True).dt.date
    else:
        df = pd.DataFrame(
            columns=[
                "symbol",
                "stock_name",
                "buy_date",
                "buy_price",
                "quantity",
                "price",
                "investment",
                "current_value",
                "profit",
                "profit_percentage",
                "profit_today",
                "profit_percentage_today",
                "link",
            ]
        )

    return df


def color_profit_loss(val):
    color = "green" if val >= 0 else "red"
    return f"color: {color}"


def calculate_prices(df):
    previous_investment = float(0)
    tickers = get_prices(df)
    for index, symbol in df["symbol"].items():
        info = tickers[symbol].info
        price = info.get("currentPrice")
        previous_close = info.get("previousClose")
        buy_price = df.at[index, "buy_price"]
        quantity = df.at[index, "quantity"]
        investment = buy_price * quantity
        current_value = price * quantity
        previous_investment = previous_investment + (previous_close * quantity)
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
        df.at[index, "link"] = f"https://finance.yahoo.com/chart/{symbol}/"

    if len(df["symbol"]) > 0:
        st.session_state["investment"] = df["investment"].sum()
        st.session_state["current_value"] = df["current_value"].sum()
        st.session_state["profit"] = df["profit"].sum()
        st.session_state["profit_percentage"] = (
            st.session_state["profit"] * 100 / st.session_state["investment"]
        )
        st.session_state["profit_today"] = df["profit_today"].sum()
        st.session_state["profit_percentage_today"] = (
            st.session_state["profit_today"] * 100 / previous_investment
        )

    return df


if st.session_state.login_success and st.session_state.is_refresh_from_db:
    df = fetch_stocks(st.session_state.user_id)
    st.session_state.is_refresh_from_db = False
    st.session_state.is_refresh = False
    st.session_state["df"] = calculate_prices(df)
elif st.session_state.login_success and st.session_state.is_refresh:
    st.session_state.is_refresh_from_db = False
    st.session_state.is_refresh = False
    st.session_state["df"] = calculate_prices(st.session_state["df"])

if "selected_stock_name" not in st.session_state:
    st.session_state["selected_stock_name"] = None
if "selected_stock" not in st.session_state:
    st.session_state["selected_stock"] = None


def save_stock(
    symbol: str,
    stock_name: str = None,
    buy_date: date = None,
    buy_price: float = None,
    quantity: int = None,
):
    user_id = st.session_state.user_id
    try:
        if not stock_name and not buy_date:
            execute_update(
                "delete from stocks where symbol = ? and user_id = ?;",
                symbol,
                user_id,
            )
            st.write(f"'{symbol}' deleted successfully!!!")
        elif not stock_name and buy_date:
            execute_update(
                """update stocks 
                    set buy_date = ?, buy_price = ?, quantity = ? 
                    where symbol = ? and user_id = ?;""",
                buy_date,
                buy_price,
                quantity,
                symbol,
                user_id,
            )
            st.write(f"'{symbol}' updated successfully!!!")
        else:
            execute_update(
                """insert into stocks
                        (user_id, symbol, stock_name, buy_date, buy_price, quantity) 
                        values(?, ?, ?, ?, ?, ?);""",
                user_id,
                symbol,
                stock_name,
                buy_date,
                buy_price,
                quantity,
            )
            st.write(f"'{stock_name}' added successfully!!!")
        refresh_data(True)

    except Exception as e:
        st.error("Internal Error occurred!!!")


def refresh_data(is_refresh_from_db: bool = False):
    st.session_state.is_refresh_from_db = is_refresh_from_db
    st.session_state.is_refresh = True
    st.rerun()


@st.dialog("Search and add stock")
def open_add_stock():
    st.session_state["selected_stock_name"] = st_searchbox(
        find_stock,
        "\n\nSearch for a stock",
        rerun_scope="fragment",
        clear_on_submit=True,
    )
    selected_stock_name = st.session_state["selected_stock_name"]
    if selected_stock_name:
        # st.write(selected_stock_name)
        symbol = selected_stock_name.split(":::")[2]
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
                st.session_state.pop("selected_stock_name", None)
                save_stock(symbol, stock_name, buy_date, buy_price, quantity)


@st.dialog("Edit a stock")
def open_edit_stock(row_num: int):
    selected_row = st.session_state["df"].iloc[row_num]
    # st.write(selected_row)
    if not selected_row.empty:
        symbol = selected_row["symbol"]
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
            save_stock(symbol, None, buy_date, buy_price, quantity)


@st.dialog("Delete a stock")
def open_delete_stock(row_num: int):
    selected_row = st.session_state["df"].iloc[row_num]
    # st.write(selected_row)
    if not selected_row.empty:
        symbol = selected_row["symbol"]
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
            save_stock(symbol)


@st.dialog("Stock information", width="large")
def open_stock_info(row_num: int):
    selected_row = st.session_state["df"].iloc[row_num]
    # st.write(selected_row)
    if not selected_row.empty:
        symbol = selected_row["symbol"]
        quote_name = selected_row["stock_name"]
        components.iframe("", height=500)


def show_login_form(is_login: bool):
    st.session_state.show_login = is_login


def login(user_id_param, password_param):
    user_id_lower = user_id_param.lower().replace(" ", "")
    try:
        rows = execute_query("select * from users where user_id = ?;", user_id_lower)
        # Print results.
        for user in rows:
            decrypted_password = decrypt_password(user.user_pass)
            if decrypted_password == password_param:
                st.session_state.name = user.name
                st.session_state.login_success = True
                st.session_state.user_id = user.id
                st.session_state.user_name = user.name

        if st.session_state.login_success:
            st.write("Successfully logged in!!!")
            st.rerun()
        else:
            st.write("Incorrect userId/password!!!")
    except Exception as e:
        st.error("Internal Error occurred!!!")


def register(name_param, user_id_param, password_param):
    user_id_lower = user_id_param.lower()
    try:
        rows = execute_query("select * from users where user_id = ?;", user_id_lower)
        if len(rows) > 0:
            st.write(f"User Id '{user_id_param}' already registered!!!")
            show_login_form(True)
        else:
            encrypted_password = encrypt_password(password_param)
            execute_update(
                "insert into users (name, user_id, user_pass) values(?,?,?);",
                name_param,
                user_id_lower,
                encrypted_password,
            )
            st.write("Registered successfully!!!")
            show_login_form(True)

    except Exception as e:
        st.error("Internal Error occurred!!!")


@st.dialog("Login form")
def open_login_form():
    if not st.session_state.login_success and st.session_state.show_login:
        st.title("Login")
        user_id = st.text_input(
            label="User Id",
            key="userid_login",
            max_chars=40,
            placeholder="Enter your user id",
        )
        password = st.text_input(
            label="Password",
            key="pass_login",
            type="password",
            max_chars=40,
            placeholder="Enter your password",
        )

        if st.button("Login", key="login", disabled=(user_id == "" or password == "")):
            login(user_id, password)
        if st.button("Signup", key="showSignup"):
            show_login_form(False)

    elif not st.session_state.login_success and not st.session_state.show_login:
        st.title("Register")
        name = st.text_input(
            label="Name",
            key="name_register",
            max_chars=40,
            placeholder="Enter your name",
        )
        user_id = st.text_input(
            label="User Id",
            key="userid_register",
            max_chars=40,
            placeholder="Enter your user id",
        )
        password = st.text_input(
            label="Password",
            key="pass_register",
            type="password",
            max_chars=40,
            placeholder="Enter your password",
        )
        if st.button(
            "Signup",
            key="signup",
            on_click=register,
            args=(name, user_id, password),
            disabled=(user_id == "" or password == "" or name == ""),
        ):
            register(name, user_id, password)
        if st.button("Login", key="showLogin"):
            show_login_form(True)


st.subheader("Market", divider="rainbow")
current_nifty, change_nifty, percentage_change_nifty = find_prices("^NSEI")
current_mid, change_mid, percentage_change_mid = find_prices("NIFTY_MIDCAP_100.NS")
current_small, change_small, percentage_change_small = find_prices("^CNXSC")
current_bank, change_bank, percentage_change_bank = find_prices("^NSEBANK")
col1, col2, col3, col4, col5 = st.columns(5)
with col2:
    st.metric(
        label="Nifty",
        value=current_nifty,
        delta=f"{change_nifty} ({percentage_change_nifty})",
    )
with col3:
    st.metric(
        label="Midcap 100",
        value=current_mid,
        delta=f"{change_mid} ({percentage_change_mid})",
    )
with col4:
    st.metric(
        label="Smallcap 100",
        value=current_small,
        delta=f"{change_small} ({percentage_change_small})",
    )
with col1:
    st.metric(
        label="Bank Nifty",
        value=current_bank,
        delta=f"{change_bank} ({percentage_change_bank})",
    )
with col5:
    if st.button(
        "View Portfolio",
        key="show_login_key",
        help="Login to view your portfolio",
        use_container_width=True,
        type="primary",
        disabled=st.session_state.login_success,
    ):
        init_connection()
        open_login_form()


if st.session_state.login_success and "df" in st.session_state:
    st.subheader(
        f"My Portfolio: {st.session_state.user_name if st.session_state.user_name else ''}",
        divider="rainbow",
    )

    if len(st.session_state.df) > 0:
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric(
            label="Total Investment",
            value=format_currency(
                st.session_state["investment"], "INR", locale="en_IN"
            ).replace("\xa0", " "),
        )
        col2.metric(
            label="Current Value & Total Profit/Loss",
            value=format_currency(
                st.session_state["current_value"], "INR", locale="en_IN"
            ).replace("\xa0", " "),
            delta=f"{format_currency(st.session_state['profit'], 'INR', locale='en_IN').replace(u'\xa0', u' ')} ({
            '{:,.3f} %'.format(st.session_state['profit_percentage'])})",
        )
        col3.metric(
            label="Current Value & Today's Profit/Loss",
            value=format_currency(
                st.session_state["current_value"], "INR", locale="en_IN"
            ).replace("\xa0", " "),
            delta=f"{format_currency(st.session_state['profit_today'], 'INR', locale='en_IN').replace(u'\xa0', u' ')} ({
            '{:,.3f} %'.format(st.session_state['profit_percentage_today'])})",
        )
        if col5.button(
            "Refresh",
            key="refresh_key",
            help="Click to refresh the prices",
            use_container_width=True,
            type="primary",
        ):
            refresh_data()

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
        column_order=[
            "link",
            "stock_name",
            "buy_date",
            "buy_price",
            "quantity",
            "price",
            "investment",
            "current_value",
            "profit",
            "profit_percentage",
            "profit_today",
            "profit_percentage_today",
        ],
        column_config={
            "link": st.column_config.LinkColumn(
                "Symbol",
                help="Stock information",
                display_text=r"https://finance\.yahoo\.com/chart/(.*?)/",
            ),
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
                format="%.2f",
            ),
            "quantity": st.column_config.NumberColumn(
                "Quantity",
                help="Quantity?",
            ),
            "price": st.column_config.NumberColumn(
                "Price",
                help="Stock price",
                format="%.2f",
            ),
            "investment": st.column_config.NumberColumn(
                "Investment",
                help="Investment",
                format="%.2f",
            ),
            "current_value": st.column_config.NumberColumn(
                "Market Value",
                help="Market Value",
                format="%.2f",
            ),
            "profit": st.column_config.NumberColumn(
                "Profit/Loss",
                help="Profit/Loss",
                format="%.2f",
            ),
            "profit_percentage": st.column_config.NumberColumn(
                "Profit/Loss %",
                help="Profit/Loss %",
                format="%.3f",
            ),
            "profit_today": st.column_config.NumberColumn(
                "Today's Profit/Loss",
                help="Today's Profit/Loss",
                format="%.2f",
            ),
            "profit_percentage_today": st.column_config.NumberColumn(
                "Today's Profit/Loss %",
                help="Today's Profit/Loss %",
                format="%.3f",
            ),
        },
        hide_index=True,
        use_container_width=True,
    )

    st.html(
        """
        <hr color="linear-gradient(to right, #ff6c6c, #ffbd45, #3dd56d, #3d9df3, #9a5dff)">
        """
    )
    is_disabled = len(event.selection.rows) == 0
    col1, col2, col3, col4, col5 = st.columns(5)
    if col5.button(
        "Add",
        key="add",
        icon="➕",
        use_container_width=True,
        help="Click to search and add a stock",
        type="primary",
    ):
        open_add_stock()

    if col1.button(
        "Edit",
        key="edit",
        disabled=is_disabled,
        icon="✍️",
        use_container_width=True,
        help="Select a row to edit",
        type="primary",
    ):
        open_edit_stock(event.selection.rows[0])

    if col2.button(
        "Delete",
        key="delete",
        disabled=is_disabled,
        icon="🚮",
        use_container_width=True,
        help="Select a row to delete",
        type="primary",
    ):
        open_delete_stock(event.selection.rows[0])
