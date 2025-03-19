import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import os
from PIL import Image

# Hide the hamburger menu and customize footer
st.markdown("""
<style>
    /* Hide the hamburger menu */
    #MainMenu {visibility: hidden;}
    
    /* Hide Streamlit footer completely */
    footer {visibility: hidden;}
    
    /* Remove the footer space which still shows up */
    .block-container {
        padding-bottom: 0px;
    }
</style>
""", unsafe_allow_html=True)



# Configuration for different indicator types
indicator_config = {
    "sma": {"params": [{"name": "length", "type": "number_input", "min_value": 1, "default": 21}]},
    "ema": {"params": [{"name": "length", "type": "number_input", "min_value": 1, "default": 50}]},
    "rsi": {"params": [{"name": "length", "type": "number_input", "min_value": 1, "default": 14}]},
    "bollinger": {"params": [{"name": "length", "type": "number_input", "min_value": 1, "default": 20}]},
    "vwap": {"params": [{"name": "anchor", "type": "selectbox", "options": ["D", "W", "M"], "default": "D"}]},
    "macd": {"params": [
        {"name": "fast", "type": "number_input", "min_value": 1, "default": 12},
        {"name": "slow", "type": "number_input", "min_value": 1, "default": 26},
        {"name": "signal", "type": "number_input", "min_value": 1, "default": 9}
    ]}
}

def render_indicator_params(indicator_type):
    """Render parameter form fields and return collected parameters"""
    params = {}
    
    if indicator_type not in indicator_config:
        st.error(f"Unknown indicator type: {indicator_type}")
        return params
    
    config = indicator_config[indicator_type]
    
    # For indicators with multiple parameters (like MACD), create columns
    if len(config["params"]) > 2:
        cols = st.columns(len(config["params"]))
    else:
        cols = [st] * len(config["params"])  # Use single column layout
        
    # Render each parameter based on its type
    for i, param in enumerate(config["params"]):
        if param["type"] == "number_input":
            params[param["name"]] = cols[i].number_input(
                param["name"].title(), 
                min_value=param.get("min_value", 1), 
                value=param.get("default", 10),
                key=f"{indicator_type}_{param['name']}_input"
            )
        elif param["type"] == "selectbox":
            params[param["name"]] = cols[i].selectbox(
                param["name"].title(), 
                options=param.get("options", []),
                index=param.get("options", []).index(param.get("default")) if param.get("default") in param.get("options", []) else 0,
                key=f"{indicator_type}_{param['name']}_input"
            )
            
    return params

def generate_indicator_color(ind_type, params):
    """Generate color for an indicator with variance based on parameters"""
    # Base colors for different indicator types
    color_map = {
        'sma': 'rgba(46, 134, 193, 0.9)',    # Blue
        'ema': 'rgba(142, 68, 173, 0.9)',    # Purple
        'rsi': 'rgba(39, 174, 96, 0.9)',     # Green
        'macd': 'rgba(230, 126, 34, 0.9)',   # Orange
        'vwap': 'rgba(241, 196, 15, 0.9)',   # Yellow
    }
    
    # Get base color
    base_color = color_map.get(ind_type, f'rgba({hash(ind_type) % 255}, {(hash(ind_type) * 13) % 255}, {(hash(ind_type) * 23) % 255}, 0.9)')
    
    # Get variance parameter based on indicator type
    if ind_type == 'vwap':
        anchor = params.get('anchor', 'D')
        variance_param = hash(anchor) % 5
    elif ind_type == 'macd':
        fast = params.get('fast', 12)
        slow = params.get('slow', 26)
        variance_param = (fast + slow) % 5
    else:
        length = params.get('length', 0)
        variance_param = length % 5
    
    # Calculate color variance
    color_variance = 0.7 + variance_param * 0.1  # Small color variation
    
    # Create a color with slight variation
    r, g, b = [int(c) for c in base_color.strip('rgba(').split(',')[:3]]
    r = min(255, int(r * color_variance))
    g = min(255, int(g * color_variance))
    b = min(255, int(b * color_variance))
    return f'rgba({r}, {g}, {b}, 0.9)'

def create_price_chart(fig, data, row=1, col=1):
    """Add price candlesticks to figure"""
    fig.add_trace(
        go.Candlestick(
            x=data['time'],
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            name="Price"
        ),
        row=row, col=col
    )
    return fig

def add_indicator_to_chart(fig, data, indicator_info, row=1, col=1):
    """Add a single indicator to the figure based on its type"""
    ind_type = indicator_info['type']
    
    # Get the appropriate column name
    if ind_type == 'vwap':
        anchor = indicator_info['params'].get('anchor', 'D')
        col_name = f"{ind_type.upper()}_{anchor}"
    elif ind_type == 'macd':
        fast = indicator_info['params'].get('fast', 12)
        slow = indicator_info['params'].get('slow', 26)
        signal = indicator_info['params'].get('signal', 9)
        col_name = f"MACD_{fast}_{slow}_{signal}"
    else:
        length = indicator_info['params'].get('length', 0)
        col_name = f"{ind_type.upper()}_{length}"
    
    # Only add if column exists
    if col_name in data.columns:
        # Generate color
        color = generate_indicator_color(ind_type, indicator_info['params'])
        
        # Add to figure
        fig.add_trace(
            go.Scatter(
                x=data['time'],
                y=data[col_name],
                mode='lines',
                line=dict(color=color, width=1.5),
                name=col_name
            ),
            row=row, col=col
        )
    
    return fig

def create_condition_section(condition_type, operand_options):
    """Create and manage trading conditions (buy or sell)"""
    state_key = f'{condition_type}_conditions'
    
    st.subheader(f"Add {condition_type.title()} Conditions")
    if state_key not in st.session_state:
        st.session_state[state_key] = []
    
    with st.form(key=f'{condition_type}_condition_form'):
        left = st.selectbox(f"{condition_type.title()} Condition Left Operand", 
                           options=operand_options, 
                           key=f'{condition_type}_left')
        left_shift = st.number_input("Left Operand Shift", 
                                    min_value=0, 
                                    value=0, 
                                    key=f'{condition_type}_left_shift')
        comparator = st.selectbox("Comparator", 
                                 options=[">", "<", "==", "!=", ">=", "<="], 
                                 key=f'{condition_type}_comparator')
        right = st.selectbox(f"{condition_type.title()} Condition Right Operand", 
                            options=operand_options, 
                            key=f'{condition_type}_right')
        right_shift = st.number_input("Right Operand Shift", 
                                     min_value=0, 
                                     value=0, 
                                     key=f'{condition_type}_right_shift')
        submitted = st.form_submit_button(f"Add {condition_type.title()} Condition")
        
        if submitted:
            condition = {
                "left_operand": {"column": left, "shift": left_shift},
                "comparator": comparator,
                "right_operand": {"column": right, "shift": right_shift}
            }
            st.session_state[state_key].append(condition)
            st.success(f"{condition_type.title()} condition added")
    
    # Display existing conditions
    if st.session_state.get(state_key):
        st.write(f"Current {condition_type.title()} Conditions ({len(st.session_state[state_key])})")
        for i, cond in enumerate(st.session_state[state_key]):
            col1, col2 = st.columns([4, 1])
            condition_text = (f"{cond['left_operand']['column']} (shift {cond['left_operand']['shift']}) "
                            f"{cond['comparator']} "
                            f"{cond['right_operand']['column']} (shift {cond['right_operand']['shift']})")
            col1.text(f"{i+1}. {condition_text}")
            if col2.button(f"Delete", key=f"del_{condition_type}_{i}"):
                st.session_state[state_key].pop(i)
                st.experimental_rerun()
        
        if st.button(f"Clear All {condition_type.title()} Conditions"):
            st.session_state[state_key] = []
            st.success(f"All {condition_type} conditions cleared")
            st.experimental_rerun()
    else:
        st.info(f"No {condition_type} conditions defined yet")


# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(current_dir, "assets", "moon-logo.png")

# Create a row with the logo and title
col1, col2 = st.columns([1, 8])  # Adjust the ratio based on your logo size

# Display logo in the first column
if os.path.exists(logo_path):
    col1.image(logo_path, width=80)  # Adjust width as needed
else:
    col1.error("Logo not found")

# Display title in the second column
col2.title("MoonTester")



timeframe = st.selectbox("Select Timeframe", ["1D", "4h","1h", "15min"])
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
        st.success(f"Data Loaded! Full dataset: {len(full_data_df)} bars")
        
        # Create initial display data - limit to 150 bars for performance
        display_df = full_data_df.copy()
        if len(display_df) > 150:
            display_df = display_df.tail(150)
            st.info(f"Showing last 150 out of {len(full_data_df)} bars")
        
        # Store display data in session state
        st.session_state['display_data'] = display_df
        
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
    
    # Initialize the indicator_type in session state if it doesn't exist
    if 'indicator_type' not in st.session_state:
        st.session_state['indicator_type'] = "sma"
    
    # Move this outside the form so it triggers a rerun when changed
    new_indicator = st.selectbox(
        "Indicator Type", 
        options=["sma", "ema", "rsi", "bollinger", "vwap", "macd"],
        key="indicator_type"
    )

    with st.form(key="indicator_form"):

        # Render parameters based on configuration
        params = render_indicator_params(st.session_state['indicator_type'])
        
        submitted_indicator = st.form_submit_button("Add Indicator")
        if submitted_indicator:
            st.session_state['indicators'].append({
                "type": st.session_state['indicator_type'],
                "params": params,
                "active": True
            })
            st.success(f"Added {st.session_state['indicator_type']} indicator.")

    st.write("Current Indicators:")
    if st.session_state['indicators']:
        for idx, ind in enumerate(st.session_state['indicators']):
            # Use columns for layout - indicator name and delete button
            col1, col2 = st.columns([4, 1])
            if ind['type'] == 'vwap':
                col1.write(f"{idx+1}. {ind['type'].upper()} with anchor {ind['params'].get('anchor')}")
            elif ind['type'] == 'macd':
                fast = ind['params'].get('fast')
                slow = ind['params'].get('slow')
                signal = ind['params'].get('signal')
                col1.write(f"{idx+1}. {ind['type'].upper()} with fast={fast}, slow={slow}, signal={signal}")
            else:
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
            
            # Limit to 150 data points for display only
            if len(display_updated) > 150:
                display_updated = display_updated.tail(150)
                
            st.session_state['display_data'] = display_updated
            
            # Separate indicators into overlay and separate indicators
            overlay_indicators = ['SMA', 'EMA', 'VWAP', 'BBL', 'BBM', 'BBU']
            oscillator_indicators = ['RSI', 'MACD']

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

            # Add price chart to first row
            fig = create_price_chart(fig, display_updated, row=1, col=1)
            
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
                
                # Skip oscillators - they'll be in their own rows
                if ind_type == 'rsi' or ind_type == 'macd':
                    continue
                # Skip Bollinger - already handled above
                if ind_type == 'bollinger':
                    continue
                
                # Add the indicator to the chart
                fig = add_indicator_to_chart(fig, display_updated, ind, row=1, col=1)
            
            # Add RSI in its own panel if it exists
            rsi_row = 2 if has_rsi else None  # Fixed row for RSI
            macd_row = 3 if has_rsi and has_macd else (2 if has_macd else None)  # Fixed row for MACD
            
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
                            row=rsi_row, col=1
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
                                row=rsi_row, col=1
                            )
                        
                        # Set y-axis range for RSI
                        fig.update_yaxes(range=[0, 100], row=rsi_row, col=1)
                
            # Add MACD in its own panel if it exists
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
                    
                    # Debug column names
                    st.write(f"Looking for MACD columns: {macd_col}, {signal_col}, {hist_col}")
                    st.write(f"Available columns: {[col for col in display_updated.columns if 'MACD' in col]}")
                    
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

# UI to add buy/sell conditions

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

    # Create the buy conditions section
    create_condition_section("buy", operand_options)
    
    # Create the sell conditions section
    create_condition_section("sell", operand_options)

# UI to run backtest
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

# At the very end of your app
# Replace your current footer with this
st.markdown("""
<div style="position: fixed; bottom: 2vh; left: 0; right: 0; display: flex; justify-content: center; align-items: center; padding: 10px 0; background: none;">
    <p style="font-size: 1rem; color: #ababab; margin: 0;">
        Made with ❤️ by&nbsp;&nbsp;
        <a href="https://github.com/KevinHancke" target="_blank">KevinHancke</a>
    </p>
</div>
""", unsafe_allow_html=True)