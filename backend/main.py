from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np

from app.prepare_data import load_csv, resample_df, apply_buy_conditions, apply_sell_conditions, calculate_signals, shift_columns
from app.apply_indicators import ta_indicator
from app.custom_backtest import custom_backtest
from app.get_stats import get_stats, get_markers, get_performance_summary

from app.models import IndicatorRequest

app = FastAPI()

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware, 
    allow_origins=origins, 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

@app.get("/")
async def root():
    return {"message": "Backend Online check docs here: http://127.0.0.1:8000/docs"}

@app.get("/api/default_chart")
async def get_default_chart(timeframe: str = '1D', ticker: str = 'BTC/USD'):
    try:
        print(f'Getting initial chart data for {ticker} with timeframe {timeframe}...')
        # Map ticker to CSV file (updated to reflect actual CSV location)
        ticker_files = {
            'BTC/USD': 'data/Binance_BTCUSDT_1min.csv',
            'SOL/USD': 'data/Binance_SOLUSDT_1min.csv',
            'JUP/USD': 'data/Binance_JUPUSDT_1min.csv'
        }
        if ticker not in ticker_files:
            raise Exception(f'Ticker {ticker} not found.')

        df = load_csv(ticker_files[ticker])
        df = resample_df(df, timeframe)
        print('Data loaded and resampled successfully!')
        print(df.info())
        print(df)

        df['time'] = df.index.astype(str)
        
        return df.to_dict(orient='records')
    
    except Exception as e:
        print(f"Error loading default chart data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/api/apply_indicators")
async def apply_indicators(request: Request):
    try:
        data = await request.json()
        indicators = data.get('indicators', [])
        timeframe = data.get('timeframe', '1D')
        ticker = data.get('ticker', 'BTC/USD')
        print(f"Applying indicators: {indicators} for {ticker} on timeframe {timeframe}")

        # Map ticker to CSV file (updated to reflect actual CSV location)
        ticker_files = {
            'BTC/USD': 'data/Binance_BTCUSDT_1min.csv',
            'SOL/USD': 'data/Binance_SOLUSDT_1min.csv',
            'JUP/USD': 'data/Binance_JUPUSDT_1min.csv'
        }
        if ticker not in ticker_files:
            raise Exception(f'Ticker {ticker} not found.')

        df = load_csv(ticker_files[ticker])
        df = resample_df(df, timeframe)

        for indicator in indicators:
            # Apply indicators as before
            result = ta_indicator(df, indicator['type'], indicator.get('params', {}))
            if isinstance(result, pd.Series):
                df = df.join(result)
            elif isinstance(result, pd.DataFrame):
                df = pd.concat([df, result], axis=1)

        # Replace infinite values with NaN and fill NaN values
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.fillna(0, inplace=True)

        print('DataFrame columns after applying indicators:', df.columns.tolist())

        df.reset_index(inplace=True)
        df['time'] = df['time'].astype(str)
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"Error applying indicators: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/custom_backtest")
async def prepare_and_backtest(request: Request):
    try:
        data = await request.json()
        backtest_params = data.get('backtestParams', {})
        prepared_data = data.get('preparedDataframe', [])

        if not prepared_data:
            raise Exception('Prepared DataFrame is empty. Please prepare data before backtesting.')
        df = pd.DataFrame(prepared_data)

        print('Received backtest parameters:', backtest_params)
        print('Received prepared DataFrame with length:', len(prepared_data))

        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        print('start backtest...')

        df = shift_columns(df)

        # Apply all buy conditions using for loops
        df = apply_buy_conditions(df, backtest_params.get('buy_conditions', []))
        print('Buy conditions applied!')

        # Apply all sell conditions using for loops
        df = apply_sell_conditions(df, backtest_params.get('sell_conditions', []))
        print('Sell conditions applied!')

        print(df.info())
        print(df)

        # Calculate signals after applying all conditions
        df = calculate_signals(df)
        print('Dataframe prepared!')

        print(df)

        # Run the backtest
        trades = custom_backtest(df, backtest_params['tp'], backtest_params['sl'])

        markers = get_markers(trades)
        markers = markers.sort_values(by='time').reset_index(drop=True)
        print(markers.info())
        print(markers)

        stats = get_stats(trades, backtest_params['account_size'], backtest_params['risk_amt'], backtest_params['tp'], backtest_params['sl'])
        print(stats.info())
        print(stats)

        df['time'] = df.index.astype(str)  # Convert to string

        summary = get_performance_summary(trades)
        print(summary)

        # Replace infinite values with NaN and fill NaN values
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.fillna(0, inplace=True)

        result = {
            "dataframe": df.to_dict(orient='records'),
            "backtest_result": stats.to_dict(orient='records'),
            "markers": markers.to_dict(orient='records'),
            "summary": summary
        }

        print('Backtest completed!')
        return result

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))