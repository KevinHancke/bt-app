from pydantic import BaseModel
from typing import List, Union, Dict, Any, Optional

class Operand(BaseModel):
    column: str
    shift: Optional[int] = 0  # Shift is optional, default to 0 if not provided

class Condition(BaseModel):
    left_operand: Operand
    comparator: str
    right_operand: Operand

class Backtest(BaseModel):
    account_size: float
    risk_amt: float
    buy_conditions: List[Condition]
    sell_conditions: List[Condition]
    freq: str
    tp: float
    sl: float

class Indicator(BaseModel):
    type: str
    params: Dict[str, Any]

class IndicatorRequest(BaseModel):
    indicators: List[Indicator]