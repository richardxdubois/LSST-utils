import sqlalchemy
import argparse


## Command line arguments
parser = argparse.ArgumentParser(description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-s','--stepName', default="SR-REB-INS-03_step4",help="step name in traveler (default=%(default)s)")
parser.add_argument('--minREB', default=0,help="min REB number (default=%(default)s)")
parser.add_argument('--maxREB', default=1000,help="max REB number (default=%(default)s)")
parser.add_argument('--db', default='db_connect.txt',help="db connect file (default=%(default)s)")
args = parser.parse_args()

kwds = {}
with open(args.db) as f:
    for line in f:
        (key, val) = line.split()
        kwds[key] = val


# extract manually submited currents from REB testing

# Create a new mysql connection object.
db_url = sqlalchemy.engine.url.URL('mysql+mysqldb', **kwds)
engine = sqlalchemy.create_engine(db_url)
mysql_connection = engine.raw_connection()

print 'connected to host' , kwds['host']

cursor = mysql_connection.cursor()

# LCA-13574 is the REB.

sql = "select hw.lsstId, res.activityId, act.rootActivityId, ip.label, res.value, ip.id from IntResultManual res join Activity act on res.activityId=act.id JOIN Hardware hw ON act.hardwareId=hw.id join Process pr on act.processId=pr.id join InputPattern ip on  res.inputPatternId=ip.id where pr.name='" + args.stepName + "' and ip.id=1685 order by res.activityId asc"

result = engine.execute(sql)
table_dict = {}
label_dict = {}
new_reb = ''

for res in result:
    reb = res['lsstId']
    reb_num = int(reb.split("-")[-1])
    if reb_num < int(args.minREB) or reb_num > int(args.maxREB): continue

    if reb not in table_dict: table_dict[reb]={}
    value = res['value']
    label = res['label'].split('at')[-1]
    if '<' in label: label = label.split('<')[0]
    table_dict[reb][label] = value
    
for reb in table_dict:
    label_title = '                '
    reb_list = table_dict[reb]
    for label in reb_list:
        label_title += label + ' '
    break
print label_title

for reb in sorted(table_dict):
    value_title = '                  '
    reb_list = table_dict[reb]
    for label in reb_list:
        value = reb_list[label]
        value_title += str(value) + '          '
    if value == 0:
        print reb
        print value_title

    

