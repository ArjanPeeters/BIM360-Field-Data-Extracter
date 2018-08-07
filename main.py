from __future__ import print_function
import requests
import json
import datetime
import os
import ssl
import logging
print(ssl.OPENSSL_VERSION)
try:
  from ConfigParser import SafeConfigParser
except ImportError:
  from configparser import SafeConfigParser

# get info from config.ini
config = SafeConfigParser()
try:
  config.read('config.ini')
except Exception:
  print("error reading config.ini")

timestamp = datetime.datetime.today().strftime('%Y%m%d_%H%M%S')
save_path = config.get("paths", "main_path")
backup_path = config.get("paths", "backup_path")
if not os.path.isdir(save_path):
  logger.debug("Created directory: {}".format(save_path))
  os.makedirs(backup_path)
backup_path_ts = os.path.join(backup_path,timestamp)
if not os.path.isdir(backup_path_ts):
  os.makedirs(backup_path_ts)

logging.basicConfig(filename='{bpt}/_harvest_{ts}.log'.format(bpt=backup_path_ts,ts=timestamp),level=logging.INFO,filemode='w',format='%(asctime)s [%(levelname)-12.12s] %(message)s',datefmt='%Y-%m-%d,%H:%M:%S')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.formatter('%(asctime)s -> %(message)s',datefmt='%Y-%m-%d,%H:%M:%S')
fh = logging.FileHandler('{bpt}/harvest_{ts}.log'.format(bpt=backup_path_ts,ts=timestamp))
fh.setLevel(logging.DEBUG)
fh.formatter('%(asctime)s [%(levelname)-8.8s] %(message)s',datefmt='%Y-%m-%d,%H:%M:%S')
logger.addHandler(fh)
logger.addHandler(ch)

username = config.get("Field", "username")
logger.debug('username={}'.format(username))
password = config.get("Field", "password")
logger.debug('password={0}{1}'.format(password[:1],(len(password)-1)*"*"))
client_id = config.get("HQ", "client_id")
logger.debug('client id={}'.format(client_id))
client_secret = config.get("HQ", "client_secret")
logger.debug('client_secret={0}{1}'.format(client_secret[:1],(len(client_secret)-1)*"*"))
account_id = config.get("HQ", "account_id")
logger.debug('account_id={}'.format(account_id))

if config.get("Server", "location") == "US":
  base_url_field = "https://bim360field.autodesk.com/"
  base_url_hub = "https://developer.api.autodesk.com/hq/v1/accounts/{0}".format(account_id)
else:
  base_url_field = "https://bim360field.{0}.autodesk.com/".format(config.get("Server", "location"))
  base_url_hub = "https://developer.api.autodesk.com/hq/v1/regions/{1}/accounts/{0}".format(account_id,config.get("Server", "location"))
logger.debug('base_url_hub={}'.format(base_url_hub))
logger.debug('base_url_field={}'.format(base_url_field))




# save file function
def double_save_file(name, data):
  """
  Checks if directories excist and makes them if not
  double saves the files for use in PowerBI
  """
  filename = '{name}.json'.format(name=name, ts=timestamp)
  backupname = '{name}_{ts}.json'.format(name=name, ts=timestamp)
  save_file = os.path.join(save_path,filename)
  backup_path_ts = os.path.join(backup_path,timestamp)
  if not os.path.isdir(backup_path_ts):
    os.makedirs(backup_path_ts)
  backup_file = os.path.join(backup_path_ts,backupname)
  with open(save_file, 'w') as outfile:
    json.dump(data, outfile)
  logger.info('{fn} saved'.format(fn=filename))
  with open(backup_file, 'w') as outbackup:
    json.dump(data, outbackup)
  logger.info('{fn} saved'.format(fn=backupname))

# ignore projects in this list
ignore_projects = config.get('ignore_projects','name')
logger.info('ignoring projects: '.format(ignore_projects))

# control what info you want to download
harvest_info = {}
logger.info("Downloading:")
for name in config.options('download'):
  harvest_info[name] = config.getboolean('download',name)
  logger.info("{:20}:{}".format(name,config.getboolean('download',name)))


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
        "POST","{0}/api/login".format(base_url_field),
        data = {
          "username": username,
          "password": password
        },
        headers = {
          'content-type': "application/x-www-form-urlencoded",
          'Cache-Control': "no-cache"
        }).text)['ticket']
    logger.debug("Logging into {0}".format(base_url_field))
    logger.info('Field ticket: {0}'.format(field_ticket))

  url = '{base_url}{command}'.format(base_url=base_url_field, command=command)

  headers = {
    'content-type': "application/x-www-form-urlencoded",
    'Cache-Control': "no-cache",
  }

  payload['ticket'] = field_ticket

  logger.debug("FIELD Request= soort:{soort}, url:{url}".format(soort=soort,url=url))
  logger.debug("data:{}".format(payload))
  logger.debug("headers:{}".format(headers))

  response = requests.request(soort, url, data=payload, headers=headers).json()

  logger.debug("FIELD returned: {} records".format(len(response)))
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
    logger.info("Hub login succesfull: {0}...{1}".format(access_token[:5],access_token[-5:]))

  payload['scope'] = "account:read"
  payload['grant_type'] = 'client_credentials'

  headers['Content-Type'] = "application"
  headers['Authorization'] = "Bearer {0}".format(access_token)

  _url = '{base_url}/{command}'.format(base_url=base_url_hub, command=command)

  logger.debug("HQ Request= soort:{soort}, url:{url}".format(soort=soort,url=_url))
  logger.debug("params:{}".format(payload))
  logger.debug("headers:{}".format(headers))

  response = requests.request(
    soort,
    _url,
    params=payload,
    headers=headers).json()

  logger.debug("HQ returned: {} records".format(len(response)))

  return response



all_project_hqs = []
all_project_ids = []
all_project_names = []

# get all field projects from field
get_projects = field_api_cmd("GET", "api/projects",{})

# extract project id's and hq id's
for i in get_projects:
  if i['name'] not in ignore_projects:
    all_project_hqs.append(i['hq_identifier'])
    all_project_ids.append(i['project_id'])
    all_project_names.append(i['name'])
    logger.debug("Adding project, name: {0}, ID: {1}, HQ: {2}".format(i['name'],i['project_id'],i['hq_identifier']))

logger.info("{} projects are harvested".format(len(all_project_ids)))

# get all project info from HQ
if harvest_info['project_info']:
  all_project_info = []
  for i, project_id in enumerate(all_project_hqs):
    all_project_info.append(bim360_api_cmd('GET','projects/{hq}'.format(hq=project_id)))
    logger.info('adding project info from {name}'.format(name=all_project_info[i]['name']))
    all_project_info[i]['field_project_id'] = all_project_ids[i]
  double_save_file('Project_info', all_project_info)


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
      logger.info('Adding {} {} for project: {}'.format(len(records), type_name, all_project_names[i]))
      all_records.append(records)
    else:
      logger.info('{} {} for project: {}'.format(len(records), type_name, all_project_names[i]))
  double_save_file("{}_info".format(type_name), all_records)


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
  logger.info('Adding {} {}'.format(len(all_records),type_name))
  double_save_file('{}_info'.format(type_name), all_records)

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

    logger.info(
        "Adding {0} Normal cat, {1} Custom Cat and {2} Equipment Status"
        .format(len(normal_categories), len(custom_categories), len(equipment_sets_categories))
    )

    all_categories_normal.append(normal_categories)
    all_categories_custom.append(custom_categories)
    all_categories_equipment_sets.append(equipment_sets_categories)

  double_save_file("Categories_normal_info", all_categories_normal)
  double_save_file("Categories_custom_info", all_categories_custom)
  double_save_file("Categories_Equipment_sets_info", all_categories_equipment_sets)


logger.info("- - Done - -")
