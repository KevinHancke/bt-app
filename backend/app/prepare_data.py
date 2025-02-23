import pandas as pd
import operator
import numpy as np

def load_csv(filepath: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(filepath)
        df = df.iloc[:, :6]
        df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']
        df.reset_index(drop=True, inplace=True)
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        return df
    except ValueError as ve:
        raise ValueError(f"Error loading CSV file: {ve}")
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found at path: {filepath}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred while loading CSV: {e}")

def resample_df(df: pd.DataFrame, freq: str) -> pd.DataFrame:   
    try:
        resampled_open = df.open.resample(freq).first()
        resampled_high = df.high.resample(freq).max()
        resampled_low = df.low.resample(freq).min()
        resampled_close = df.close.resample(freq).last()
        resampled_volume = df.volume.resample(freq).sum()
        df = pd.concat([resampled_open, resampled_high, resampled_low, resampled_close, resampled_volume], axis=1)
        df.dropna(inplace=True)
        return df
    except Exception as e:
        raise Exception(f"Error resampling DataFrame: {e}")

def shift_columns(df: pd.DataFrame) -> pd.DataFrame:
    df['entry_price'] = df['open'].shift(-1)
    return df

def get_shifted_series(df: pd.DataFrame, operand: dict) -> pd.Series:
    column = operand.get('column')
    shift = operand.get('shift', 0)
    if column in df.columns:
        return df[column].shift(shift)
    else:
        raise ValueError(f"Column '{column}' does not exist in DataFrame.")

def apply_buy_conditions(df: pd.DataFrame, conditions: list) -> pd.DataFrame:
    if 'buy_conditions' not in df.columns:
        df['buy_conditions'] = True  # Initialize as True for logical AND

    print("Applying buy conditions with for loop")

    operators = {
        '>': operator.gt,
        '<': operator.lt,
        '==': operator.eq,
        '!=': operator.ne,
        '>=': operator.ge,
        '<=': operator.le
    }

    for condition in conditions:
        left_operand = condition['left_operand']
        comparator = condition['comparator']
        right_operand = condition['right_operand']

        print(f"Evaluating buy condition: {left_operand} {comparator} {right_operand}")

        if comparator in operators:
            left_series = get_shifted_series(df, left_operand)
            right_series = get_shifted_series(df, right_operand)
            condition_result = operators[comparator](left_series, right_series)
            condition_result = condition_result.fillna(False)  # Handle NaN values
            df['buy_conditions'] &= condition_result
            print(f"Buy conditions after applying condition: {df['buy_conditions'].value_counts().to_dict()}")
        else:
            raise ValueError(f"Invalid comparator: {comparator}")

    return df

def apply_sell_conditions(df: pd.DataFrame, conditions: list) -> pd.DataFrame:
    if 'sell_conditions' not in df.columns:
        df['sell_conditions'] = True  # Initialize as True for logical AND

    print("Applying sell conditions with for loop")

    operators = {
        '>': operator.gt,
        '<': operator.lt,
        '==': operator.eq,
        '!=': operator.ne,
        '>=': operator.ge,
        '<=': operator.le
    }

    for condition in conditions:
        left_operand = condition['left_operand']
        comparator = condition['comparator']
        right_operand = condition['right_operand']

        print(f"Evaluating sell condition: {left_operand} {comparator} {right_operand}")

        if comparator in operators:
            left_series = get_shifted_series(df, left_operand)
            right_series = get_shifted_series(df, right_operand)
            condition_result = operators[comparator](left_series, right_series)
            condition_result = condition_result.fillna(False)  # Handle NaN values
            df['sell_conditions'] &= condition_result
            print(f"Sell conditions after applying condition: {df['sell_conditions'].value_counts().to_dict()}")
        else:
            raise ValueError(f"Invalid comparator: {comparator}")

    return df

def calculate_signals(df: pd.DataFrame) -> pd.DataFrame:
    print('Attempting to calculate signals')
    df['buy_signal'] = np.where((df['buy_conditions']) & (df['buy_conditions'].shift(1)), 1, 0)
    df['sell_signal'] = np.where((df['sell_conditions']) & (df['sell_conditions'].shift(1)), 1, 0)
    print(f"Buy signals after applying calc_suignal: {df['buy_signal'].value_counts().to_dict()}")
    print(f"Sell signals after applying calc_signal: {df['sell_signal'].value_counts().to_dict()}")
    return df