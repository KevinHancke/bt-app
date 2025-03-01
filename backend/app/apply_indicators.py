import pandas as pd
import pandas_ta as ta
from typing import Union
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ta_indicator(df: pd.DataFrame, indicator_name: str, params: dict) -> Union[pd.Series, pd.DataFrame]:
    """
    Applies a technical indicator to the DataFrame.

    Args:
        df (pd.DataFrame): The input DataFrame with price data.
        indicator_name (str): The name of the indicator to apply.
        params (dict): A dictionary of parameters for the indicator.

    Returns:
        Union[pd.Series, pd.DataFrame]: The calculated indicator values.
    """
    logger.info(f"Applying indicator: {indicator_name} with params: {params}")

    if indicator_name == 'sma':
        if 'length' not in params:
            raise ValueError("Missing 'length' parameter for SMA.")
        length = int(params['length'])
        if length <= 0:
            raise ValueError("'length' must be a positive integer.")
        result = ta.sma(df['close'], length=length)
        logger.info(f"SMA({length}) calculated.")
        return result.to_frame(name=f'SMA_{length}')

    elif indicator_name == 'ema':
        if 'length' not in params:
            raise ValueError("Missing 'length' parameter for EMA.")
        length = int(params['length'])
        if length <= 0:
            raise ValueError("'length' must be a positive integer.")
        result = ta.ema(df['close'], length=length)
        logger.info(f"EMA({length}) calculated.")
        return result.to_frame(name=f'EMA_{length}')

    elif indicator_name == 'rsi':
        if 'length' not in params:
            raise ValueError("Missing 'length' parameter for RSI.")
        length = int(params['length'])
        if length <= 0:
            raise ValueError("'length' must be a positive integer.")
        result = ta.rsi(df['close'], length=length)
        result_name = f'RSI_{length}'
        logger.info(f"RSI column: {result_name}")
        return result.to_frame(name=result_name)

    elif indicator_name == 'vwap':
        anchor = params.get("anchor", 'start')
        result = ta.vwap(df['high'], df['low'], df['close'], df['volume'], anchor=anchor)
        logger.info(f"VWAP({anchor}) calculated.")
        return result.to_frame(name=f'VWAP_{anchor}')

    elif indicator_name == 'bollinger':
        if 'length' not in params:
            raise ValueError("Missing 'length' parameter for Bollinger Bands.")
        length = int(params['length'])
        if length <= 0:
            raise ValueError("'length' must be a positive integer.")
        std_dev = float(params.get("std_dev", 2))
        result = ta.bbands(df['close'], length=length, std=std_dev)
        # Rename columns to make them identifiable
        result.columns = [f'BBL_{length}', f'BBM_{length}', f'BBU_{length}', f'BBB_{length}', f'BBP_{length}']
        logger.info(f"Bollinger Bands columns: {', '.join(result.columns)}")
        return result

    elif indicator_name == 'macd':
        fast = int(params.get("fast", 12))
        slow = int(params.get("slow", 26))
        signal = int(params.get("signal", 9))
        result = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
        logger.info(f"MACD (Fast: {fast}, Slow: {slow}, Signal: {signal}) calculated.")
        return result

    else:
        raise ValueError(f"Unknown indicator: {indicator_name}")