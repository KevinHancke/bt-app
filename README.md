# MoonTester - Cryptocurrency Trading Strategy Backtester

MoonTester is a web-based application for backtesting cryptocurrency trading strategies with customizable technical indicators and trading conditions.

![MoonTester Logo](frontend/assets/moon-logo.png)

## Features

- Interactive UI built with Streamlit
- Real-time technical analysis with various indicators:
  - Simple Moving Average (SMA)
  - Exponential Moving Average (EMA)
  - Relative Strength Index (RSI)
  - Bollinger Bands
  - Volume Weighted Average Price (VWAP)
  - Moving Average Convergence Divergence (MACD)
- Custom buy/sell condition creation based on indicators
- Comprehensive backtesting with configurable parameters:
  - Take profit percentage
  - Stop loss percentage 
  - Account size
  - Risk management
- Visualization of trade entries/exits and account growth
- Historical data analysis for different timeframes

## Project Structure

```
bt-app/
├── frontend/                # Streamlit frontend application
│   ├── app.py               # Main Streamlit application
│   └── assets/              # Static assets like images
│       └── moon-logo.png    # Application logo
├── backend/                 # FastAPI backend server
├── data/                    # Data storage (gitignored)
└── requirements.txt         # Python dependencies
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd bt-app
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Make sure you have the necessary data:
- Create a `data` directory if it doesn't exist and place your historical data there
- Note: CSV files are .gitignored

## Usage

1. Start the backend server:
```bash
cd backend
uvicorn main:app --reload
```

2. Start the frontend application:
```bash
cd frontend
streamlit run app.py
```

3. Open your browser and navigate to the URL displayed by Streamlit (usually http://localhost:8501)

## How to Use

1. **Select Data**: Choose a ticker and timeframe from the dropdown menus
2. **Load Data**: Click "Load Data" to retrieve historical price data
3. **Add Indicators**: Select indicators and configure their parameters
4. **Apply Indicators**: Click "Apply Indicators" to calculate and display indicators on the chart
5. **Create Trading Rules**: Set up buy and sell conditions using the dropdown menus
6. **Configure Backtest Parameters**: Set take profit, stop loss, account size, and risk amount
7. **Run Backtest**: Click "Run Backtest" to see performance metrics and trade visualizations

## Requirements

- Python 3.8+
- See requirements.txt for all Python dependencies

## License

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).

This means:
- You are free to share and adapt this software for non-commercial purposes
- You must give appropriate credit to the original author
- You may not use this software for commercial purposes
- For the full license text, see: https://creativecommons.org/licenses/by-nc/4.0/

## Acknowledgements

- [pandas_ta](https://github.com/twopirllc/pandas-ta) for technical analysis indicators
- [Streamlit](https://streamlit.io/) for the interactive web interface
- [Plotly](https://plotly.com/) for interactive charts
