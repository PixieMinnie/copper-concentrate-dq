import pandas as pd
from sqlalchemy import text

from db import get_engine

engine = get_engine()
df = pd.read_sql(text("SELECT reporter_name, net_wgt_kg FROM trade_flows"), engine)
cv = df.groupby("reporter_name")["net_wgt_kg"].agg(lambda s: s.std() / s.mean())
print(cv.round(2))