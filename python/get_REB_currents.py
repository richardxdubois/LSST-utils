import sqlalchemy

kwds = {}
kwds['username'] = 'rd_lsst_cam_ro'
kwds['password'] = '2chmu#2do'
kwds['host'] = 'mysql-node03.slac.stanford.edu'
kwds['port'] = '3306'
kwds['database'] = 'rd_lsst_cam'

# extract manually submited currents from REB testing

# Create a new mysql connection object.
db_url = sqlalchemy.engine.url.URL('mysql+mysqldb', **kwds)
engine = sqlalchemy.create_engine(db_url)
mysql_connection = engine.raw_connection()

print 'connected to host' , kwds['host']

cursor = mysql_connection.cursor()

# LCA-13574 is the REB.

sql = "select hw.lsstId, res.activityId, act.rootActivityId, ip.label, res.value from StringResultManual res join Activity act on res.activityId=act.id JOIN Hardware hw ON act.hardwareId=hw.id join Process pr on act.processId=pr.id join InputPattern ip on  res.inputPatternId=ip.id where pr.name='SR-REB-VER-01_step6' order by res.activityId asc"

result = engine.execute(sql)
table_dict = {}
label_dict = {}
new_reb = ''

for res in result:
    reb = res['lsstId']
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
    print reb
    reb_list = table_dict[reb]
    for label in reb_list:
        value_title += reb_list[label] + '          '
    print value_title

    

