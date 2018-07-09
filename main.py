import requests
import json
import datetime
from ConfigParser import SafeConfigParser


# get info from config.ini
config = SafeConfigParser()
config.read('config.ini')

username = config.get("Field", "username")
password = config.get("Field", "password")
client_id = config.get("HQ", "client_id")
client_secret = config.get("HQ", "client_secret")
account_id = config.get("HQ", "account_id")


base_url_field = "https://bim360field.eu.autodesk.com/"
base_url_eu_hub = "https://developer.api.autodesk.com/hq/v1/regions/eu/accounts/" + account_id

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
url = base_url_field + "api/login"

payload = "username=" + username + "&password=" + password
headers = {
    'content-type': "application/x-www-form-urlencoded",
    'Authorization':
    "Basic ZWRnYXIud2VzdGVyaG92ZW5AYXV0b2Rlc2suY29tOltudGVyUzc2",
    'Cache-Control': "no-cache",
}

response = json.loads(
    requests.request("POST", url, data=payload, headers=headers).text)

Field_ticket = response['ticket']
print "Field login successful"


# function for FIELD commands
def field_api_cmd(soort, command, payload):
    url = base_url_field + command
    headers = {
        'content-type': "application/x-www-form-urlencoded",
        'Cache-Control': "no-cache",
    }

    response = json.loads(requests.request(soort, url, data=payload, headers=headers).text)
    return response


# get all HQ & ID's from field
grant_type = "client_credentials"
scope = "data:read account:read bucket:read"

all_project_HQs = []
all_project_IDs = []
all_project_names = []

# get all field projects from field
get_projects = field_api_cmd("GET", "api/projects", {'ticket': Field_ticket})

# extract project id's and hq id's
for i in range(len(get_projects)):
    current_project = get_projects[i]
    if current_project['name'] not in ignore_projects:
        all_project_HQs.append(current_project['hq_identifier'])
        all_project_IDs.append(current_project['project_id'])
        all_project_names.append(current_project['name'])

# Login in to HQ
payload = "client_id=" + client_id + "&client_secret=" + client_secret + "&Account_id=" + account_id + "&grant_type=" + grant_type + "&scope=" + scope

headers = {
    'Content-Type': "application/x-www-form-urlencoded",
    'Cache-Control': "no-cache"
}

response = json.loads(
    requests.request(
        "POST",
        "https://developer.api.autodesk.com/authentication/v1/authenticate",
        data=payload,
        headers=headers).text)

# get access_token from response
access_token = response['access_token']
print "Hub login successful"


# get all the projects from HQ
def get_project_info(command, proj_id):
    headers = {
        'Content-Type': "application",
        'scope': "account:read",
        'Authorization': "Bearer " + access_token,
        'Cache-Control': "no-cache"
    }

    response = requests.request(
        "GET", base_url_eu_hub + "/" + command + "/" + proj_id, headers=headers)
    return json.loads(response.text)


print len(all_project_IDs), " projects are being harvested"

# save file
timestamp = datetime.datetime.today().strftime('%Y%m%d_%H%M%S')


def save_file(name, data):
    filename = name + "_" + timestamp + '.json'
    with open(filename, 'w') as outfile:
        json.dump(data, outfile)
    print filename + " saved"


# get all project info from HQ
if harvest_info['project_info'] == True:
    all_project_info = []
    for i in range(len(all_project_HQs)):
        current_project_id = all_project_HQs[i]
        all_project_info.append(
            get_project_info("projects", current_project_id))
        print "adding project info from " + all_project_info[i]['name']
        all_project_info[i]['field_project_id'] = all_project_IDs[i]
    save_file("Project_info", all_project_info)


# standard methode of getting info from field
def get_standard_records(type_name, type_query, api_location, **parameters):
    all_records = []
    if 'ticket' in parameters:
        parameters['ticket']=Field_ticket
    for i in range(len(all_project_IDs)):
        current_project_id = all_project_IDs[i]
        if 'project_id' in parameters:
            parameters['project_id'] = current_project_id
        get_records_from_project = field_api_cmd(type_query, api_location, parameters)
        count_records = len(get_records_from_project)
        if count_records > 0:
            for p in range(count_records):
                get_records_from_project[p]['project_id'] = current_project_id
            print "Adding %s %s for project: %s" % (count_records, type_name, all_project_names[i])
            all_records.append(get_records_from_project)
        else:
            print "%s %s for project: %s" % (count_records, type_name, all_project_names[i])
    save_file(type_name + "_info", all_records)


# get contacts from field
if harvest_info['contacts'] == True:
    get_standard_records("Contacts", "POST", "api/contacts", ticket="x", project_id="x")

if harvest_info['companies'] == True:
    get_standard_records("Companies", "POST", "api/companies", ticket="x", project_id="x")

if harvest_info['issues'] == True:
    get_standard_records("Companies", "POST", "api/get_issues", ticket="x", project_id="x")

if harvest_info['tasks'] == True:
    get_standard_records("Companies", "POST", "api/get_tasks", ticket="x", project_id="x")

if harvest_info['equipment'] == True:
    get_standard_records("Equipement", "POST", "api/get_equipment", ticket="x", project_id="x", details="all")

if harvest_info['areas'] == True:
    get_standard_records("Areas", "POST", "api/areas", ticket="x", project_id="x")

if harvest_info['checklists'] == True:
    get_standard_records("Checklists", "GET", "fieldapi/checklists/v1.json", ticket="x", project_id="x")


# get all Categories from field
if harvest_info['categories'] == True:

    all_categories_normal = []
    all_categories_custom = []
    all_categories_equipment_sets = []

    for i in range(len(all_project_IDs)):

        current_project_id = all_project_IDs[i]

        get_all_categories_from_project = field_api_cmd("POST", "api/get_categories", {'ticket': Field_ticket, 'project_id': current_project_id})

        get_categories_normal = get_all_categories_from_project['categories']
        for i in range(len(get_categories_normal)):
            get_categories_normal[i]['project_id'] = current_project_id

        get_categories_custom = get_all_categories_from_project['customizable_categories']
        for i in range(len(get_categories_custom)):
            get_categories_custom[i]['project_id'] = current_project_id

        get_categories_equipment_sets = get_all_categories_from_project['equipment_category_status_sets']
        for i in range(len(get_categories_equipment_sets)):
            get_categories_equipment_sets[i]['project_id'] = current_project_id

        print "Adding %s Normal cat, %s Custom Cat and %s Equipment Status" % (len(get_categories_normal), len(get_categories_custom), len(get_categories_equipment_sets))

        all_categories_normal.append(get_categories_normal)
        all_categories_custom.append(get_categories_custom)
        all_categories_equipment_sets.append(get_categories_equipment_sets)

    save_file("Categories_normal_info", all_categories_normal)
    save_file("Categories_custom_info", all_categories_custom)
    save_file("Categories_Equipment_sets_info", all_categories_equipment_sets)


print "- - Done - -"
