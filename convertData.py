import pandas
import json
import pandas as pd
import os
import json
from pandas.io.json import json_normalize

id = 'A5_292076'
print("Making Folders")
try:
    os.mkdir(id)
except OSError as error:
     print(error)

try:
     os.mkdir(f'{id}/Figures')
     os.mkdir(f'{id}/Simulator')
     os.mkdir(f'{id}/Physiological')
except OSError as error:
     print(error)

# ########### SIMULATOR ##############
print("Making Simulator files (Engine files)")
path = f'convert/ACC'
scenarios = os.listdir(path)

for x in scenarios:
   path = f'convert/ACC/{x}'
   file = os.listdir(path)
   # SCRIPT FOR ORGANIZING DATA
   # insert the right path
   right_file = ""
   for y in file:
     if y.__contains__("Engine"):
       right_file = y

   with open(f'convert/ACC/{x}/{right_file}') as f:
     json_data = json.load(f)
   df = json_data['Logs']
   df = json_normalize(df)
   df1 = pandas.DataFrame.from_dict(df, orient='columns')
   df1 = df1[df1.Type != 'Anchor']
   df1 = df1[df1.Type != 'ActionScript']
   df1 = df1[df1.Type != 'SemanticLabelingType']
   df1 = df1[df1.Type != 'SemanticLabelingInstance']
   # insert the path where you want to store your csv file
   df1.to_csv(f'{id}/Simulator/{x}.csv')

############# Phy #####################
path = f'convert/Phy'
phy_scenarios = os.listdir(path)
print("Making Physiological files (Amp)")
for x in phy_scenarios:
  path = f'convert/Phy/{x}'
  file = os.listdir(path)
  right_file = ""
  for y in file:
    if y.__contains__("Amp"):
      right_file = y
  # insert the right path
  df = pd.DataFrame(pd.read_excel(f'convert/Phy/{x}/{right_file}'))
  # insert the path where you want to store your csv file
  string = right_file
  string = string[28:40]
  string = string.replace(' ','')
  string = string[:5] + '_' + string[5:]
  df.to_csv(f'{id}/Physiological/{string}.csv')

print("Making Figures Folders")
for x in scenarios:
  try:
    os.mkdir(f'{id}/Figures/{x}')
  except OSError as error:
    print(error)

print("Done.")