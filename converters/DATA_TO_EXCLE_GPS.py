import pandas
import json
from pandas.io.json import json_normalize
# SCRIPT FOR ORGANIZING DATA
# insert the right path
with open(r'3796(18_23_52)-VehicleGPSLog (6).json') as f:
  json_data= json.load(f)
df=json_data['Logs']
df = json_normalize(df)
df1=pandas.DataFrame.from_dict(df, orient='columns')
# insert the path where you want to store your csv file
df1.to_csv('LOAD3_TTC2.csv')
