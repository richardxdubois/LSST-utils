from github import Github
import base64
import inspect

def get_sha_for_tag(repository, tag):
    """
    Returns a commit PyGithub object for the specified repository and tag.
    """
    tags = repository.get_tags()
    matched_tags = [match for match in tags if match.name == tag]
    if not matched_tags:
        raise ValueError('No Tag or Branch exists with that name')
    return matched_tags[0].commit.sha

git = Github(None,None)
org = git.get_organization('lsst-camera-dh')
repo = org.get_repo('config_files')
print inspect.getargspec(org.get_repo)

#tag = Github("0.0.5")
print inspect.getargspec(repo.get_file_contents)
#sha = get_sha_for_tag(repo, "0.0.5")
#print sha

file_contents = repo.get_file_contents('BNL/TS8-Setup1/etc/rtm2/TS8Subsystem_e2v_Rafts.properties')

f = base64.b64decode(file_contents.content)
temp_file = open('temp','w')
temp_file.write(f)
temp_file.close()
temp_file = open('temp',"r")

# configs is a dict of reb's, with a list of property types (eg ASPIC0, DAC), each with a list of key value pairs
configs = {}
for lines in temp_file:
    parts =lines.split(".")
    if len(parts) > 2:
        what = parts[2].split('//')
        reb = parts[1]
        item = what[0]
    else:
        what = parts[1].split('//')
        reb = what[0]
        item = what[1]
    try:
        keypair = str(what[1].split('=')).strip()
    except:
        print 'Exception! ', parts, what
        pass
#    print 'parts = ', parts[1], ' what =', what[0], 'kp= ', keypair
    if reb not in configs:
        configs[reb] = []
#    look for this item in the reb's list of items; if not there, create an empty list
    t = [i for i, v in enumerate(configs[reb]) if v[0] == item]
    if len(t) == 0:  configs[reb].append((item,[]))
# now find that item and append the keypair to its list  (must be a better way than this!        
    t = [i for i, v in enumerate(configs[reb]) if v[0] == item]
    v[1].append(keypair)


print configs




        
