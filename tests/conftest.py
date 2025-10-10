import os
import pandas as pd
import pytest

FIX = os.path.join(os.path.dirname(__file__), "fixtures")

@pytest.fixture
def load_csv():
    def _load(name):
        return pd.read_csv(os.path.join(FIX, name), parse_dates=["Date"])
    return _load
