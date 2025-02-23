import streamlit as st
import requests
import plotly.graph_objects as go

st.title("Backtesting Application")
timeframe = st.selectbox("Select Timeframe", ["1D", "1H", "15M"])
ticker = st.selectbox("Select Ticker", ["BTC/USD", "SOL/USD", "JUP/USD"])

if st.button("Load Data"):
    response = requests.get(
        "http://localhost:8000/api/default_chart",
        params={"timeframe": timeframe, "ticker": ticker}
    )
    if response.status_code == 200:
        data = response.json()
        fig = go.Figure(data=[go.Candlestick(
            x=data['time'],
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close']
        )])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"Error fetching data: {response.text}")