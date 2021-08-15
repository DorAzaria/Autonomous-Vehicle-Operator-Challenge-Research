import os
import pandas as pd
import neurokit2 as nk
from os import path
import haversine as hs
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
import warnings
warnings.filterwarnings('ignore')
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

def getGSR(name, id,flag):  # load xlsx to gsr df, flag=0 with zero, removes final clock duplication

    df12 = pd.read_csv(os.getcwd() +('/%s/Physiological/%s.csv' % (id, name)))
    df12 = df12.rename(columns={'simulation time': 'SimulationTime'})
    df12 = df12.rename(columns={'measurement time': 'measurementTime'})

    #   removes final clock duplication
    dfLastIndex = df12.index[-1]
    endTime = df12.SimulationTime[dfLastIndex]
    for i in df12.index:
        if df12.SimulationTime[i] == endTime:
            myLastIndex = i+11
            break
    newGsr = df12.iloc[0:myLastIndex]

    # filter time and gsr
    if flag == 1:
        newGsr = newGsr[newGsr.SimulationTime != 0].reset_index(drop=True)

    newGsr = newGsr.filter(items=['SimulationTime', 'GSR', 'measurementTime'])
    return newGsr

def getLeadCar(name, id):  # load json to gsp df
    df = pd.read_csv(os.getcwd() +('/%s/Simulator/%s.csv' % (id, name)))

    df = (pd.DataFrame(df['Logs'].values.tolist()).join(df.drop('Logs', 1)))
    df = pd.DataFrame.from_dict(df, orient='columns')
    df3 = df[df.Name == 'lead car'].reset_index()
    df3 = df3.filter(items=['SimulationTime', 'Latitude', 'Longitude'])  # 'Speed', 'PositionInLane', 'LaneNumber'])
    df3 = df3.rename(columns={'Latitude': 'Latitude_lead'})
    df3 = df3.rename(columns={'Longitude': 'Longitude_lead'})
    return df3


def getGPS(name, id):  # load json to gsp df
    df = pd.read_csv(os.getcwd() +('/%s/Simulator/%s.csv' % (id, name)))
    df = pd.DataFrame.from_dict(df, orient='columns')
    # filter GPS
    ego1 = df[df.Type == 'GPS'].reset_index()
    ego1["RealTime"] = " "
    for x in ego1.index:
        currentTime = ego1.WorldTime[x]
        currentTime2 = currentTime[0:15]
        currentTime3 = datetime.strptime(currentTime2, "%H:%M:%S.%f")

        fixedTime = ego1.WorldTime[0]
        fixedTime2 = fixedTime[0:15]
        fixedTime3 = datetime.strptime(fixedTime2, "%H:%M:%S.%f")

        delta = currentTime3 - fixedTime3
        deltasec = delta.total_seconds()
        ego1.RealTime[x] = deltasec
    ego1 = ego1.filter(
        items=['RealTime', 'SimulationTime', 'Latitude', 'Longitude', 'Speed', 'PositionInLane', 'LaneNumber'])

    try:
        mergeEgoAndLead = pd.merge(ego1, getLeadCar(name, id), how='inner', on='SimulationTime')
        mergeEgoAndLead.insert(8, 'DistanceToLeadCar', " ", allow_duplicates=True)
        for i in range(len(mergeEgoAndLead)):
            loc1 = (mergeEgoAndLead.Latitude[i], mergeEgoAndLead.Longitude[i])
            loc2 = (mergeEgoAndLead.Latitude_lead[i], mergeEgoAndLead.Longitude_lead[i])
            mergeEgoAndLead.DistanceToLeadCar[i] = hs.haversine(loc1, loc2)
    except:
        mergeEgoAndLead = ego1
        mergeEgoAndLead.insert(6, 'DistanceToLeadCar', " ", allow_duplicates=True)
    return mergeEgoAndLead

def Tonic(raw_signal):  # get tonic from raw gsr signal
    data = nk.eda_phasic(nk.standardize(raw_signal), sampling_rate=512)

    return data.EDA_Tonic


def Phasic(raw_signal):  # get phasic from raw gsr signal
    data = nk.eda_phasic(nk.standardize(raw_signal), sampling_rate=512)
    return data.EDA_Phasic

def isNaN(num):
    return num != num

def TonicDF(name, id):  # TonicDF return flag=0 if the clock is empty,return tonic+gps
    # tonic
    gsr = getGSR(name, id,1)
    gps = getGPS(name, id)

    if isNaN(gsr.SimulationTime.mean()):
        print("empty clock")
        return 0, 0

    tonic = pd.DataFrame(Tonic(gsr.GSR))
    tonic.insert(0, "SimulationTime", gsr.SimulationTime, True)
    tonic = tonic.groupby('SimulationTime').mean().reset_index()
    tonic = tonic.round({'SimulationTime': 4})
    gps = gps.round({'SimulationTime': 4})
    mergeTimeTonic = pd.merge(tonic, gps, how='inner', on='SimulationTime')
    mergeTimeTonic.insert(0, 'Name', name, allow_duplicates=True)
    return mergeTimeTonic, 1

def PhasicDF(name, id):  # PhasicDF return flag=0 if the clock is empty
    gsr = getGSR(name, id, 0)

    if isNaN(gsr.SimulationTime.mean()):
        print("empty clock")
        return 0, 0

    signals1, info1 = nk.eda_process(gsr.GSR, sampling_rate=512)
    arr = pd.DataFrame(columns=['SimulationTime', 'Amplitude', 'RiseTime'])
    for i in range(len(info1['SCR_Peaks'])):
        peakIndex = info1['SCR_Peaks'][i]
        arr = arr.append({'SimulationTime':gsr.SimulationTime[peakIndex], 'Amplitude':signals1.SCR_Amplitude[peakIndex],'RiseTime':signals1.SCR_RiseTime[peakIndex]}, ignore_index=True)
        # arr = arr.append({'SimulationTime':gsr.SimulationTime[peakIndex], 'Amplitude':signals1.SCR_Amplitude[peakIndex],'RiseTime':signals1.SCR_RiseTime[peakIndex],'measurementTime':gsr.measurementTime[peakIndex]}, ignore_index=True)

    arr = arr[arr.SimulationTime != 0].reset_index()
    arr = arr.filter(items=['SimulationTime', 'Amplitude', 'RiseTime'])
    arr = arr.round({'SimulationTime': 4})

    return arr,1

def TonicAndPhasicDF(name, id):  # tonic and phasic df
    dfTonic = TonicDF(name, id)[0]
    dfPhasic = PhasicDF(name, id)[0]
    if TonicDF(name, id)[1] == 0:
        return 0
    mergeTimeTonic = pd.merge(dfTonic, dfPhasic, how='outer', on='SimulationTime')
    return mergeTimeTonic

def newPhasic(name,id): #phasic df with simulation info
    tonic_phasic = TonicAndPhasicDF(name, id)
    df_phasic_new = pd.DataFrame()

    for x in tonic_phasic.index:
        if tonic_phasic.Amplitude[x] > 0:
            newRow = tonic_phasic.loc[[x]]
            df_phasic_new = df_phasic_new.append(newRow)
    return df_phasic_new

def locationToIndex(df,location):  # get df and location ,return event index
    minDist = 100
    minIndex = 0
    for i in df.index:
        locationDF = (df.Latitude[i], df.Longitude[i])
        dist = hs.haversine(location, locationDF)
        if dist < 0.005:
            if dist < minDist:
                minDist = dist
                minIndex = i
    return minIndex

def termination(name, id):  # get name and id return if  Reached end point == True
    df = pd.read_csv(os.getcwd() +('/%s/Simulator/%s.csv' % (id, name)))
    df = pd.DataFrame.from_dict(df, orient='columns')
    gps = df[df.Type == 'Termination'].reset_index()
    gps = gps.filter(items=['Reason'])
    try:
        if gps.Reason[0] == "End of simulation requested. Reason: Reached end point":
            return True
        else:
            return gps.Reason[0]
    except:
        return "DataFrame object has no attribute for Termination"


def eventDfTonic(name, id):  # get name and id , return df tonic of events
    df = TonicDF(name, id)[0]
    eventDF = pd.DataFrame()
    termination1 = termination(name, id)

    locExitOrder = (50.061328318333327, 8.679703474044802)
    locFirstBrake = (50.06123361426605, 8.681690990924837)
    locSecondBrake = (50.0613214307710, 8.679287731647493)

    index_locFirstBrake = locationToIndex(df, locFirstBrake)
    index_locExitOrder = locationToIndex(df, locExitOrder)
    index_locSecondBrake = locationToIndex(df, locSecondBrake)

    newRow1 = df.loc[[index_locFirstBrake]]
    newRow1.insert(2, 'Event', "FirstBrake", allow_duplicates=True)

    newRow2 = df.loc[[index_locExitOrder]]
    newRow2.insert(2, 'Event', "ExitOrder", allow_duplicates=True)

    newRow3 = df.loc[[index_locSecondBrake]]
    newRow3.insert(2, 'Event', "SecondBrake", allow_duplicates=True)

    eventDF = eventDF.append(newRow1)
    eventDF = eventDF.append(newRow2)
    eventDF = eventDF.append(newRow3)
    eventDF.insert(11, 'Completed', termination1, allow_duplicates=True)

    return eventDF

def getParticipantDf_tonic(id): #return all events sum
    newDf = pd.DataFrame()
    newDf = newDf.append(eventDfTonic("LOAD1_TTC1", id))
    newDf = newDf.append(eventDfTonic("LOAD2_TTC1", id))
    newDf = newDf.append(eventDfTonic("LOAD3_TTC1", id))
    newDf = newDf.append(eventDfTonic("LOAD1_TTC2", id))
    newDf = newDf.append(eventDfTonic("LOAD2_TTC2", id))
    newDf = newDf.append(eventDfTonic("LOAD3_TTC2", id)).reset_index()

    return newDf

def generate(id,name):

    dfGSR = getGSR(name, id, 1)

    signals, info = nk.eda_process(dfGSR.GSR, sampling_rate=512)
    nk.eda_plot(signals).savefig(f'{id}/Figures/{name}/EDA.png')

    dfGPS = getGPS(name, id)

    tdDF = TonicAndPhasicDF(name, id)

    ####################################################
    x = tdDF.Latitude
    y = tdDF.Longitude

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(x, y, c=tdDF.EDA_Tonic)
    ax.scatter(50.061483288221794, 8.6767315864563, label="end point")
    ax.set_title("Tonic")
    ax.legend()
    plt.savefig(f'{id}/Figures/{name}/tonic.png')

    ####################################################

    dfPhasic = newPhasic(name, id)

    x = dfPhasic.Latitude
    y = dfPhasic.Longitude
    x1 = tdDF.Latitude
    y1 = tdDF.Longitude

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(x1, y1, label="Route")
    ax.scatter(x, y, label="Phasic Peak")
    ax.scatter(50.061483288221794, 8.6767315864563, label="end point")
    ax.set_title("Phasic Peaks")
    ax.legend()
    plt.savefig(f'{id}/Figures/{name}/phasic.png')

if __name__ == '__main__':
    id = 'A5_094593'
    means = {}
    path = f'{id}/Simulator'
    scenarios = [os.path.splitext(filename)[0] for filename in os.listdir(path)]
    for scenario in scenarios:
        generate(id,scenario)
