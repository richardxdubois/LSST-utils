from  eTraveler.clientAPI.connection import Connection
import datetime
import argparse
import numpy as np
import operator
import statsmodels.api as smapi
from statsmodels.formula.api import ols


## Command line arguments
parser = argparse.ArgumentParser(description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-r','--run', default=None,help="(raft run number (default=%(default)s)")
parser.add_argument('-d','--db',default='Prod',help="database to use (default=%(default)s)")
parser.add_argument('-e','--eTserver',default='Dev',help="eTraveler server (default=%(default)s)")
parser.add_argument('--appSuffix','--appSuffix',default='jrb',help="eTraveler server (default=%(default)s)")
args = parser.parse_args()


run = args.run
if args.eTserver == 'Prod': pS = True
else: pS = False


connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA', prodServer=pS, appSuffix='-'+args.appSuffix)

rsp = connect.getRunSummary(run=args.run)
raft = rsp['experimentSN']

rspRunAct = connect.getRunActivities(run=run)


print 'Run, raft ', run, raft, ' for ', args.db , 'database and server is ', args.eTserver

gain_table = {}
start = 0
    
returnData = connect.getRunResults(run=run)

for i in range(1,5):
    for j in range(1,11):
        step = 'fe55_raft_analysis_' + str(i) + '_' + str(j)

        for actStep in rspRunAct:
            step_name = actStep['stepName']
            if step_name <> step: continue
            if actStep['status'] <> 'success': continue

            begin = datetime.datetime.strptime(actStep['begin'],'%Y-%m-%dT%H:%M:%S.%f')
            if start == 0: start = begin
            dT = (begin - start).seconds
            print i, j, begin, dT
            break

        stepDict = returnData['steps'][step]

        for schemaList in stepDict:
            if 'fe55_raft_analysis' in schemaList:

                for d in stepDict[schemaList]:
                    if d['schemaInstance'] == 0: continue
                    # use schemaInstance to run amps from 1 to 144
                    shots = gain_table.setdefault(d['schemaInstance'], [])

                    shots.append((d['gain'], d['gain_error'], dT))
                break
frac = []

print '      amp           mean gain        std          std/mean (%)    fit slope    fit intercept   deltaT (sec) \n'

for amp in gain_table:
    mean_list = [element[0] for element in gain_table[amp]]
    t = [element[2] for element in gain_table[amp]]
    mean = np.mean(mean_list)
    std = np.std([element[1] for element in gain_table[amp]])
    frac_std = std/mean*100.
    frac.append((frac_std))

    model = ols('data ~ x',dict(x=t, data=mean_list))
    regression = model.fit()

    dt = t[-1] - t[0]
    res = regression.params

    print "%8i          %6.3f          %6.3E         %6.3f       %6.3E      %6.3f      %6.2f" % (amp, mean, std, frac_std, res['x'], res['Intercept'], dt)

index, value = max(enumerate(frac), key=operator.itemgetter(1))
print 'Largest width = ', value, ' % for amp ', index+1

print t


    

