import pandas as pd

def custom_backtest(new_df: pd.DataFrame, tp: float, sl: float):
    # Error handle for no buy or sell signals
    if len(new_df[new_df.buy_signal > 0]) == 0 and len(new_df[new_df.sell_signal > 0]) == 0:
        empty_result = pd.DataFrame({
            "entry_time": [0],
            "entry_price": [0],
            "tp_target": [0],
            "sl_target": [0],
            "exit_time": [0],
            "exit_price": [0],
            "pnl": [0],
            "equity": [0],
            "pnl_perc": [0]
        })
        return empty_result

    # Initialize Variables
    in_sell_position = False
    in_buy_position = False
    buy_trades = []
    current_buy_trade = {}
    sell_trades = []
    current_sell_trade = {}

    for i in range(len(new_df) - 1):
        # Check exit conditions for buy position
        if in_buy_position:
            if new_df.iloc[i].low < current_buy_trade["sl_price"]:
                current_buy_trade["exit_price"] = current_buy_trade["sl_price"]
                percentage_change = -1 * sl/100
                buy_trades.append({
                    "entry_time": current_buy_trade["entry_time"],
                    "entry_price": current_buy_trade["entry_price"],
                    "side": current_buy_trade["side"],
                    "tp_target": current_buy_trade["tp_price"],
                    "sl_target": current_buy_trade["sl_price"],
                    "sl_distance": current_buy_trade["sl_distance"],
                    "exit_time": new_df.iloc[i].name,
                    "exit_price": current_buy_trade["sl_price"],
                    "perc_chg": percentage_change,
                })
                current_buy_trade = {}
                in_buy_position = False

            elif new_df.iloc[i].high > current_buy_trade["tp_price"]:
                current_buy_trade["exit_price"] = current_buy_trade["tp_price"]
                percentage_change = tp/100
                buy_trades.append({
                    "entry_time": current_buy_trade["entry_time"],
                    "entry_price": current_buy_trade["entry_price"],
                    "side": current_buy_trade["side"],
                    "tp_target": current_buy_trade["tp_price"],
                    "sl_target": current_buy_trade["sl_price"],
                    "sl_distance": current_buy_trade["sl_distance"],
                    "exit_time": new_df.iloc[i].name,
                    "exit_price": current_buy_trade["tp_price"],
                    "perc_chg": percentage_change,
                })
                current_buy_trade = {}
                in_buy_position = False

        # Check exit conditions for sell position
        if in_sell_position:
            if new_df.iloc[i].high > current_sell_trade["sl_price"]:
                current_sell_trade["exit_price"] = current_sell_trade["sl_price"]
                percentage_change = -1 * sl/100
                sell_trades.append({
                    "entry_time": current_sell_trade["entry_time"],
                    "entry_price": current_sell_trade["entry_price"],
                    "side": current_sell_trade["side"],
                    "tp_target": current_sell_trade["tp_price"],
                    "sl_target": current_sell_trade["sl_price"],
                    "sl_distance": current_sell_trade["sl_distance"],
                    "exit_time": new_df.iloc[i].name,
                    "exit_price": current_sell_trade["sl_price"],
                    "perc_chg": percentage_change,
                })
                current_sell_trade = {}
                in_sell_position = False

            elif new_df.iloc[i].low < current_sell_trade["tp_price"]:
                current_sell_trade["exit_price"] = current_sell_trade["tp_price"]
                percentage_change = tp/100
                sell_trades.append({
                    "entry_time": current_sell_trade["entry_time"],
                    "entry_price": current_sell_trade["entry_price"],
                    "side": current_sell_trade["side"],
                    "tp_target": current_sell_trade["tp_price"],
                    "sl_target": current_sell_trade["sl_price"],
                    "sl_distance": current_sell_trade["sl_distance"],
                    "exit_time": new_df.iloc[i].name,
                    "exit_price": current_sell_trade["tp_price"],
                    "perc_chg": percentage_change,
                })
                current_sell_trade = {}
                in_sell_position = False

        # Check entry conditions for buy position
        if not in_buy_position:
            if new_df.iloc[i].buy_signal:
                current_buy_trade["entry_price"] = new_df.iloc[i].entry_price
                current_buy_trade["entry_time"] = new_df.iloc[i + 1].name
                current_buy_trade["side"] = "long"
                current_buy_trade["tp_price"] = new_df.iloc[i].entry_price * (1 + tp/100)
                current_buy_trade["sl_price"] = new_df.iloc[i].entry_price * (1 - sl/100)
                current_buy_trade["sl_distance"] = current_buy_trade["entry_price"] - current_buy_trade["sl_price"]
                in_buy_position = True

        # Check entry conditions for sell position
        if not in_sell_position:
            if new_df.iloc[i].sell_signal:
                current_sell_trade["entry_price"] = new_df.iloc[i].entry_price
                current_sell_trade["entry_time"] = new_df.iloc[i + 1].name
                current_sell_trade["side"] = "short"
                current_sell_trade["tp_price"] = new_df.iloc[i].entry_price * (1 - tp/100)
                current_sell_trade["sl_price"] = new_df.iloc[i].entry_price * (1 + sl/100)
                current_sell_trade["sl_distance"] = current_sell_trade["sl_price"] - current_sell_trade["entry_price"]
                in_sell_position = True

    # Prepare all trades DataFrame for future calculations
    all_trades = buy_trades + sell_trades
    df_all_trades = pd.DataFrame(all_trades)
    df_all_trades = df_all_trades.sort_values(by='entry_time').reset_index(drop=True)


    return df_all_trades