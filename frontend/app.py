import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

st.title("Backtesting Application")
timeframe = st.selectbox("Select Timeframe", ["1D", "1h", "15min"])
ticker = st.selectbox("Select Ticker", ["BTC/USD", "SOL/USD", "JUP/USD"])

# UI to load data
if st.button("Load Data"):
    response = requests.get(
        "http://localhost:8000/api/default_chart",
        params={"timeframe": timeframe, "ticker": ticker}
    )
    if response.status_code == 200:
        data_df = pd.DataFrame(response.json())
        # Convert time to datetime
        data_df['time'] = pd.to_datetime(data_df['time'])
        # Add date range selector based on min and max dates in the data
        min_date = data_df['time'].min().date()
        max_date = data_df['time'].max().date()
        date_range = st.date_input("Select Date Range", [min_date, max_date])
        if isinstance(date_range, list) and len(date_range) == 2:
            start_date, end_date = date_range
            data_df = data_df[(data_df['time'].dt.date >= start_date) & (data_df['time'].dt.date <= end_date)]
        # Limit to 100 data points (latest 100 rows)
        if len(data_df) > 100:
            data_df = data_df.tail(100)
        st.session_state['loaded_data'] = data_df
        st.success("Data Loaded!")
        # Render initial candlestick chart
        fig = go.Figure(data=[go.Candlestick(
            x=data_df['time'],
            open=data_df['open'],
            high=data_df['high'],
            low=data_df['low'],
            close=data_df['close']
        )])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"Error fetching data: {response.text}")

# UI to apply indicator if data is loaded
if 'loaded_data' in st.session_state:
    st.subheader("Manage Indicators")
    if 'indicators' not in st.session_state:
        st.session_state['indicators'] = []  # Each element: dict with type, params, active flag

    with st.form(key="indicator_form"):
        new_indicator = st.selectbox("Indicator Type", options=["sma", "ema", "rsi", "bollinger"])
        new_length = st.number_input("Length", min_value=1, value=10, key="length_input")
        new_active = st.checkbox("Enable", value=True, key="active_toggle")
        submitted_indicator = st.form_submit_button("Add Indicator")
        if submitted_indicator:
            st.session_state['indicators'].append({
                "type": new_indicator,
                "params": {"length": new_length},
                "active": new_active
            })
            st.success(f"Added {new_indicator} indicator.")

    st.write("Current Indicators:")
    for idx, ind in enumerate(st.session_state['indicators']):
        # Allow user to toggle active status for each indicator.
        cols = st.columns([3, 1])
        cols[0].write(f"{idx+1}. {ind['type'].upper()} with length {ind['params'].get('length')}")
        new_status = cols[1].checkbox("Active", value=ind.get("active", True), key=f"active_{idx}")
        st.session_state['indicators'][idx]["active"] = new_status

    if st.button("Apply Indicators"):
        # Filter only active indicators
        active_indicators = [ind for ind in st.session_state['indicators'] if ind.get("active")]
        payload = {
            "ticker": ticker,
            "timeframe": timeframe,
            "indicators": active_indicators
        }
        response = requests.post("http://localhost:8000/api/apply_indicators", json=payload)
        if response.status_code == 200:
            updated_df = pd.DataFrame(response.json())
            updated_df['time'] = pd.to_datetime(updated_df['time'])
            if len(updated_df) > 100:
                updated_df = updated_df.tail(100)
            st.session_state['loaded_data'] = updated_df
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=updated_df['time'],
                open=updated_df['open'],
                high=updated_df['high'],
                low=updated_df['low'],
                close=updated_df['close'],
                name="Price"
            ))
            # Overlay each applied indicator: assume naming as INDICATOR_length (upper-case)
            for ind in active_indicators:
                col_name = f"{ind['type'].upper()}_{ind['params'].get('length')}"
                if col_name in updated_df.columns:
                    fig.add_trace(go.Scatter(
                        x=updated_df['time'],
                        y=updated_df[col_name],
                        mode='lines',
                        name=col_name
                    ))
            fig.update_layout(xaxis_title="Time", yaxis_title="Price")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(f"Error applying indicators: {response.text}")

    st.subheader("Add Buy Conditions")
    if 'buy_conditions' not in st.session_state:
        st.session_state['buy_conditions'] = []

    # Prepare options for buy/sell condition operand selectboxes.
    default_fields = ["open", "high", "low", "close"]
    if 'loaded_data' in st.session_state:
        additional_fields = [col for col in st.session_state['loaded_data'].columns if col not in default_fields and col != "time"]
        operand_options = default_fields + additional_fields
    else:
        operand_options = default_fields

    with st.form(key='buy_condition_form'):
        buy_left = st.selectbox("Buy Condition Left Operand", options=operand_options, key='buy_left')
        buy_left_shift = st.number_input("Left Operand Shift", min_value=0, value=0, key='buy_left_shift')
        buy_comparator = st.selectbox("Comparator", options=[">", "<", "==", "!=", ">=", "<="], key='buy_comparator')
        buy_right = st.selectbox("Buy Condition Right Operand", options=operand_options, key='buy_right')
        buy_right_shift = st.number_input("Right Operand Shift", min_value=0, value=0, key='buy_right_shift')
        submitted_buy = st.form_submit_button("Add Buy Condition")
        if submitted_buy:
            condition = {
                "left_operand": {"column": buy_left, "shift": buy_left_shift},
                "comparator": buy_comparator,
                "right_operand": {"column": buy_right, "shift": buy_right_shift}
            }
            st.session_state['buy_conditions'].append(condition)
            st.success("Buy condition added")
    st.write("Current Buy Conditions:", st.session_state.get('buy_conditions'))

    st.subheader("Add Sell Conditions")
    if 'sell_conditions' not in st.session_state:
        st.session_state['sell_conditions'] = []
    with st.form(key='sell_condition_form'):
        sell_left = st.selectbox("Sell Condition Left Operand", options=operand_options, key='sell_left')
        sell_left_shift = st.number_input("Left Operand Shift", min_value=0, value=0, key='sell_left_shift')
        sell_comparator = st.selectbox("Comparator", options=[">", "<", "==", "!=", ">=", "<="], key='sell_comparator')
        sell_right = st.selectbox("Sell Condition Right Operand", options=operand_options, key='sell_right')
        sell_right_shift = st.number_input("Right Operand Shift", min_value=0, value=0, key='sell_right_shift')
        submitted_sell = st.form_submit_button("Add Sell Condition")
        if submitted_sell:
            condition = {
                "left_operand": {"column": sell_left, "shift": sell_left_shift},
                "comparator": sell_comparator,
                "right_operand": {"column": sell_right, "shift": sell_right_shift}
            }
            st.session_state['sell_conditions'].append(condition)
            st.success("Sell condition added")
    st.write("Current Sell Conditions:", st.session_state.get('sell_conditions'))

    st.subheader("Run Backtest")
    tp_value = st.number_input("Take Profit %", value=4)
    sl_value = st.number_input("Stop Loss %", value=3)
    account_size = st.number_input("Account Size", value=10000)
    risk_amt = st.number_input("Risk Amount %", value=1.0)
    if st.button("Run Backtest"):
        # Convert loaded_data Timestamps to strings for JSON serialization
        loaded_data_serializable = st.session_state['loaded_data'].copy()
        loaded_data_serializable['time'] = loaded_data_serializable['time'].apply(lambda x: x.isoformat())
        payload = {
            "backtestParams": {
                "tp": tp_value,
                "sl": sl_value,
                "account_size": account_size,
                "risk_amt": risk_amt,
                "buy_conditions": st.session_state.get('buy_conditions', []),
                "sell_conditions": st.session_state.get('sell_conditions', [])
            },
            "preparedDataframe": loaded_data_serializable.to_dict(orient='records')
        }
        response = requests.post("http://localhost:8000/custom_backtest", json=payload)
        if response.status_code == 200:
            result = response.json()
            # Display Backtest Summary using metrics
            st.subheader("Backtest Summary")
            summary = result.get("summary", {})
            if summary:
                cols = st.columns(3)
                for idx, (key, value) in enumerate(summary.items()):
                    col = cols[idx % 3]
                    # Format numbers nicely if possible
                    if isinstance(value, (int, float)):
                        display_value = round(value, 2)
                    else:
                        display_value = value
                    col.metric(label=key.replace("_", " ").title(), value=display_value)
            else:
                st.write("No summary available")
            # Get markers DataFrame from result
            markers = pd.DataFrame(result.get("markers", []))
            # Create chart using the loaded data
            loaded_data = st.session_state['loaded_data']
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=loaded_data['time'],
                open=loaded_data['open'],
                high=loaded_data['high'],
                low=loaded_data['low'],
                close=loaded_data['close'],
                name="Price"
            ))
            if not markers.empty:
                # Convert marker times to datetime
                markers['time'] = pd.to_datetime(markers['time'])
                # Map shape values to Plotly marker symbols.
                def map_shape(shape):
                    if shape == 'arrowUp':
                        return 'triangle-up'
                    elif shape == 'arrowDown':
                        return 'triangle-down'
                    elif shape == 'circle':
                        return 'circle'
                    else:
                        return 'circle'
                markers['symbol'] = markers['shape'].apply(map_shape)
                # Map textposition values to valid Plotly values
                def map_textposition(pos):
                    if pos == 'belowBar':
                        return 'bottom center'
                    elif pos == 'aboveBar':
                        return 'top center'
                    return pos
                # Add a trace for each marker
                for _, row in markers.iterrows():
                    fig.add_trace(go.Scatter(
                        x=[row['time']],
                        y=[row['price']],
                        mode='markers+text',
                        marker=dict(symbol=row['symbol'], color=row['color'], size=12),
                        text=[row['text']],
                        textposition=map_textposition(row['position']),
                        name=f"{row['type']} marker"
                    ))
            fig.update_layout(xaxis_title="Time", yaxis_title="Price")
            st.plotly_chart(fig, use_container_width=True)
            
            # --- New: Plot Account Sizes Over Time ---
            # Convert backtest stats to DataFrame for plotting
            backtest_stats = pd.DataFrame(result.get("backtest_result", []))
            if not backtest_stats.empty:
                # Use trade sequence as x-axis if time is not available
                if "entry_time" in backtest_stats.columns:
                    backtest_stats['entry_time'] = pd.to_datetime(backtest_stats['entry_time'])
                    x_axis = backtest_stats['entry_time']
                else:
                    x_axis = backtest_stats.index
                # Create a line chart for account sizes
                line_fig = go.Figure()
                if "account_size_quote" in backtest_stats.columns:
                    line_fig.add_trace(go.Scatter(
                        x=x_axis,
                        y=backtest_stats["account_size_quote"],
                        mode="lines+markers",
                        name="Account Size Quote"
                    ))
                if "account_size_base" in backtest_stats.columns and "exit_price" in backtest_stats.columns:
                    # Calculate account_size_base_value if not present
                    if "account_size_base_value" not in backtest_stats.columns:
                        backtest_stats["account_size_base_value"] = backtest_stats["account_size_base"] * backtest_stats["exit_price"]
                    line_fig.add_trace(go.Scatter(
                        x=x_axis,
                        y=backtest_stats["account_size_base_value"],
                        mode="lines+markers",
                        name="Account Size Base Value"
                    ))
                line_fig.update_layout(
                    title="Account Sizes Over Time",
                    xaxis_title="Trade Entry Time",
                    yaxis_title="Account Size Value",
                )
                st.plotly_chart(line_fig, use_container_width=True)
            else:
                st.write("No backtest stats available for account sizes.")
        else:
            st.error(f"Error running backtest: {response.text}")