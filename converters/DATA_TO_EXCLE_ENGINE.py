import pandas 
import json
from pandas.io.json import json_normalize
# SCRIPT FOR ORGANIZING DATA
# insert the right path
with open(r'3693(10_38_50)-CognataEngineLog.json (2).json') as f:
  json_data= json.load(f)
df=json_data['Logs']
df = json_normalize(df)
df1=pandas.DataFrame.from_dict(df, orient='columns')
df1=df1[df1.Type != 'Anchor']
df1=df1[df1.Type != 'ActionScript']
df1=df1[df1.Type != 'SemanticLabelingType']
df1=df1[df1.Type != 'SemanticLabelingInstance']
# insert the path where you want to store your csv file
df1.to_csv('LOAD1_TTC1.csv')

