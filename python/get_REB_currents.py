##import sqlalchemy
import argparse
from eTraveler.clientAPI.connection import Connection

## Command line arguments
parser = argparse.ArgumentParser(description='Extract manual operator entries for re-recorded currents for REBs')

parser.add_argument('--minREB', default=0,help="min REB number (default=%(default)s)")
parser.add_argument('--maxREB', default=1000,help="max REB number (default=%(default)s)")
parser.add_argument('-d', '--db', default='Prod', help="eT database (default=%(default)s)")
parser.add_argument('-e', '--eTserver', default='Dev', help="eTraveler server (default=%(default)s)")
parser.add_argument('--appSuffix', '--appSuffix', default='jrb',
                    help="eTraveler Dev server instance (default=%(default)s); ignored if --etServer=Prod")

args = parser.parse_args()

# LCA-13574 is the REB.
rebType='LCA-13574'
travelerName='SR-REB-VER-01'
stepNames=['SR-REB-VER-01_step6', 'SR-REB-VER-01_step5']

# extract manually submitted currents from REB testing

# Create a new eTraveler API connection 
if args.eTserver == 'Prod':
    connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA',
                         prodServer=True)
else:
    pS = False
    connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA',
                         prodServer=False, appSuffix='-' + args.appSuffix)

table_dict = {}
label_dict = {}
new_reb = ''

print 'min, max REB ', args.minREB, args.maxREB
print '\n\n'

for stepName in stepNames:
    try:
        rsp = connect.getManualResultsStep(travelerName=travelerName,
                                           stepName=stepName,
                                           hardwareType=rebType)
    except Exception, msg:
        print msg
        raise

    for cmp in rsp:
        cmpdata = rsp[cmp]
        reb = cmpdata['experimentSN']
        reb_num = int(reb.split("-")[-1])
        if reb_num < int(args.minREB) or reb_num > int(args.maxREB): continue
        
        if reb not in table_dict: table_dict[reb]={}

        stepdata = cmpdata['steps'][stepName]
        for entryname in stepdata:
            entrydict = stepdata[entryname]
            if entrydict['isOptional'] == 1: continue
            if entrydict['datatype'] != 'string': continue
            parts = entryname.split('_current_at_')
            if len(parts) != 2: continue
            label=parts[1]
            value=entrydict['value']
            table_dict[reb][label] = value

rebNameWidth = 13
aReb = list(table_dict)[0]
reb_dict = table_dict[aReb]

fieldWidth = max(len(k) for k in reb_dict) + 2
formatTitle = 'REB          '
formatValues = '{:' + str(rebNameWidth) + '}'
ix = 0
label_list = []
for k in reb_dict:
    label_list.append(k)
    formatTitle += ('{d[' + str(ix) + ']:>' + str(fieldWidth) + '}')
    formatValues += '{valueDict[' + k + ']:>' + str(fieldWidth) + '}'
    ix += 1

#print 'formatTitle string is:  ', formatTitle
#print 'formatValues string is: ', formatValues
#print '\n\n\n'
print formatTitle.format(d=label_list)

for reb in sorted(table_dict):
    valueString = formatValues.format(reb, valueDict=table_dict[reb])
    print valueString


    

