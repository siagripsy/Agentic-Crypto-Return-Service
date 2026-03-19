"""
Initialize database with sample coins data
"""
import pandas as pd
from sqlalchemy import text
from core.storage.database import get_engine

# Sample coins data
COINS_DATA = [
    {"CoinID": 1, "symbol": "BTC", "coingecko_id": "bitcoin", "yahoo_ticker": "BTC-USD", "start_year": 2015},
    {"CoinID": 2, "symbol": "ETH", "coingecko_id": "ethereum", "yahoo_ticker": "ETH-USD", "start_year": 2015},
    {"CoinID": 3, "symbol": "ADA", "coingecko_id": "cardano", "yahoo_ticker": "ADA-USD", "start_year": 2017},
    {"CoinID": 4, "symbol": "SOL", "coingecko_id": "solana", "yahoo_ticker": "SOL-USD", "start_year": 2020},
    {"CoinID": 5, "symbol": "XRP", "coingecko_id": "ripple", "yahoo_ticker": "XRP-USD", "start_year": 2013},
    {"CoinID": 6, "symbol": "BNB", "coingecko_id": "binancecoin", "yahoo_ticker": "BNB-USD", "start_year": 2017},
    {"CoinID": 7, "symbol": "DOGE", "coingecko_id": "dogecoin", "yahoo_ticker": "DOGE-USD", "start_year": 2013},
    {"CoinID": 8, "symbol": "LINK", "coingecko_id": "chainlink", "yahoo_ticker": "LINK-USD", "start_year": 2017},
    {"CoinID": 9, "symbol": "AVAX", "coingecko_id": "avalanche-2", "yahoo_ticker": "AVAX-USD", "start_year": 2020},
    {"CoinID": 10, "symbol": "FLOKI", "coingecko_id": "floki", "yahoo_ticker": "FLOKI-USD", "start_year": 2021},
]

def init_coins():
    engine = get_engine()
    df = pd.DataFrame(COINS_DATA)
    
    # Create table if not exists and insert data
    with engine.begin() as conn:
        # Drop existing table for fresh start
        conn.execute(text("""
            IF OBJECT_ID('Coins', 'U') IS NOT NULL 
            DROP TABLE Coins
        """))
        
        # Create new table
        conn.execute(text("""
            CREATE TABLE Coins (
                CoinID INT PRIMARY KEY,
                symbol NVARCHAR(50) NOT NULL UNIQUE,
                coingecko_id NVARCHAR(100) NOT NULL,
                yahoo_ticker NVARCHAR(50) NOT NULL,
                start_year INT
            )
        """))
    
    # Insert data
    df.to_sql('Coins', con=engine, if_exists='append', index=False)
    print(f"✅ Database initialized with {len(df)} coins")

if __name__ == "__main__":
    init_coins()
