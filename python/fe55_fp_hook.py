from __future__ import print_function
import pickle

def hook(run=None, mode=None, slot=None):
    """
    User hook for test quantity
    :param run: run number
    :return: list of user-supplied quantities to be included in the heat map
    """
    print("called user hook with run ", str(run), slot)

    count_list = []

    with open("/Users/richard/LSST/Data/fe55_fp_hits.pkl", "rb") as openfile:
        hm = pickle.load(openfile)

        for index, row in hm.iterrows():
            raft = row['raft']
            if raft == slot:
                sensor = row['sensor']
                amp = row['amp']
                count = row['count']
                count_list.append(count)

    return count_list


if __name__ == "__main__":

    fl = hook(slot="R10")
