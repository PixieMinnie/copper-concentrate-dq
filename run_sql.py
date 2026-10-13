import sys
import pandas as pd
from sqlalchemy import create_engine, text
from db import get_engine

engine = get_engine()
query = open(sys.argv[1]).read()
df = pd.read_sql(text(query), engine)
print(df.to_string(index=False))