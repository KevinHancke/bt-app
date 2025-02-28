import pandas as pd
import numpy as np

def calculate_trade_pnl(trade_type, account_size, risk_amt, risk_reward, is_win):
    """
    Calculate PnL for a specific trade
    
    Args:
        trade_type: 'quote' or 'base' to indicate currency type
        account_size: Current account size
        risk_amt: Risk percentage for trade
        risk_reward: Risk-reward ratio (tp/sl)
        is_win: Boolean indicating if trade is a win
    
    Returns:
        tuple: (pnl_amount, new_account_size, result_label)
    """
    max_loss = account_size * (risk_amt / 100)
    
    if is_win:
        profit = max_loss * risk_reward
        return profit, account_size + profit, 'win'
    else:
        return -max_loss, account_size - max_loss, 'loss'

def get_stats(trades: pd.DataFrame, initial_account_size: float, risk_amt: float, tp: float, sl: float) -> pd.DataFrame:
    """Calculate performance statistics for a set of trades"""
    risk_reward = tp/sl

    # Initialize account sizes
    account_size_quote = initial_account_size
    account_size_base = initial_account_size / trades['entry_price'].iloc[0]

    # Calculate buy and hold performance
    buy_and_hold_amount = initial_account_size / trades['entry_price'].iloc[0]
    trades['buyhold'] = buy_and_hold_amount * trades['exit_price']

    # Vectorize some calculations where possible
    is_win = trades['perc_chg'] > 0

    # Iterate through each trade (we still need a loop for accumulated values)
    for i in range(len(trades)):
        # Quote currency calculations
        pnl_quote, account_size_quote, result = calculate_trade_pnl(
            'quote', account_size_quote, risk_amt, risk_reward, is_win.iloc[i]
        )
        trades.loc[i, 'result'] = result
        trades.loc[i, 'pnl'] = pnl_quote
        trades.loc[i, 'account_size_quote'] = account_size_quote
        
        # Base currency calculations
        pnl_base, account_size_base, result_base = calculate_trade_pnl(
            'base', account_size_base, risk_amt, risk_reward, is_win.iloc[i]
        )
        trades.loc[i, 'result_base'] = result_base
        trades.loc[i, 'pnl_base'] = pnl_base
        trades.loc[i, 'account_size_base'] = account_size_base

    # Calculate base currency value in quote terms
    trades['account_size_base_value'] = trades['account_size_base'] * trades['exit_price']
    
    return trades

def calculate_duration_metrics(trades: pd.DataFrame):
    """Calculate trade duration metrics"""
    for i in range(len(trades)):
        trades.loc[i, 'trade_duration'] = (
            trades.loc[i, 'exit_time'] - trades.loc[i, 'entry_time']
        ).total_seconds() / 60  # Convert to minutes
    
    return {
        'avg_trade_duration': trades['trade_duration'].mean(),
        'total_duration': trades['trade_duration'].sum()
    }

def calculate_win_loss_metrics(trades: pd.DataFrame):
    """Calculate win/loss related metrics"""
    total_trades = len(trades)
    if total_trades == 0:
        return {
            'total_trades': 0,
            'win_rate': 0,
            'loss_rate': 0,
            'long_win_rate': 0,
            'short_win_rate': 0
        }
        
    total_wins = len(trades[trades['perc_chg'] > 0])
    total_losses = len(trades[trades['perc_chg'] < 0])
    
    # Handle potential division by zero
    long_trades = len(trades[trades['side'] == 'long'])
    short_trades = len(trades[trades['side'] == 'short'])
    
    long_win_rate = len(trades[(trades['perc_chg'] > 0) & (trades['side'] == 'long')]) / long_trades if long_trades > 0 else 0
    short_win_rate = len(trades[(trades['perc_chg'] > 0) & (trades['side'] == 'short')]) / short_trades if short_trades > 0 else 0
    
    return {
        'total_trades': total_trades,
        'total_wins': total_wins,
        'total_losses': total_losses,
        'win_rate': total_wins / total_trades,
        'loss_rate': total_losses / total_trades,
        'long_win_rate': long_win_rate,
        'short_win_rate': short_win_rate
    }

def get_performance_summary(trades: pd.DataFrame) -> dict:
    """Calculate comprehensive performance summary statistics"""
    if len(trades) == 0:
        return {
            'total_trades': 0,
            'total_profit': 0,
            'win_rate': 0
        }
        
    # Calculate win/loss metrics
    win_loss_metrics = calculate_win_loss_metrics(trades)
    
    # Calculate duration metrics
    duration_metrics = calculate_duration_metrics(trades)
    
    # Calculate profit metrics
    profit_metrics = {
        'total_profit': trades['perc_chg'].sum(),
        'long_profit': trades[trades['side'] == 'long']['perc_chg'].sum(),
        'short_profit': trades[trades['side'] == 'short']['perc_chg'].sum(),
    }
    
    # Calculate account metrics
    if 'account_size_quote' in trades.columns and len(trades) > 0:
        initial_account = trades['account_size_quote'].iloc[0]
        max_drawdown = trades['account_size_quote'].min() - initial_account
        account_metrics = {
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown / initial_account if initial_account != 0 else 0,
            'initial_account_size': initial_account,
            'min_account_size': trades['account_size_quote'].min(),
            'max_account_size': trades['account_size_quote'].max(),
            'final_account_size': trades['account_size_quote'].iloc[-1]
        }
    else:
        account_metrics = {}
    
    # Combine all metrics
    result = {**win_loss_metrics, **duration_metrics, **profit_metrics, **account_metrics}
    return result

def get_markers(trades: pd.DataFrame) -> pd.DataFrame:
    """Generate chart markers for entry and exit points"""
    if trades.empty:
        return pd.DataFrame(columns=[
            'time', 'price', 'side', 'type', 'result', 
            'position', 'color', 'shape', 'text'
        ])
    
    # Pre-allocate the DataFrame for better performance
    n_trades = len(trades)
    markers = pd.DataFrame(index=range(2*n_trades), columns=[
        'time', 'price', 'side', 'type', 'result', 
        'position', 'color', 'shape', 'text'
    ])
    
    for i in range(n_trades):
        # Determine if win or loss
        result = 'w' if trades.iloc[i]['perc_chg'] > 0 else 'l'
        side = trades.iloc[i]['side']
        
        # Entry marker
        markers.iloc[2*i] = {
            'time': trades.iloc[i]['entry_time'],
            'price': trades.iloc[i]['entry_price'],
            'side': side,
            'type': 'entry',
            'result': result,
            'position': 'belowBar' if side == 'long' else 'aboveBar',
            'color': 'green' if side == 'long' else 'red',
            'shape': 'arrowUp' if side == 'long' else 'arrowDown',
            'text': 'b' if side == 'long' else 's'
        }
        
        # Determine exit marker position based on result and side
        position = 'aboveBar' if (side == 'long' and result == 'w') or (side == 'short' and result == 'l') else 'belowBar'
        
        # Exit marker
        markers.iloc[2*i+1] = {
            'time': trades.iloc[i]['exit_time'],
            'price': trades.iloc[i]['exit_price'],
            'side': side,
            'type': 'exit',
            'result': result,
            'position': position,
            'color': 'green' if side == 'long' else 'red',
            'shape': 'circle',
            'text': result
        }
    
    return markers