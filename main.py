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
BASE_URL_EU_HUB = "https://developer.api.autodesk.com/hq/v1/regions/eu/accounts/{0}".format(account_id)

# ignore projects in this list
ignore_projects = config.get('ignore_projects','name')

# control what info you want to download
harvest_info = {}
print("Downloading:")
for name in config.options('download'):
  harvest_info[name] = config.getboolean('download',name)
  print("{:20}:{}".format(name,config.getboolean('download',name)))


# function for FIELD commands
field_ticket = ""
def field_api_cmd(soort, command, payload):
  """
  This function is for calling all commands from the Field cloud
  It will check first if there is a ticket available otherwise it will login and get a ticket first.
  When calling the function you can give it the various payload options that are documented by Autodesk
  """
  global field_ticket
  if field_ticket == "":
    #if not logedin yet, login
    field_ticket = json.loads(
      requests.request(
        "POST","https://bim360field.eu.autodesk.com/api/login",
        data = {
          "username": username,
          "password": password
        },
        headers = {
          'content-type': "application/x-www-form-urlencoded",
          'Cache-Control': "no-cache"
        }).text)['ticket']
    print ('Field ticket: {0}'.format(field_ticket))

  url = '{base_url}{command}'.format(base_url=BASE_URL_FIELD, command=command)

  headers = {
      'content-type': "application/x-www-form-urlencoded",
      'Cache-Control': "no-cache",
  }

  payload['ticket'] = field_ticket

  response = requests.request(soort, url, data=payload, headers=headers).json()
  return response


access_token = ""
#Application for HQ commands
def bim360_api_cmd(soort, command, **payload):
  """
  This function is for calling all commands from the HQ cloud
  It will check first if there is a token available otherwise it will login and get a token first.
  When calling the function you can give it the various payload options that are documented by Autodesk
  don't forget to check if a (page)size and (page)offset are needed. See pagination documentation
  """
  headers = {}
  global access_token
  if access_token == "":
    # if access_token is empty, login to HQ en get access_token
    access_token = json.loads(
      requests.request(
        "POST",
        "https://developer.api.autodesk.com/authentication/v1/authenticate",
        data = {
          "client_id": client_id,
          "client_secret": client_secret,
          "Account_id": account_id,
          'scope': "data:read account:read bucket:read",
          'grant_type': 'client_credentials'
        },
        headers = {
          'Content-Type': "application/x-www-form-urlencoded",
          'Cache-Control': "no-cache"
        }).text)['access_token']
    print("Hub login succesfull: {0}...{1}".format(access_token[:5],access_token[-5:]))

  payload['scope'] = "account:read"
  payload['grant_type'] = 'client_credentials'

  headers['Content-Type'] = "application"
  headers['Authorization'] = "Bearer {0}".format(access_token)

  _url = '{base_url}/{command}'.format(base_url=BASE_URL_EU_HUB, command=command)

  response = requests.request(
    soort,
    _url,
    params=payload,
    headers=headers).json()
  return response



all_project_hqs = []
all_project_ids = []
all_project_names = []

# get all field projects from field
get_projects = field_api_cmd("GET", "api/projects",{})

# extract project id's and hq id's
for i in range(len(get_projects)):
  current_project = get_projects[i]
  if current_project['name'] not in ignore_projects:
    all_project_hqs.append(current_project['hq_identifier'])
    all_project_ids.append(current_project['project_id'])
    all_project_names.append(current_project['name'])

print(len(all_project_ids), " projects are being harvested")

# save file function
timestamp = datetime.datetime.today().strftime('%Y%m%d_%H%M%S')
def save_file(name, data):
  filename = '{name}_{ts}.json'.format(name=name, ts=timestamp)
  with open(filename, 'w') as outfile:
    json.dump(data, outfile)
  print('{fn} saved'.format(fn=filename))


# get all project info from HQ
if harvest_info['project_info']:
  all_project_info = []
  for i, project_id in enumerate(all_project_hqs):
    all_project_info.append(bim360_api_cmd('GET','projects/{hq}'.format(hq=project_id)))
    print('adding project info from {name}'.format(name=all_project_info[i]['name']))
    all_project_info[i]['field_project_id'] = all_project_ids[i]
  save_file('Project_info', all_project_info)


# standard function for getting info from field
def get_standard_field_records(type_name, type_query, api_location, **parameters):
  all_records = []
  for i, current_project_id in enumerate(all_project_ids):
    if 'project_id' in parameters:
      parameters['project_id'] = current_project_id
    records = field_api_cmd(type_query, api_location, parameters)
    if records:
      for record in records:
        record['project_id'] = current_project_id
      print('Adding {} {} for project: {}'.format(len(records), type_name, all_project_names[i]))
      all_records.append(records)
    else:
      print('{} {} for project: {}'.format(len(records), type_name, all_project_names[i]))
  save_file("{}_info".format(type_name), all_records)


# standard function for getting info from HQ
def get_standard_hq_records(type_name, type_query, api_location, limitandresponse=10):
  all_records = []
  limit = limitandresponse
  response = limitandresponse
  offset = 0
  while limit == response:
    get_records = bim360_api_cmd(type_query,api_location,limit=limit,offset=offset,)
    for i in range(len(get_records)):
      all_records.append(get_records[i])
    offset += limit
    response = len(get_records)
  print('Adding {} {}'.format(len(all_records),type_name))
  save_file('{}_info'.format(type_name), all_records)

# get contacts from field
if harvest_info['users']:
  get_standard_hq_records("Users", "GET", "users", 100)

if harvest_info['companies']:
  get_standard_hq_records("Companies", "GET", "companies", 10)

if harvest_info['issues']:
  get_standard_field_records("Issues", "POST", "api/get_issues", project_id="x")

if harvest_info['tasks']:
  get_standard_field_records("Tasks", "POST", "api/get_tasks", project_id="x")

if harvest_info['equipment']:
  get_standard_field_records("Equipement", "POST", "api/get_equipment",project_id="x", details="all")

if harvest_info['areas']:
  get_standard_field_records("Areas", "POST", "api/areas", project_id="x")

if harvest_info['checklists']:
  get_standard_field_records("Checklists", "GET", "fieldapi/checklists/v1.json", project_id="x")

if harvest_info['project_contacts']:
  get_standard_field_records("Project_Contacts", "POST", "fieldapi/admin/v1/users", project_id="x")

if harvest_info['project_companies']:
  get_standard_field_records("Project_Companies", "POST", "fieldapi/admin/v1/companies", project_id="x")


# get all Categories from field
if harvest_info['categories']:

  all_categories_normal = []
  all_categories_custom = []
  all_categories_equipment_sets = []

  for current_project_id in all_project_ids:

    get_all_categories_from_project = field_api_cmd(
        "POST",
        "api/get_categories",
        {'project_id': current_project_id}
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
        "Adding {0} Normal cat, {1} Custom Cat and {2} Equipment Status"
        .format(len(normal_categories), len(custom_categories), len(equipment_sets_categories))
    )

    all_categories_normal.append(normal_categories)
    all_categories_custom.append(custom_categories)
    all_categories_equipment_sets.append(equipment_sets_categories)

  save_file("Categories_normal_info", all_categories_normal)
  save_file("Categories_custom_info", all_categories_custom)
  save_file("Categories_Equipment_sets_info", all_categories_equipment_sets)


print("- - Done - -")
