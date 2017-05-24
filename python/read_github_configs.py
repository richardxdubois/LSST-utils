from github import Github
import base64
import inspect

def item_split(line):
    """item_split returns the split line and a split keypair"""
    item, pair = line.split('//')
    return item, pair.split(" = ")

git = Github(None,None)
org = git.get_organization('lsst-camera-dh')
repo = org.get_repo('config_files')

file_path = 'BNL/TS8-Setup1/etc/rtm2/TS8Subsystem_e2v_Rafts.properties'
tag = "refs/tags/0.0.13"

file_contents = repo.get_file_contents(file_path, ref=tag)

data = base64.b64decode(file_contents.content).decode()

# skip blank lines via len(line) check
lines = [line for line in data.split('\n') if len(line)] 

item_pairs = [item_split(line) for line in lines if len(line)]

# Note `sorted` call. This will take the set and return a sorted list
items = sorted(set([item for item, pair in item_pairs]))

# I think prefixes == rebs ? Unsure. Again, not use of `sorted`
prefixes = sorted(set(['.'.join(item.split('.')[0:2]) for item in items]))

#print(prefixes)

#print(item_pairs)


# configs is a dict of reb's, with a dict of property types (eg ASPIC0, DAC), each with a list of key value pairs
configs = {}
for item,  pair in item_pairs:
    more = item.split(".")
    reb = more[1]
    # R00.Reb0 by itself translates to an item key of the name of the value, since there's no actual item name
    item = more[2] if len(more) > 2 else pair[0] 
    # Get dict for config[reb] if it exists, otherwise set it to {} and return the 
    # blank dict
    reb_config = configs.setdefault(reb, {})
    # Same for reb item, but with list
    reb_items = reb_config.setdefault(item, [])
    reb_items.append(tuple(pair))
    # Otherwise, with dict instead of list
    # reb_items = reb_config.setdefault(item, {})
    # key, value = pair
    # reb_items[key] = value

print configs




        
