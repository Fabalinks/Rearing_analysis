import math
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import scipy.stats
import os
import h5py
import os
from datetime import datetime


figures = 'C:/Users/Fabian/Desktop/Analysis/Round3_FS03_FS06/Figures/'
processed= 'C:/Users/Fabian/Desktop/Analysis/Round3_FS03_FS06/processed/'


#Hardset cutoffs of the arena - if new calibration need to change.
cut = 0 # keeping the cut where rectangle of arena ends
X_cut_min = -.59
Y_cut_max = 1.61
X_cut_max = .12
Y_cut_min = .00
#print("area %s M*2" %((X_cut_max-X_cut_min)*(Y_cut_max-Y_cut_min)))
#Translations
x_max, x_min = 0.12, -0.59
x_offset = x_max - (x_max - x_min)/2
y_max, y_min = 1.61,  0
y_offset = y_max - (y_max - y_min)/2
#print(x_offset,y_offset)
xcut_offset=-.24
ycut_offset=-.8
#alpha
rotation= 1.7




def rotation_correction_points(position_data,alpha=1.7):
    alpha = (alpha) * np.pi / 180
    rot_position_data = position_data
    rot_position_data[1] = position_data[1] * np.cos(alpha) - position_data[3] * np.sin(alpha)
    rot_position_data[3] = position_data[1] * np.sin(alpha) + position_data[3] * np.cos(alpha)
    return rot_position_data
def rotation_correction_beacons(position_data,alpha=-5):
    alpha = (alpha) * np.pi / 180
    rot_position_data = position_data
    rot_position_data["BeaconX"] = position_data["BeaconX"] * np.cos(alpha) - position_data["BeaconY"] * np.sin(alpha)
    rot_position_data["BeaconY"] = position_data["BeaconX"] * np.sin(alpha) + position_data["BeaconY"] * np.cos(alpha)
    return rot_position_data


def Z_period_points(positions,In_arena):
    """get every rear event in center of arena

    If animal gets above .62 detect it as one until below again

    PARAMS
    ------------
    positions : DataFrame

    Returns
    ------------
    Data Frame with all rears position (begining of rear) and time.

    """
    high = 0
    low = 0
    switch = 0
    last = .60
    high_points = []
    z = positions[2]
    count = 0
    for height in z:
        if height > .62 and last < .62:
            high += 1
            if In_arena:
                if (X_cut_min + cut) < positions[1][count] < (X_cut_max - cut) and (Y_cut_min + cut) < positions[3][
                    count] < (Y_cut_max - cut):
                    high_points.append((positions[0][count], positions[1][count], positions[3][count], positions[2][count]))
            else:
                high_points.append((positions[0][count], positions[1][count], positions[3][count], positions[2][count]))
        last = height
        count += 1

    return pd.DataFrame(high_points)


def vis_invis(beacon, light_off=4):
    """ Add 6th column to beacon file if visible or not

    PARAMS
    ------------
    beacon : DataFrame
        beacons
    light_off : int
        how often beacon visible

    Returns
    ------------
    Data Frame with all beacon position and if visible or not

    """
    visibility = []
    for i in beacon.index:
        if ((i + 1) % light_off == 0):
            visibility.append(0)
        else:
            visibility.append(1)
    beacon[6] = visibility
    return beacon


def invis_succ_meta(beacon, invisible_time=60, light_off=6):
    """Find succesfull invisible trials and name them 2 in the 6th column also incorporate metadata to subtract correctly
    PARAMS
    ------------
    beacon : DataFrame
        beacons
    invisible_time ; int
        Inter trial interval time
    light_off : int
        how often beacon visible

    Returns
    ------------
    Data Frame with all beacon position and if visible or not and collecting succesful visible trials
    """
    invis = []
    df = beacon[0].diff().to_frame()
    for ind in df.index:
        if df[0][ind] < invisible_time and ((ind + 1) % light_off == 0):
            invis.append(df[0][ind])
            beacon[6][ind] = 2
    return beacon


def invis_times_meta(beacon, invisible_time=60, light_off=4):
    """Add invisible time from beacon
    PARAMS
    ------------
    beacon : DataFrame
        beacons
    invisible_time ; int
        Inter trial interval time
    light_off : int
        how often beacon visible

    Returns
    ------------
    Data Frame with all beacon position and if visible or not and collecting
    succesful visible trials an dho much time elapsed since invisible beacon

    """
    invis = []
    beacon[7] = 0.0
    df = beacon[0].diff().to_frame()
    for ind in df.index:
        if df[0][ind] > invisible_time and ((ind + 1) % light_off == 0):
            beacon[7][ind] = beacon[0][ind - 1] + invisible_time
            invis.append((beacon[0][ind - 1], beacon[0][ind - 1] + invisible_time))
        elif ((ind + 1) % light_off == 0):
            invis.append((beacon[0][ind - 1], beacon[0][ind]))
            beacon[7][ind] = beacon[0][ind]
        else:
            beacon[7][ind] = beacon[0][ind]
    return beacon, invis


def match_and_append(Z_points, beacon, times):
    """Matchs a beacon to a particular rear and join into one data frame also rotate them!
    PARAMS
    ------------
    Z_points : DataFrame
        rears
    beacon ; DataFrame
        beacon
    times : tuples
        tuple of all invisible intervals

    Returns
    ------------
    Data Frame with all beacon position matching to rears

    """
    alpha = 1.7
    df_rears = Z_points
    df_rears[7] = 1
    df_rears[8] = 0
    i = 0
    Xs = []
    Ys = []
    visibility = []
    beacon_trigger = []
    beacon_seen_in_rear = []
    for index, row in df_rears.iterrows():
        k = beacon.iloc[(beacon[0] - row[0]).abs().argsort()[:1]]
        for r in times:
            if r[0] < row[0] < r[1]:
                df_rears.loc[index, 7] = 0
            elif df_rears.loc[index, 7] == 0:
                break
        if row[0] <= beacon[0][i]:
            beacon_trigger.append(beacon[0][i])
            Xs.append(beacon[4][i])
            Ys.append(beacon[5][i])
            # visibility.append(beacon[6][i])
        elif row[0] > beacon[0][i] and i < len(beacon) - 1:
            # print(len(beacon))
            i += 1
            beacon_trigger.append(beacon[0][i])
            Xs.append(beacon[4][i])
            Ys.append(beacon[5][i])
            # visibility.append(beacon[6][i])
        else:
            beacon_trigger.append(beacon[0][i])
            Xs.append(beacon[4][i])
            Ys.append(beacon[5][i])
            # visibility.append(beacon[6][i])

    df_rears[8] = beacon_trigger
    # return rearing

    # print(beacon_seen_in_rear)
    df_rears[4] = Xs
    df_rears[5] = Ys
    # df_rears[6]=visibility
    df_rears[8] = beacon_trigger
    # df_rears[8]=beacon_seen_in_rear
    df_rears_corrected = df_rears
    df_rears_corrected[1] = df_rears[1] - x_offset
    df_rears_corrected[2] = df_rears[2] - y_offset

    # Rotate beacons
    alpha = (alpha) * np.pi / 180
    Xs = df_rears_corrected[4]
    Ys = df_rears_corrected[5]
    df_rears[4] = Xs * np.cos(alpha) - Ys * np.sin(alpha)
    df_rears[5] = Xs * np.sin(alpha) + Ys * np.cos(alpha)
    # Rotate positions
    Xpos = df_rears_corrected[1]
    Ypos = df_rears_corrected[2]
    df_rears_corrected[1] = Xpos * np.cos(alpha) - Ypos * np.sin(alpha)
    df_rears_corrected[2] = Xpos * np.sin(alpha) + Ypos * np.cos(alpha)

    return df_rears_corrected[[0, 1, 2, 3, 4, 5, 7, 8]]


def beacon_group(rearing, location_change=10):
    """
    Detect change in beacon location - create beacon group number for fatigue measures

    PARAMS
    ------------
    rears : DataFrame
        rearing
    location_change : int
        from metadata

    Returns
    ------------
    Data Frame with named by group and how many beacons already

    """
    group = []
    sub_group = []
    group_num = 0
    sub_group_num = 0
    rearing[9] = rearing[4].shift() != rearing[4]
    rearing[10] = rearing[8].shift() != rearing[8]
    rearing[11] = rearing[8].shift() != rearing[8]
    for index, row in rearing.iterrows():
        if row[9] == True:
            group_num += 1
            group.append(group_num)
        else:
            group.append(group_num)
    for index, row in rearing.iterrows():
        if row[10] == True and sub_group_num < location_change:
            sub_group_num += 1
            sub_group.append(sub_group_num)

        elif row[10] == True and sub_group_num == location_change:
            sub_group_num = 1
            sub_group.append(sub_group_num)
        else:
            sub_group.append(sub_group_num)
    rearing[9] = group
    rearing[10] = sub_group
    return rearing


def make_rearing_df_meta(position, beacon,In_arena, invisible_time=60, light_off=2, location_change=10):
    """
    Run all and merge

    PARAMS
    ------------
    position: Data Frame
        positions
    beacon : DataFrame
        beacon
    invisible_time : int
        Inter trial interval
    light_off :int
        starting invisibility
    location_change : int
        from metadata when beacon changes location

    Returns
    ------------
    Data Frame - complete with rears time and beacon groups

    """
    Z_points = Z_period_points(position,In_arena)
    beacon = vis_invis(beacon, light_off=2)
    beacon = invis_succ_meta(beacon, invisible_time=60, light_off=2)
    beacon, times = invis_times_meta(beacon, invisible_time=60, light_off=2)
    rearing_df = match_and_append(Z_points, beacon, times)
    rearing_df = beacon_group(rearing_df, location_change=10)
    return rearing_df





def crawl_make_and_safe(rat_ID, In_arena ,Save_plots=True):
    """
    Crawl through, find metadata, beacons and position files that match and run all the function above to then save a spread sheet.

    PARAMS
    ------------
    Rat_ID: str
        name of animal ['FS09']
    Save plots: boolean
        To save session rearign plots or not

    Returns
    ------------
    nothing - automatically saves into processed

    """

    how_many = 0
    substring = "BPositions_"
    position = "position_2"
    beacon = 'beacons'
    metadata = 'metadata'
    animal = '//10.153.170.3/storage2/fabian/data/project/' + rat_ID
    average_rears = []
    animal_dir = os.path.join(figures + rat_ID)
    if not os.path.isdir(animal_dir):
        os.makedirs(animal_dir)
    rearing = pd.DataFrame()
    all_metadata = pd.DataFrame()
    for dirpath, dirnames, files in os.walk(animal, topdown=True):
        fullstring = dirpath
        for file_name in files:
            fullstring = dirpath
            if beacon in file_name:
                beacons = pd.read_csv(dirpath + '/' + file_name, sep=" ", header=None, engine='python')
                beacon_date = list(file_name)
            if metadata in file_name:
                metadatas = pd.read_csv(dirpath + '/' + file_name, sep=" : ", header=None, engine='python')
                df = metadatas.T
                df = df.rename(columns=df.iloc[0])
                df = df.drop(df.index[0])
                if int(df['Pellets'].values[0]) > 1:
                    all_metadata = all_metadata.append(df, ignore_index=True, sort=False)
                    invisible_time = int(df['invisible_time'].values[0])
                    light_off = int(df['light_off'].values[0])
                    location_change = (df['position_change'].values[0])
                    Computer_time_was = (df['Computer time was'].values[0])
                    # print(int(Computer_time_was))
                    time_stamp = datetime.fromtimestamp(int(float(Computer_time_was))).strftime('%Y%m%d-%H%M%S')
                    print(time_stamp)
            if position in file_name:
                positions = pd.read_csv(dirpath + '/' + file_name, sep=" ", header=None, engine='python')
                positions_date = list(file_name)
                if beacon_date[-9:] == positions_date[-9:]:
                    print("Match found making rearing file")
                    how_many += 1
                    rearing_df = make_rearing_df_meta(positions,beacons,In_arena ,invisible_time=invisible_time,light_off=light_off,location_change=location_change)
                    average_rears.append(len(rearing_df.index))
                    plt.plot(rearing_df[1], rearing_df[2], 'yo', ms=10)
                    plt.plot(rearing_df[4], rearing_df[5], 'g+')
                    if Save_plots is True:
                        plt.savefig('%s/%srears_%s.png' % (animal_dir, time_stamp, rat_ID), dpi=200)
                    plt.show()
                    if how_many < 1.5:
                        rearing = rearing_df
                        # print(rearing)
                    else:
                        rearing = rearing.append(rearing_df, ignore_index=True)
                else:
                    print('bad match')
    sorted_data = all_metadata.sort_values('Computer time was', )

    # SAVER AND NAMING  FUNCTIONS
    writer = pd.ExcelWriter(processed + rat_ID + '_metadata.xlsx')
    sorted_data.to_excel(writer)
    writer.save()

    rearing.columns = ["Time", "RatX", "RatY", "RatZ", "BeaconX", "BeaconY", "Visibility", "time_of_beacon_trigger",
                       "Beacon_group", 'Beacon_subgroup', 'trial_in_next', ]
    if In_arena:
        writer = pd.ExcelWriter(processed + rat_ID + '_rears_in_arena.xlsx')
        rearing.to_excel(writer)
        writer.save()
    else:
        writer = pd.ExcelWriter(processed + rat_ID + '_rears_all.xlsx')
        rearing.to_excel(writer)
        writer.save()

###### - maybe only worth to load this in function individually??
# FS08=pd.read_excel(processed +'FS08_rears_new.xlsx', index_col=0)
# FS09=pd.read_excel(processed +'FS09_rears_new.xlsx', index_col=0)
# FS10=pd.read_excel(processed +'FS10_rears_new.xlsx', index_col=0)
# FS11=pd.read_excel(processed +'FS11_rears_new.xlsx', index_col=0)
######

def day_cutter(Animal_ID,In_arena, days=(0, 1)):
    """Cuts data frame to day chunks

    PARAMS
    ------------
    Animal_ID : str
        name of animal to load data from processed.
    days : tuple
        which days to extract from rearing dataframe
    Returns
    ------------
    cut rears by days in tuple

    """
    if In_arena:
        rears= pd.read_excel(processed + Animal_ID+'_rears_in_arena.xlsx', index_col=0)
    else:
        rears = pd.read_excel(processed + Animal_ID + '_rears_all.xlsx', index_col=0)
    time_stamp_old = rears['Time'][0]
    day = 0
    index_list = []
    index_list.append(0)
    for index, row in rears.iterrows():
        time_stamp = (row['Time'])
        if time_stamp - time_stamp_old > 10000:  # larger then 3 hours
            index_list.append(index)
            day += 1
        time_stamp_old = time_stamp

    return rears[index_list[days[0]]:index_list[days[1]]]


def Z_period_dynamics_beg_end(positions):
    """get every rear event in center of arena

    If animal gets above .62 detect it as one until below again

    PARAMS
    ------------
    positions : DataFrame

    Returns
    ------------
    Data Frame with all rears position (begining of rear) and time.

    """
    high = 0
    low = 0
    switch = 0
    last = .60
    last2 = .60
    high_points = []
    high_points_end = []
    z = positions[2]
    count = 0
    for height in z:
        if height > .62 and last < .62:
            high += 1
            # if  (X_cut_min+cut)< positions[1][count]<(X_cut_max-cut) and (Y_cut_min+cut)< positions[3][count]<(Y_cut_max-cut):
            high_points.append((positions[0][count], positions[1][count], positions[3][count], positions[2][count]))
        last = height
        # print("beg" , last)
        if height < .62 and last2 > .62:
            high += 1
            # if  (X_cut_min+cut)< positions[1][count]<(X_cut_max-cut) and (Y_cut_min+cut)< positions[3][count]<(Y_cut_max-cut):
            high_points_end.append((positions[0][count], positions[1][count], positions[3][count], positions[2][count]))
        last2 = height
        count += 1
        # print("end", last)
    return pd.DataFrame(high_points), pd.DataFrame(high_points_end)


def Rearing_traj(position_data, metadata, buffer=10):
    """
    Generate trials +- buffer aorund where animal is above .62 "rearing"

    PARAMS
    ------------
    positions : DataFrame
    metadata : data frame of metadata to be used for invisible rears and attempts.
    buffer : how many sampled before and after to see - could run into errors here!!

    Returns
    ------------
    trial_list: list of numpy arrays position data [time, x, y, z] .
    rear_time: list of rears detected
    trial_visible: list of booleans referring visibility of trial (True - visible, False- invisible)
    """

    rear_time_beg, rear_time_end = Z_period_dynamics_beg_end(position_data)

    trial_list = []
    # print(beacon_data.iloc[:, -2:])
    trial_beacon = rear_time_end.iloc[:, -2:]

    sampling_rate = position_data.iloc[1, 0] - position_data.iloc[0, 0]
    rear_time_beg_idx = [
        np.argmin(abs(position_data.iloc[:, 0] - i)) for i in rear_time_beg.iloc[:, 0]
    ]
    rear_time_end_idx = [
        np.argmin(abs(position_data.iloc[:, 0] - i)) for i in rear_time_end.iloc[:, 0]
    ]

    trial_list.append(position_data[rear_time_beg_idx[0] - buffer:rear_time_end_idx[0] + buffer])
    for i in range(len(rear_time_end_idx)):
        if i != len(rear_time_end_idx) - 1:
            trial = position_data[rear_time_beg_idx[i] - buffer:rear_time_end_idx[i] + buffer]
        else:
            print('last rear')  # trial = position_data[rear_time_beg_idx[i]:]
        trial_list.append(trial)
    visible = []
    trial_visible = [True] * len(trial_list)
    invisible_time = eval(metadata['invisible_time'].item())
    invisible_index = eval(metadata['invisible_list'].item())

    ### Had to uncoment this for now due to some rears ending past the recordign lenght.

    #     for n, trial in enumerate(trial_list):
    #         trial_visible_ = np.ones_like(trial)
    #         if n in invisible_index:
    #             time_after = np.cumsum(trial.iloc[1:, 0] - trial.iloc[:-1, 0])
    #             if time_after.iloc[-1] > invisible_time:
    #                 invisible_end = np.where(time_after >= invisible_time)[0][0]
    #                 trial_visible_ = trial_visible_[:invisible_end]
    #             trial_visible[n] = False
    #         visible.append(trial_visible_)

    return trial_list, trial_beacon,  # visible, trial_visible


def Make_rear_dyn(rat_ID):
    """
    Should crawl through, check for time and data and generate rear ends and begs for a given time
    then make all trajectoriess into Data frame??
    """
    how_many = 0
    substring = "BPositions_"
    position = "position_2"
    beacon = 'beacons'
    metadata = 'metadata'
    animal = '//10.153.170.3/storage2/fabian/data/project/' + rat_ID
    average_rears = []
    animal_dir = os.path.join(figures + rat_ID)
    if not os.path.isdir(animal_dir):
        os.makedirs(animal_dir)
    animal_process = os.path.join(processed + rat_ID)
    if not os.path.isdir(animal_process):
        os.makedirs(animal_process)
    # rearing = pd.DataFrame()

    for dirpath, dirnames, files in os.walk(animal, topdown=True):
        fullstring = dirpath
        # if how_many<3:
        for file_name in files:
            # print(file_name)
            fullstring = dirpath
            if beacon in file_name:
                beacons = pd.read_csv(dirpath + '/' + file_name, sep=" ", header=None, engine='python')
                beacon_date = list(file_name)
            if metadata in file_name:
                metadatas = pd.read_csv(dirpath + '/' + file_name, sep=" : ", header=None, engine='python')
                df = metadatas.T
                df = df.rename(columns=df.iloc[0])
                df = df.drop(df.index[0])
                if int(df['Pellets'].values[0]) > 1:
                    invisible_time = int(df['invisible_time'].values[0])
                    light_off = int(df['light_off'].values[0])
                    location_change = (df['position_change'].values[0])
                    Computer_time_was = (df['Computer time was'].values[0])
                    # print(int(Computer_time_was))
                    time_stamp = datetime.fromtimestamp(int(float(Computer_time_was))).strftime('%Y%m%d-%H%M%S')
                    print(time_stamp)
            if position in file_name:
                positions = pd.read_csv(dirpath + '/' + file_name, sep=" ", header=None, engine='python')
                positions_date = list(file_name)
                if beacon_date[-9:] == positions_date[-9:]:
                    print("Match found making rearing file")
                    how_many += 1

                    rearing_df, trial_beacon = Rearing_traj(positions, df, buffer=0)
                    # rearing_df = pd.DataFrame.from_records(rearing_df)
                    # print (rearing_df)
                    ## save in HDF5

                    if not os.path.exists(processed + '/' + rat_ID):
                        os.makedirs(processed + '/' + rat_ID)
                    with h5py.File(processed + '/' + rat_ID + '/' + rat_ID + '.h5', mode='a') as f:
                        grp = f.create_group(time_stamp)
                        for i in range(len(rearing_df)):
                            name = str(i)
                            grp.create_dataset(name, data=rearing_df[i])

                else:
                    print('bad match')

    return

