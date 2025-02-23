import pandas as pd
import numpy as np

def get_stats(trades: pd.DataFrame, initial_account_size: float, risk_amt: float, tp: float, sl: float) -> pd.DataFrame:
    risk_reward = tp/sl

    # Initialize account size for quote and base currency
    account_size_quote = initial_account_size
    account_size_base = initial_account_size / trades['entry_price'].iloc[0]

    buy_and_hold_amount = initial_account_size / trades['entry_price'].iloc[0]
    trades['buyhold'] = buy_and_hold_amount * trades['exit_price']

    # Iterate through each trade
    for i in range(len(trades)):
        #--------------------------------------------------
        # 1) QUOTE SCENARIO: For a losing trade, reduce
        #    account by 'risk_amt %' of current balance.
        #--------------------------------------------------
        max_loss_quote = account_size_quote * (risk_amt / 100)
        if trades.loc[i, 'perc_chg'] < 0:
            # Lose exactly risk portion
            account_size_quote -= max_loss_quote
            trades.loc[i, 'result'] = 'loss'
            trades.loc[i, 'pnl'] = -max_loss_quote
        else:
            # Example: Win the same fraction, multiplied by risk_reward
            # Adjust as you prefer
            profit_quote = max_loss_quote * risk_reward
            account_size_quote += profit_quote
            trades.loc[i, 'result'] = 'win'
            trades.loc[i, 'pnl'] = profit_quote

        trades.loc[i, 'account_size_quote'] = account_size_quote

        #--------------------------------------------------
        # 2) BASE SCENARIO: Parallel logic to track base
        #--------------------------------------------------
        max_loss_base = account_size_base * (risk_amt / 100)
        if trades.loc[i, 'perc_chg'] < 0:
            account_size_base -= max_loss_base
            trades.loc[i, 'result_base'] = 'loss'
            trades.loc[i, 'pnl_base'] = -max_loss_base
        else:
            profit_base = max_loss_base * risk_reward
            account_size_base += profit_base
            trades.loc[i, 'result_base'] = 'win'
            trades.loc[i, 'pnl_base'] = profit_base

        trades.loc[i, 'account_size_base'] = account_size_base

    trades['account_size_base_value'] = trades['account_size_base'] * trades['exit_price']

    print(trades[['account_size_quote', 'buyhold', 'account_size_base', 'account_size_base_value', 'pnl']])
        
    return trades

def get_performance_summary(trades: pd.DataFrame) -> pd.DataFrame:
    # Initialize variables
    total_trades = len(trades)
    total_wins = len(trades[trades['perc_chg'] > 0])
    total_losses = len(trades[trades['perc_chg'] < 0])
    win_rate = total_wins / total_trades
    loss_rate = total_losses / total_trades
    long_win_rate = len(trades[(trades['perc_chg'] > 0) & (trades['side'] == 'long')]) / len(trades[trades['side'] == 'long'])
    short_win_rate = len(trades[(trades['perc_chg'] > 0) & (trades['side'] == 'short')]) / len(trades[trades['side'] == 'short'])

    for i in range(len(trades)):
        trades.loc[i, 'trade_duration'] = trades.loc[i, 'exit_time'] - trades.loc[i, 'entry_time']
        trades.loc[i, 'trade_duration'] = trades.loc[i, 'trade_duration'].total_seconds() / 60  # Convert to minutes
    
    avg_trade_duration = trades['trade_duration'].mean()
    total_duration = trades['trade_duration'].sum()

    # Calculate the total profit and loss
    total_profit = trades['perc_chg'].sum()
    long_profit = trades[trades['side'] == 'long']['perc_chg'].sum()
    short_profit = trades[trades['side'] == 'short']['perc_chg'].sum()
    max_drawdown = trades['account_size_quote'].min() - trades['account_size_quote'].iloc[0]
    max_drawdown_pct = max_drawdown / trades['account_size_quote'].iloc[0]
    
    initial_account_size = trades['account_size_quote'].iloc[0]
    min_account_size = trades['account_size_quote'].min()
    max_account_size = trades['account_size_quote'].max()
    final_account_size = trades['account_size_quote'].iloc[-1]

    

    result = {
        'total_trades': total_trades,
        'total_wins': total_wins,
        'total_losses': total_losses,
        'win_rate': win_rate,
        'loss_rate': loss_rate,
        'long_win_rate': long_win_rate,
        'short_win_rate': short_win_rate,
        'avg_trade_duration': avg_trade_duration,
        'total_profit': total_profit,
        'long_profit': long_profit,
        'short_profit': short_profit,
        'total_duration': total_duration,
        'max_drawdown': max_drawdown,
        'max_drawdown_pct': max_drawdown_pct,
        'initial_account_size': initial_account_size,
        'min_account_size': min_account_size,
        'max_account_size': max_account_size,
        'final_account_size': final_account_size
    }
    
    return result

def get_markers(trades: pd.DataFrame) -> pd.DataFrame:
    trades_markers = pd.DataFrame(columns=['time', 'price', 'side', 'type', 'result', 'position', 'color', 'shape', 'text'])

    for i in range(len(trades)):
        # Update result: win -> 'w', loss -> 'l'
        result = 'w' if trades.loc[i, 'perc_chg'] > 0 else 'l'

        entry_marker = pd.DataFrame([{
            'time': trades.loc[i, 'entry_time'],
            'price': trades.loc[i, 'entry_price'],
            'side': trades.loc[i, 'side'],
            'type': 'entry',
            'result': result,
            'position': 'belowBar' if trades.loc[i, 'side'] == 'long' else 'aboveBar',
            'color': 'green' if trades.loc[i, 'side'] == 'long' else 'red',
            'shape': 'arrowUp' if trades.loc[i, 'side'] == 'long' else 'arrowDown',
            # For entry, use 'b' for long, 's' for short
            'text': 'b' if trades.loc[i, 'side'] == 'long' else 's'
        }])

        # Determine exit marker position based on result and side
        position = 'none'
        if trades.loc[i, 'side'] == 'long':
            position = 'aboveBar' if result == 'w' else 'belowBar'
        else:
            position = 'belowBar' if result == 'w' else 'aboveBar'

        exit_marker = pd.DataFrame([{
            'time': trades.loc[i, 'exit_time'],
            'price': trades.loc[i, 'exit_price'],
            'side': trades.loc[i, 'side'],
            'type': 'exit',
            'result': result,
            'position': position,
            'color': 'green' if trades.loc[i, 'side'] == 'long' else 'red',
            'shape': 'circle',
            # For exit, use 'w' if positive change, else 'l'
            'text': 'w' if trades.loc[i, 'perc_chg'] > 0 else 'l'
        }])

        trades_markers = pd.concat([trades_markers, entry_marker, exit_marker], ignore_index=True)

    return trades_markers