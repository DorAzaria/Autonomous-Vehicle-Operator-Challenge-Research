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

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def getGSR(name, id, flag):  # load xlsx to gsr df, flag=0 with zero, removes final clock duplication
    df12 = pd.read_csv(os.getcwd() + ('/%s/Physiological/%s.csv' % (id, name)))
    df12 = df12.rename(columns={'simulation time': 'SimulationTime'})
    df12 = df12.rename(columns={'measurement time': 'measurementTime'})

    #   removes final clock duplication
    dfLastIndex = df12.index[-1]
    endTime = df12.SimulationTime[dfLastIndex]
    for i in df12.index:
        if df12.SimulationTime[i] == endTime:
            myLastIndex = i + 11
            break
    newGsr = df12.iloc[0:myLastIndex]

    # filter time and gsr
    if flag == 1:
        newGsr = newGsr[newGsr.SimulationTime != 0].reset_index(drop=True)

    newGsr = newGsr.filter(items=['SimulationTime', 'GSR', 'measurementTime'])
    return newGsr


def getLeadCar(name, id):  # load json to gsp df
    df = pd.read_csv(os.getcwd() + ('/%s/Simulator/%s.csv' % (id, name)))

    df = (pd.DataFrame(df['Logs'].values.tolist()).join(df.drop('Logs', 1)))
    df = pd.DataFrame.from_dict(df, orient='columns')
    df3 = df[df.Name == 'lead car'].reset_index()
    df3 = df3.filter(items=['SimulationTime', 'Latitude', 'Longitude'])  # 'Speed', 'PositionInLane', 'LaneNumber'])
    df3 = df3.rename(columns={'Latitude': 'Latitude_lead'})
    df3 = df3.rename(columns={'Longitude': 'Longitude_lead'})
    return df3


def getGPS(name, id):  # load json to gsp df
    df = pd.read_csv(os.getcwd() + ('/%s/Simulator/%s.csv' % (id, name)))
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
    gsr = getGSR(name, id, 1)
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
        arr = arr.append(
            {'SimulationTime': gsr.SimulationTime[peakIndex], 'Amplitude': signals1.SCR_Amplitude[peakIndex],
             'RiseTime': signals1.SCR_RiseTime[peakIndex]}, ignore_index=True)

    arr = arr[arr.SimulationTime != 0].reset_index()
    arr = arr.filter(items=['SimulationTime', 'Amplitude', 'RiseTime'])
    arr = arr.round({'SimulationTime': 4})

    return arr, 1


def TonicAndPhasicDF(name, id):  # tonic and phasic df
    dfTonic = TonicDF(name, id)[0]
    dfPhasic = PhasicDF(name, id)[0]
    if TonicDF(name, id)[1] == 0:
        return 0
    mergeTimeTonic = pd.merge(dfTonic, dfPhasic, how='outer', on='SimulationTime')
    return mergeTimeTonic


def newPhasic(name, id):  # phasic df with simulation info
    tonic_phasic = TonicAndPhasicDF(name, id)
    df_phasic_new = pd.DataFrame()

    for x in tonic_phasic.index:
        if tonic_phasic.Amplitude[x] > 0:
            newRow = tonic_phasic.loc[[x]]
            df_phasic_new = df_phasic_new.append(newRow)
    return df_phasic_new


def termination(name, id):  # get name and id return if  Reached end point == True
    df = pd.read_csv(os.getcwd() + ('/%s/Simulator/%s.csv' % (id, name)))
    df = pd.DataFrame.from_dict(df, orient='columns')
    gps = df[df.Type == 'Termination'].reset_index()
    gps = gps.filter(items=['Reason'])
    try:
        if gps.Reason[0] == "End of simulation requested. Reason: Reached end point":
            return "No"
        else:
            return "Yes"
    except:
        return "None"


def getMeanPhasic(name, id):
    dfGSR = getGSR(name, id, 1)
    signals, info = nk.eda_process(dfGSR.GSR, sampling_rate=512)
    return signals['EDA_Phasic'].values.mean(), signals['EDA_Tonic'].values.mean()


def getPeaks(name, id):
    dfGSR = getGSR(name, id, 1)
    signals, info = nk.eda_process(dfGSR.GSR, sampling_rate=512)
    peaks = signals['SCR_Peaks']
    heights = signals['SCR_Height']
    sum = 0
    times = 0
    for i in range(len(peaks)):
        if peaks[i] == 1:
            sum += heights[i]
            times += 1

    return sum / times, times


if __name__ == '__main__':
    id = 'A1_030951'
    means = {}
    path = f'{id}/Simulator'
    scenarios = [os.path.splitext(filename)[0] for filename in os.listdir(path)]
    getPeaks(scenarios[0], id)
    for scenario in scenarios:
        peak = getPeaks(scenario, id)
        means[scenario] = (getMeanPhasic(scenario, id), termination(scenario, id), peak[0], peak[1])

    f = open(f'{id}/Figures/research2.txt', "w")
    f.write('   Name\t\t\t\tPhasic\t\t\t\t\tTonic\t\tAn accident occurred\t  Peak Height Mean\t\tNum of Peaks')
    f.write(
        '\n----------------------------------------------------------------------------------------------------------------------')

    print(f'{bcolors.OKBLUE}   Name\t\t\t\tPhasic\t\t\t\t\tTonic\t\tAn accident occurred\t  Peak Height Mean\t\tNum of Peaks{bcolors.ENDC}')
    print('----------------------------------------------------------------------------------------------------------------------')

    phasic_means = []
    tonic_means = []
    peak_means = []
    peak_nums = []
    keys = []
    for y, x in means.items():
        if x[1] == "Yes":
            print(f'{bcolors.FAIL}{y} |  {x[0][0]}  |  {x[0][1]} |  \t\t{x[1]}  | \t\t\t {x[2]} |  \t\t {x[3]}{bcolors.ENDC}')
        else:
            print(f'{y} |  {x[0][0]}  |  {x[0][1]} |  \t\t{x[1]}  | \t\t\t {x[2]} |  \t\t {x[3]}')
        f.write(f'\n{y} |  {x[0][0]}  |  {x[0][1]} |  \t\t{x[1]}  | \t\t\t {x[2]} |  \t\t {x[3]}')
        phasic_means.append(x[0][0])
        tonic_means.append(x[0][1])
        peak_means.append(x[2])
        peak_nums.append(x[3])
        keys.append(y)

    f.close()

    fig, ax = plt.subplots(2, 2)

    ax[0, 0].scatter(phasic_means, keys)
    ax[0, 0].set_title('Phasic Mean Rate')
    ax[0, 0].set_xlabel('Rate')

    ax[1, 0].scatter(peak_means, keys)
    ax[1, 0].set_title('Peak Height Mean Rate')
    ax[1, 0].set_xlabel('Rate')

    ax[0, 1].scatter(tonic_means, keys)
    ax[0, 1].set_title('Tonic Mean Rate')
    ax[0, 1].set_xlabel('Rate')

    ax[1, 1].scatter(peak_nums, keys)
    ax[1, 1].set_title('Number of Peaks')
    ax[1, 1].set_xlabel('Number')
    ax[1, 1].set_xticks(peak_nums)

    for y, x in means.items():
        if x[1] == "Yes":
            ax[0, 0].scatter(x[0][0], y, s=200, c='red', marker='x')
            ax[0, 1].scatter(x[0][1], y, s=200, c='red', marker='x')
            ax[1, 0].scatter(x[2], y, s=200, c='red', marker='x')
            ax[1, 1].scatter(x[3], y, s=200, c='red', marker='x')

    fig.suptitle(f'EDA Mean Rate for user {id} ', fontsize="x-large")
    fig.tight_layout()

    plt.savefig(f'{id}/Figures/MeanRate.png')

    plt.show()
