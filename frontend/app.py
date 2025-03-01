import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

st.title("Moon Tester")
timeframe = st.selectbox("Select Timeframe", ["1D", "1h", "15min"])
ticker = st.selectbox("Select Ticker", ["BTC/USD", "SOL/USD", "JUP/USD"])

# UI to load data
if st.button("Load Data"):
    response = requests.get(
        "http://localhost:8000/api/default_chart",
        params={"timeframe": timeframe, "ticker": ticker}
    )
    if response.status_code == 200:
        # Store the full dataset
        full_data_df = pd.DataFrame(response.json())
        full_data_df['time'] = pd.to_datetime(full_data_df['time'])
        st.session_state['full_data'] = full_data_df
        
        # Create a date-filtered display dataset
        display_df = full_data_df.copy()
        
        # Add date range selector based on min and max dates in the data
        min_date = display_df['time'].min().date()
        max_date = display_df['time'].max().date()
        date_range = st.date_input("Select Date Range", [min_date, max_date])
        
        if isinstance(date_range, list) and len(date_range) == 2:
            start_date, end_date = date_range
            display_df = display_df[(display_df['time'].dt.date >= start_date) & (display_df['time'].dt.date <= end_date)]
            # Store the date range for future use
            st.session_state['date_range'] = (start_date, end_date)
        
        # Limit to 100 data points for display only
        if len(display_df) > 100:
            display_df = display_df.tail(100)
        
        st.session_state['display_data'] = display_df
        st.success(f"Data Loaded! Full dataset: {len(full_data_df)} bars, Display: {len(display_df)} bars")
        
        # Render initial candlestick chart
        fig = go.Figure(data=[go.Candlestick(
            x=display_df['time'],
            open=display_df['open'],
            high=display_df['high'],
            low=display_df['low'],
            close=display_df['close']
        )])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"Error fetching data: {response.text}")

# UI to apply indicator if data is loaded
if 'full_data' in st.session_state:
    st.subheader("Manage Indicators")
    if 'indicators' not in st.session_state:
        st.session_state['indicators'] = []  # Each element: dict with type, params, active flag

    with st.form(key="indicator_form"):
        # Add VWAP and MACD to the indicator options
        new_indicator = st.selectbox("Indicator Type", options=["sma", "ema", "rsi", "bollinger", "vwap", "macd"])
        
        # Conditional input fields based on indicator type
        if new_indicator in ["sma", "ema", "rsi", "bollinger"]:
            new_length = st.number_input("Length", min_value=1, value=10, key="length_input")
            params = {"length": new_length}
        elif new_indicator == "vwap":
            new_length = st.number_input("Length", min_value=1, value=14, key="length_input")
            params = {"length": new_length}
        elif new_indicator == "macd":
            # Additional parameters for MACD
            col1, col2, col3 = st.columns(3)
            fast = col1.number_input("Fast Period", min_value=1, value=12, key="fast_input")
            slow = col2.number_input("Slow Period", min_value=1, value=26, key="slow_input")
            signal = col3.number_input("Signal Period", min_value=1, value=9, key="signal_input")
            params = {"fast": fast, "slow": slow, "signal": signal}
        
        submitted_indicator = st.form_submit_button("Add Indicator")
        if submitted_indicator:
            st.session_state['indicators'].append({
                "type": new_indicator,
                "params": params,
                "active": True
            })
            st.success(f"Added {new_indicator} indicator.")

    st.write("Current Indicators:")
    if st.session_state['indicators']:
        for idx, ind in enumerate(st.session_state['indicators']):
            # Use columns for layout - indicator name and delete button
            col1, col2 = st.columns([4, 1])
            col1.write(f"{idx+1}. {ind['type'].upper()} with length {ind['params'].get('length')}")
            
            # Add delete button for each indicator
            if col2.button(f"Delete", key=f"del_ind_{idx}"):
                st.session_state['indicators'].pop(idx)
                st.experimental_rerun()
        
        # Add a button to clear all indicators
        if st.button("Clear All Indicators"):
            st.session_state['indicators'] = []
            st.success("All indicators cleared")
            st.experimental_rerun()
    else:
        st.info("No indicators added yet")

    if st.button("Apply Indicators"):
        # Use all indicators instead of filtering for active ones
        active_indicators = st.session_state['indicators']
        payload = {
            "ticker": ticker,
            "timeframe": timeframe,
            "indicators": active_indicators
        }
        response = requests.post("http://localhost:8000/api/apply_indicators", json=payload)
        if response.status_code == 200:
            # Update the full dataset with indicators
            full_data_updated = pd.DataFrame(response.json())
            full_data_updated['time'] = pd.to_datetime(full_data_updated['time'])
            
            # Update all data stores to ensure consistency
            st.session_state['full_data'] = full_data_updated
            st.session_state['loaded_data'] = full_data_updated  
            
            # Display the columns for debugging
            st.write(f"Available columns after applying indicators: {', '.join(full_data_updated.columns)}")
            
            # Apply date filtering to match previous display
            display_updated = full_data_updated.copy()
            if 'date_range' in st.session_state:
                start_date, end_date = st.session_state['date_range']
                display_updated = display_updated[(display_updated['time'].dt.date >= start_date) & 
                                                 (display_updated['time'].dt.date <= end_date)]
            
            # Limit to 100 data points for display only
            if len(display_updated) > 100:
                display_updated = display_updated.tail(100)
                
            st.session_state['display_data'] = display_updated
            
            # Separate indicators into overlay and separate indicators
            overlay_indicators = ['SMA', 'EMA', 'VWAP', 'BBL', 'BBM', 'BBU']
            oscillator_indicators = ['RSI', 'MACD']
            
            # First, create the main price chart with overlay indicators
            fig_price = go.Figure()
            
            # Add candlestick chart
            fig_price.add_trace(go.Candlestick(
                x=display_updated['time'],
                open=display_updated['open'],
                high=display_updated['high'],
                low=display_updated['low'],
                close=display_updated['close'],
                name="Price"
            ))
            
            # Create a color mapping for indicator types
            color_map = {
                'sma': 'rgba(46, 134, 193, 0.9)',    # Blue
                'ema': 'rgba(142, 68, 173, 0.9)',    # Purple
                'rsi': 'rgba(39, 174, 96, 0.9)',     # Green
                'macd': 'rgba(230, 126, 34, 0.9)',   # Orange
                'vwap': 'rgba(241, 196, 15, 0.9)',   # Yellow
            }
            
            # Find all Bollinger Band components
            bb_columns = {col: col.split('_')[0] for col in display_updated.columns 
                         if col.startswith(('BBL_', 'BBM_', 'BBU_'))}
            
            # Group BB columns by their length parameter
            bb_groups = {}
            for col, prefix in bb_columns.items():
                length = col.split('_')[1]
                if length not in bb_groups:
                    bb_groups[length] = []
                bb_groups[length].append(col)
            
            # Plot grouped Bollinger Bands with consistent styling
            for length, cols in bb_groups.items():
                # Choose a color for this BB group
                bb_color = f"rgba({hash(length) % 255}, {(hash(length) * 7) % 255}, {(hash(length) * 13) % 255}, 0.7)"
                
                for col in sorted(cols):  # Sort to ensure consistent order (BBL, BBM, BBU)
                    line_style = 'solid'
                    if col.startswith('BBL_'):
                        line_style = 'dash'
                    elif col.startswith('BBU_'):
                        line_style = 'dash'
                        
                    # Add to plot with consistent styling
                    fig_price.add_trace(go.Scatter(
                        x=display_updated['time'],
                        y=display_updated[col],
                        mode='lines',
                        line=dict(color=bb_color, dash=line_style, width=1),
                        name=f"BB_{length}" if col.startswith('BBM_') else f"{col}",
                        legendgroup=f"BB_{length}",
                        showlegend=col.startswith('BBM_')  # Only show legend for middle band
                    ))
            
            # Plot overlay indicators on the price chart
            for ind in active_indicators:
                ind_type = ind['type']
                
                # Skip oscillator indicators - they'll be in separate charts
                if any(ind_type.upper().startswith(osc) for osc in oscillator_indicators):
                    continue
                    
                # Skip Bollinger Bands - already plotted
                if ind_type == 'bollinger':
                    continue
                
                length = ind['params'].get('length', 0)
                col_name = f"{ind_type.upper()}_{length}"
                
                # Get a base color for this indicator type
                base_color = color_map.get(ind_type, f'rgba({hash(ind_type) % 255}, {(hash(ind_type) * 13) % 255}, {(hash(ind_type) * 23) % 255}, 0.9)')
                
                # For multiple indicators of the same type, slightly modify the color
                color_variance = 0.7 + (length % 5) * 0.1  # Small color variation based on length
                
                # Create a color with slight variation
                r, g, b = [int(c) for c in base_color.strip('rgba(').split(',')[:3]]
                r = min(255, int(r * color_variance))
                g = min(255, int(g * color_variance))
                b = min(255, int(b * color_variance))
                indicator_color = f'rgba({r}, {g}, {b}, 0.9)'
                
                if col_name in display_updated.columns:
                    fig_price.add_trace(go.Scatter(
                        x=display_updated['time'],
                        y=display_updated[col_name],
                        mode='lines',
                        line=dict(color=indicator_color, width=1.5),
                        name=col_name
                    ))
            
            # Check if we have any oscillator indicators that need separate panels
            has_rsi = any(ind['type'] == 'rsi' for ind in active_indicators)
            has_macd = any(ind['type'] == 'macd' for ind in active_indicators)
            
            # Import make_subplots if needed
            from plotly.subplots import make_subplots
            
            # Create subplot structure based on which oscillators are present
            rows = 1 + (1 if has_rsi else 0) + (1 if has_macd else 0)  # Main chart + optional RSI + optional MACD
            
            # Set row heights: main chart gets 70%, oscillators share the rest
            if rows == 1:
                row_heights = [1.0]
            elif rows == 2:
                row_heights = [0.7, 0.3]
            else:  # 3 rows
                row_heights = [0.6, 0.2, 0.2]
            
            # Create the figure with subplots
            fig = make_subplots(
                rows=rows, 
                cols=1,
                shared_xaxes=True,  # Share x-axis between subplots
                vertical_spacing=0.03,
                row_heights=row_heights,
                subplot_titles=["Price" + (" with Indicators" if rows > 1 else "")]
                + (["RSI"] if has_rsi else [])
                + (["MACD"] if has_macd else [])
            )
            
            # Add candlestick to main chart (first row)
            fig.add_trace(
                go.Candlestick(
                    x=display_updated['time'],
                    open=display_updated['open'],
                    high=display_updated['high'],
                    low=display_updated['low'],
                    close=display_updated['close'],
                    name="Price"
                ),
                row=1, col=1
            )
            
            # Plot Bollinger Bands on main chart
            # ...existing BB plotting code, but add row=1, col=1 to each add_trace call...
            for length, cols in bb_groups.items():
                bb_color = f"rgba({hash(length) % 255}, {(hash(length) * 7) % 255}, {(hash(length) * 13) % 255}, 0.7)"
                
                for col in sorted(cols):
                    line_style = 'solid'
                    if col.startswith('BBL_'):
                        line_style = 'dash'
                    elif col.startswith('BBU_'):
                        line_style = 'dash'
                        
                    fig.add_trace(
                        go.Scatter(
                            x=display_updated['time'],
                            y=display_updated[col],
                            mode='lines',
                            line=dict(color=bb_color, dash=line_style, width=1),
                            name=f"BB_{length}" if col.startswith('BBM_') else f"{col}",
                            legendgroup=f"BB_{length}",
                            showlegend=col.startswith('BBM_')
                        ),
                        row=1, col=1  # Always on main price chart
                    )
            
            # Plot overlay indicators on the price chart
            for ind in active_indicators:
                ind_type = ind['type']
                length = ind['params'].get('length', 0)
                
                # Skip oscillators - they'll be in their own rows
                if ind_type == 'rsi' or ind_type == 'macd':
                    continue
                # Skip Bollinger - already handled above
                if ind_type == 'bollinger':
                    continue
                
                col_name = f"{ind_type.upper()}_{length}"
                
                # Get color with variance
                # ...existing color code...
                base_color = color_map.get(ind_type, f'rgba({hash(ind_type) % 255}, {(hash(ind_type) * 13) % 255}, {(hash(ind_type) * 23) % 255}, 0.9)')
                
                # For multiple indicators of the same type, slightly modify the color
                color_variance = 0.7 + (length % 5) * 0.1
                
                # Create a color with slight variation
                r, g, b = [int(c) for c in base_color.strip('rgba(').split(',')[:3]]
                r = min(255, int(r * color_variance))
                g = min(255, int(g * color_variance))
                b = min(255, int(b * color_variance))
                indicator_color = f'rgba({r}, {g}, {b}, 0.9)'
                
                if col_name in display_updated.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=display_updated['time'],
                            y=display_updated[col_name],
                            mode='lines',
                            line=dict(color=indicator_color, width=1.5),
                            name=col_name
                        ),
                        row=1, col=1  # Always on the main price chart
                    )
            
            # Add RSI in its own panel if it exists
            panel_row = 2  # Start with second row for oscillators
            
            # Handle RSI panel
            for ind in active_indicators:
                if ind['type'] == 'rsi' and has_rsi:
                    length = ind['params'].get('length', 14)
                    col_name = f"RSI_{length}"
                    
                    if col_name in display_updated.columns:
                        # Add RSI line
                        fig.add_trace(
                            go.Scatter(
                                x=display_updated['time'],
                                y=display_updated[col_name],
                                mode='lines',
                                line=dict(color='rgba(39, 174, 96, 0.9)', width=1.5),
                                name=col_name
                            ),
                            row=panel_row, col=1
                        )
                        
                        # Add reference lines for RSI - fixed to use exact dates instead of normalized values
                        min_date = display_updated['time'].min()
                        max_date = display_updated['time'].max()
                        
                        # Reference lines for RSI (30 and 70)
                        for level in [30, 70]:
                            fig.add_shape(
                                type="line", 
                                x0=min_date, 
                                x1=max_date,
                                y0=level, 
                                y1=level,
                                line=dict(color="gray", width=1, dash="dash"),
                                row=panel_row, col=1
                            )
                        
                        # Set y-axis range for RSI
                        fig.update_yaxes(range=[0, 100], row=panel_row, col=1)
                    panel_row += 1  # Increment for next panel
                
            # Add MACD in its own panel if it exists
            macd_row = 2 if not has_rsi else 3
            for ind in active_indicators:
                if ind['type'] == 'macd' and has_macd:
                    # Get MACD parameters
                    fast = ind['params'].get('fast', 12)
                    slow = ind['params'].get('slow', 26)
                    signal = ind['params'].get('signal', 9)
                    
                    # Check for MACD columns
                    macd_col = f"MACD_{fast}_{slow}_{signal}"
                    signal_col = f"MACDs_{fast}_{slow}_{signal}"
                    hist_col = f"MACDh_{fast}_{slow}_{signal}"
                    
                    if macd_col in display_updated.columns:
                        # Add MACD line
                        fig.add_trace(
                            go.Scatter(
                                x=display_updated['time'],
                                y=display_updated[macd_col],
                                mode='lines',
                                line=dict(color='#2962FF', width=1.5),
                                name=f"MACD ({fast},{slow},{signal})"
                            ),
                            row=macd_row, col=1
                        )
                        
                        # Add Signal line
                        if signal_col in display_updated.columns:
                            fig.add_trace(
                                go.Scatter(
                                    x=display_updated['time'],
                                    y=display_updated[signal_col],
                                    mode='lines',
                                    line=dict(color='#FF6D00', width=1.5),
                                    name=f"Signal ({signal})"
                                ),
                                row=macd_row, col=1
                            )
                        
                        # Add Histogram as bar chart
                        if hist_col in display_updated.columns:
                            fig.add_trace(
                                go.Bar(
                                    x=display_updated['time'],
                                    y=display_updated[hist_col],
                                    marker=dict(
                                        color=display_updated[hist_col].apply(
                                            lambda x: 'rgba(0,255,0,0.5)' if x >= 0 else 'rgba(255,0,0,0.5)'
                                        )
                                    ),
                                    name="Histogram"
                                ),
                                row=macd_row, col=1
                            )
                        
                        # Add zero line reference
                        min_date = display_updated['time'].min()
                        max_date = display_updated['time'].max()
                        fig.add_shape(
                            type="line", 
                            x0=min_date, 
                            x1=max_date,
                            y0=0, 
                            y1=0,
                            line=dict(color="gray", width=1, dash="dash"),
                            row=macd_row, col=1
                        )
            
            # Update layout for the entire figure
            fig.update_layout(
                height=600 if rows > 1 else 500,  # Taller if we have subplots
                xaxis_rangeslider_visible=False,
                yaxis_autorange=True,
                margin=dict(t=30, b=30, l=30, r=30)
            )
            
            # Ensure x-axis matches the data range exactly
            fig.update_xaxes(
                range=[display_updated['time'].min(), display_updated['time'].max()],
                autorange=False  # Disable autorange to use our explicit range
            )
            
            # Display the unified chart with shared x-axis
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.error(f"Error applying indicators: {response.text}")

    st.subheader("Add Buy Conditions")
    if 'buy_conditions' not in st.session_state:
        st.session_state['buy_conditions'] = []

    # Prepare options for buy/sell condition operand selectboxes.
    default_fields = ["open", "high", "low", "close"]
    indicator_options = []
    
    # Get all available columns from full data if it exists
    if 'full_data' in st.session_state:
        full_data_cols = list(st.session_state['full_data'].columns)
        indicator_options = [col for col in full_data_cols 
                            if col not in default_fields 
                            and col != "time"
                            and not col.startswith("buy_") 
                            and not col.startswith("sell_")]
    
    operand_options = default_fields + indicator_options
    
    # Debug what columns are available
    st.write(f"Condition options: {operand_options}")

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
    
    # Display and manage existing buy conditions
    if st.session_state.get('buy_conditions'):
        st.write(f"Current Buy Conditions ({len(st.session_state['buy_conditions'])})")
        for i, cond in enumerate(st.session_state['buy_conditions']):
            col1, col2 = st.columns([4, 1])
            condition_text = (f"{cond['left_operand']['column']} (shift {cond['left_operand']['shift']}) "
                            f"{cond['comparator']} "
                            f"{cond['right_operand']['column']} (shift {cond['right_operand']['shift']})")
            col1.text(f"{i+1}. {condition_text}")
            # Add delete button for each condition
            if col2.button(f"Delete", key=f"del_buy_{i}"):
                st.session_state['buy_conditions'].pop(i)
                st.experimental_rerun()
        
        # Add a button to clear all conditions
        if st.button("Clear All Buy Conditions"):
            st.session_state['buy_conditions'] = []
            st.success("All buy conditions cleared")
            st.experimental_rerun()
    else:
        st.info("No buy conditions defined yet")

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
    
    # Display and manage existing sell conditions
    if st.session_state.get('sell_conditions'):
        st.write(f"Current Sell Conditions ({len(st.session_state['sell_conditions'])})")
        for i, cond in enumerate(st.session_state['sell_conditions']):
            col1, col2 = st.columns([4, 1])
            condition_text = (f"{cond['left_operand']['column']} (shift {cond['left_operand']['shift']}) "
                            f"{cond['comparator']} "
                            f"{cond['right_operand']['column']} (shift {cond['right_operand']['shift']})")
            col1.text(f"{i+1}. {condition_text}")
            # Add delete button for each condition
            if col2.button(f"Delete", key=f"del_sell_{i}"):
                st.session_state['sell_conditions'].pop(i)
                st.experimental_rerun()
        
        # Add a button to clear all conditions
        if st.button("Clear All Sell Conditions"):
            st.session_state['sell_conditions'] = []
            st.success("All sell conditions cleared")
            st.experimental_rerun()
    else:
        st.info("No sell conditions defined yet")

    st.subheader("Run Backtest")
    tp_value = st.number_input("Take Profit %", value=4)
    sl_value = st.number_input("Stop Loss %", value=3)
    account_size = st.number_input("Account Size", value=10000)
    risk_amt = st.number_input("Risk Amount %", value=1.0)
    if st.button("Run Backtest"):
        if 'full_data' not in st.session_state:
            st.error("Please load data first!")
        else:
            # Use the full dataset for backtesting
            full_data_serializable = st.session_state['full_data'].copy()
            full_data_serializable['time'] = full_data_serializable['time'].apply(lambda x: x.isoformat())
            
            # Debug information
            st.info(f"Running backtest on {len(full_data_serializable)} bars with {len(st.session_state.get('buy_conditions', []))} buy conditions and {len(st.session_state.get('sell_conditions', []))} sell conditions")
            
            payload = {
                "backtestParams": {
                    "tp": tp_value,
                    "sl": sl_value,
                    "account_size": account_size,
                    "risk_amt": risk_amt,
                    "buy_conditions": st.session_state.get('buy_conditions', []),
                    "sell_conditions": st.session_state.get('sell_conditions', [])
                },
                "preparedDataframe": full_data_serializable.to_dict(orient='records')
            }
            
            with st.spinner('Running backtest...'):
                response = requests.post("http://localhost:8000/custom_backtest", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                # Display Backtest Summary
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
                # Create chart using the display data (not the full dataset)
                display_data = st.session_state['display_data']
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=display_data['time'],
                    open=display_data['open'],
                    high=display_data['high'],
                    low=display_data['low'],
                    close=display_data['close'],
                    name="Price"
                ))
                
                # Filter markers to only those in the display data's time range
                if not markers.empty:
                    markers['time'] = pd.to_datetime(markers['time'])
                    
                    # Get the time range of the displayed data
                    min_display_time = display_data['time'].min()
                    max_display_time = display_data['time'].max()
                    
                    # Filter markers to only those within the displayed time window
                    visible_markers = markers[
                        (markers['time'] >= min_display_time) & 
                        (markers['time'] <= max_display_time)
                    ]
                    
                    st.write(f"Showing {len(visible_markers)} of {len(markers)} total trade signals in the chart view")
                    
                    # Map shape values to Plotly marker symbols
                    def map_shape(shape):
                        if shape == 'arrowUp':
                            return 'triangle-up'
                        elif shape == 'arrowDown':
                            return 'triangle-down'
                        elif shape == 'circle':
                            return 'circle'
                        else:
                            return 'circle'
                    visible_markers['symbol'] = visible_markers['shape'].apply(map_shape)
                    
                    # Map textposition values to valid Plotly values
                    def map_textposition(pos):
                        if pos == 'belowBar':
                            return 'bottom center'
                        elif pos == 'aboveBar':
                            return 'top center'
                        return pos
                    # Add a trace for each visible marker
                    for _, row in visible_markers.iterrows():
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
                            mode="lines",
                            name="Account Size Quote"
                        ))
                    if "account_size_base" in backtest_stats.columns and "exit_price" in backtest_stats.columns:
                        # Calculate account_size_base_value if not present
                        if "account_size_base_value" not in backtest_stats.columns:
                            backtest_stats["account_size_base_value"] = backtest_stats["account_size_base"] * backtest_stats["exit_price"]
                        line_fig.add_trace(go.Scatter(
                            x=x_axis,
                            y=backtest_stats["account_size_base_value"],
                            mode="lines",
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