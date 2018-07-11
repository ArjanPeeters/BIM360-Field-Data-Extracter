from __future__ import print_function
import requests
import json
import datetime
try:
    from ConfigParser import SafeConfigParser
except ImportError:
    from configparser import SafeConfigParser


# get info from config.ini
config = SafeConfigParser()
config.read('config.ini')

username = config.get("Field", "username")
password = config.get("Field", "password")
client_id = config.get("HQ", "client_id")
client_secret = config.get("HQ", "client_secret")
account_id = config.get("HQ", "account_id")


BASE_URL_FIELD = "https://bim360field.eu.autodesk.com/"
BASE_URL_EU_HUB = "https://developer.api.autodesk.com/hq/v1/regions/eu/accounts/" + account_id

# ignore projects in this list
ignore_projects = [
    "Sample Project",
    "Lokhorst Template Project"
]


# control what info you want to download
harvest_info = {
    'project_info': True,
    'companies': True,
    'contacts': True,
    'issues': True,
    'tasks': True,
    'equipment': True,
    'areas': True,
    'categories': True,
    'checklists': True
}

# Login in FIELD
url = BASE_URL_FIELD + "api/login"

payload = 'username={un}&password={pw}'.format(un=username, pw=password)
headers = {
    'content-type': "application/x-www-form-urlencoded",
    'Authorization':
    "Basic ZWRnYXIud2VzdGVyaG92ZW5AYXV0b2Rlc2suY29tOltudGVyUzc2",
    'Cache-Control': "no-cache",
}

response = requests.post(url, data=payload, headers=headers).json()

field_ticket = response['ticket']
print("Field login successful")


# function for FIELD commands
def field_api_cmd(soort, command, payload):
    url = '{base_url}{command}'.format(base_url=BASE_URL_FIELD, command=command)
    headers = {
        'content-type': "application/x-www-form-urlencoded",
        'Cache-Control': "no-cache",
    }

    response = requests.request(soort, url, data=payload, headers=headers).json()
    return response


# get all HQ & ID's from field
grant_type = "client_credentials"
scope = "data:read account:read bucket:read"

all_project_HQs = []
all_project_IDs = []
all_project_names = []

# get all field projects from field
get_projects = field_api_cmd("GET", "api/projects", {'ticket': field_ticket})

# extract project id's and hq id's
for i in range(len(get_projects)):
    current_project = get_projects[i]
    if current_project['name'] not in ignore_projects:
        all_project_HQs.append(current_project['hq_identifier'])
        all_project_IDs.append(current_project['project_id'])
        all_project_names.append(current_project['name'])

# Login in to HQ
payload = (
    'client_id={cid}&client_secret={cs}&Account_id={aid}&grant_type={gt}&scope={s}'
    .format(cid=client_id, cs=client_secret, aid=account_id, gt=grant_type, s=scope)
)

headers = {
    'Content-Type': "application/x-www-form-urlencoded",
    'Cache-Control': "no-cache"
}

response = requests.post(
    "https://developer.api.autodesk.com/authentication/v1/authenticate",
    data=payload,
    headers=headers
).json()

# get access_token from response
access_token = response['access_token']
print("Hub login successful")


# get all the projects from HQ
def get_project_info(command, proj_id):
    headers = {
        'Content-Type': "application",
        'scope': "account:read",
        'Authorization': "Bearer {at}".format(at=access_token),
        'Cache-Control': "no-cache"
    }

    _url = '{base_url}/{command}/{proj_id}'.format(base_url=BASE_URL_EU_HUB, command=command, proj_id=proj_id)
    response = requests.get(_url, headers=headers)
    return response.json()


print(len(all_project_IDs), " projects are being harvested")

# save file
timestamp = datetime.datetime.today().strftime('%Y%m%d_%H%M%S')


def save_file(name, data):
    filename = '{name}_{ts}.json'.format(name=name, ts=timestamp)
    with open(filename, 'w') as outfile:
        json.dump(data, outfile)
    print('{fn} saved'.format(fn=filename))


# get all project info from HQ
if harvest_info['project_info']:
    all_project_info = []
    for i, project_id in enumerate(all_project_HQs):
        all_project_info.append(get_project_info('projects', project_id))
        print('adding project info from {name}'.format(name=all_project_info[i]['name']))
        all_project_info[i]['field_project_id'] = all_project_IDs[i]
    save_file('Project_info', all_project_info)


# standard method of getting info from field
def get_standard_records(type_name, type_query, api_location, **parameters):
    all_records = []
    if 'ticket' in parameters:
        parameters['ticket'] = field_ticket
    for i, current_project_id in enumerate(all_project_IDs):
        if 'project_id' in parameters:
            parameters['project_id'] = current_project_id
        records = field_api_cmd(type_query, api_location, parameters)
        if records:
            for record in records:
                record['project_id'] = project_id
            print('Adding {} {} for project: {}'.format(len(records), type_name, all_project_names[i]))
            all_records.append(records)
        else:
            print('{} {} for project: {}'.format(len(records), type_name, all_project_names[i]))
    save_file(type_name + "_info", all_records)


# get contacts from field
if harvest_info['contacts']:
    get_standard_records("Contacts", "POST", "api/contacts", ticket="x", project_id="x")

if harvest_info['companies']:
    get_standard_records("Companies", "POST", "api/companies", ticket="x", project_id="x")

if harvest_info['issues']:
    get_standard_records("Companies", "POST", "api/get_issues", ticket="x", project_id="x")

if harvest_info['tasks']:
    get_standard_records("Companies", "POST", "api/get_tasks", ticket="x", project_id="x")

if harvest_info['equipment']:
    get_standard_records("Equipement", "POST", "api/get_equipment", ticket="x", project_id="x", details="all")

if harvest_info['areas']:
    get_standard_records("Areas", "POST", "api/areas", ticket="x", project_id="x")

if harvest_info['checklists']:
    get_standard_records("Checklists", "GET", "fieldapi/checklists/v1.json", ticket="x", project_id="x")


# get all Categories from field
if harvest_info['categories']:

    all_categories_normal = []
    all_categories_custom = []
    all_categories_equipment_sets = []

    for current_project_id in all_project_IDs:

        get_all_categories_from_project = field_api_cmd(
            "POST", "api/get_categories", {'ticket': field_ticket, 'project_id': current_project_id}
        )

        normal_categories = get_all_categories_from_project['categories']
        for normal_category in normal_categories:
            normal_category['project_id'] = current_project_id

        custom_categories = get_all_categories_from_project['customizable_categories']
        for custom_category in custom_categories:
            custom_category['project_id'] = current_project_id

        equipment_sets_categories = get_all_categories_from_project['equipment_category_status_sets']
        for equipment_sets_category in equipment_sets_categories:
            equipment_sets_categories['project_id'] = current_project_id

        print(
            "Adding {} Normal cat, {} Custom Cat and {} Equipment Status"
            .format(len(normal_categories), len(custom_categories), len(equipment_sets_categories))
        )

        all_categories_normal.append(normal_categories)
        all_categories_custom.append(custom_categories)
        all_categories_equipment_sets.append(equipment_sets_categories)

    save_file("Categories_normal_info", all_categories_normal)
    save_file("Categories_custom_info", all_categories_custom)
    save_file("Categories_Equipment_sets_info", all_categories_equipment_sets)


print("- - Done - -")
