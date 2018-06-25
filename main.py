import requests
import json
import datetime
from ConfigParser import SafeConfigParser


#get info from config.ini
config = SafeConfigParser()
config.read('config.ini')

UserName = config.get("Field","username")
Password = config.get("Field","password")
Client_ID = config.get("HQ", "client_id")
Client_secret = config.get("HQ", "client_secret")
Account_ID = config.get("HQ", "account_id")


BaseURL_field = "https://bim360field.eu.autodesk.com/"
BaseURL_EU_Hub = "https://developer.api.autodesk.com/hq/v1/regions/eu/accounts/" + Account_ID


#control what info you want to download
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


"""Login in FIELD"""
url = BaseURL_field + "api/login"

payload = "username=" + UserName + "&password=" + Password
headers = {
    'content-type': "application/x-www-form-urlencoded",
    'Authorization':
    "Basic ZWRnYXIud2VzdGVyaG92ZW5AYXV0b2Rlc2suY29tOltudGVyUzc2",
    'Cache-Control': "no-cache",
}

response = json.loads(
    requests.request("POST", url, data=payload, headers=headers).text)

Field_ticket = response['ticket']
print "Field login succesful"
"""function for FIELD commands"""


def Field_Api_CMD(soort, command, payload):
	url = BaseURL_field + command

	headers = {
	    'content-type': "application/x-www-form-urlencoded",
	    'Cache-Control': "no-cache",
	}

	response = json.loads(requests.request(soort, url, data=payload, headers=headers).text)
	return response


#get all HQ & ID's from field
Grant_Type = "client_credentials"
Scope = "data:read account:read bucket:read"

All_Project_HQs = []
All_Project_IDs = []

#get all field projects from field
Get_Projects = Field_Api_CMD("GET", "api/projects", {'ticket': Field_ticket})

#extract project id's and hq id's
for i in range(len(Get_Projects)):
	current_project = Get_Projects[i]
	All_Project_HQs.append(current_project['hq_identifier'])
	All_Project_IDs.append(current_project['project_id'])

#Login in to HQ
payload = "client_id=" + Client_ID + "&client_secret=" + Client_secret + "&Account_id=" + Account_ID + "&grant_type=" + Grant_Type + "&scope=" + Scope

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

#get access_token from response
access_token = response['access_token']
print "Hub login succesfull"


#get all the projects from HQ
def Get_Project_Info(command, proj_id):
	headers = {
	    'Content-Type': "application",
	    'scope': "account:read",
	    'Authorization': "Bearer " + access_token,
	    'Cache-Control': "no-cache"
	}

	response = requests.request(
	    "GET", BaseURL_EU_Hub + "/" + command + "/" + proj_id, headers=headers)
	return json.loads(response.text)


print len(All_Project_IDs), " projects are being harvested"

#save file
timestamp = datetime.datetime.today().strftime('%Y%m%d_%H%M%S')
def SaveFile(Name, Data):
	filename = Name + "_" + timestamp + '.json'
	with open(filename, 'w') as outfile:
		json.dump(Data, outfile)
	print filename + " saved"


#get all project info from HQ
if harvest_info['project_info'] == True:
	All_Project_Info = []
	for i in range(len(All_Project_HQs)):
		Current_Project_ID = All_Project_HQs[i]
		All_Project_Info.append(
		    Get_Project_Info("projects", Current_Project_ID))
		print "adding project info from " + All_Project_Info[i]['name']
	SaveFile("Project_info", All_Project_Info)

#get contacts from field
if harvest_info['contacts'] == True:

	All_contacts = []

	for i in range(len(All_Project_IDs)):

		Current_Project_ID = All_Project_IDs[i]

		Get_Contacts_from_Project = Field_Api_CMD("POST", "api/contacts", {'ticket': Field_ticket,'project_id': Current_Project_ID})

		for i in range(len(Get_Contacts_from_Project)):

			Get_Contacts_from_Project[i]['project_id'] = Current_Project_ID

		print "Adding %s contacts" % len(Get_Contacts_from_Project)

		All_contacts.append(Get_Contacts_from_Project)

	SaveFile("Contact_info", All_contacts)

#get all companies from field
if harvest_info['companies'] == True:

	All_Companies = []

	for i in range(len(All_Project_IDs)):

		Current_Project_ID = All_Project_IDs[i]

		Get_Companies_from_Project = Field_Api_CMD("POST", "api/companies", {'ticket': Field_ticket,'project_id': Current_Project_ID})

		for i in range(len(Get_Companies_from_Project)):

			Get_Companies_from_Project[i]['project_id'] = Current_Project_ID

		print "Adding %s companies" % len(Get_Companies_from_Project)

		All_Companies.append(Get_Companies_from_Project)

	SaveFile("Companie_info", All_Companies)

#get all issues from field
if harvest_info['issues'] == True:

	All_Issues = []

	for i in range(len(All_Project_IDs)):

		Current_Project_ID = All_Project_IDs[i]

		Get_Issues_from_Project = Field_Api_CMD("POST", "api/get_issues", {'ticket': Field_ticket,'project_id': Current_Project_ID})

		for i in range(len(Get_Issues_from_Project)):

			Get_Issues_from_Project[i]['project_id'] = Current_Project_ID

		print "Adding %s Issues" % len(Get_Issues_from_Project)

		All_Issues.append(Get_Issues_from_Project)

	SaveFile("Issues_info", All_Issues)

#get all Tasks from field
if harvest_info['tasks'] == True:

	All_Tasks = []

	for i in range(len(All_Project_IDs)):

		Current_Project_ID = All_Project_IDs[i]

		Get_Tasks_from_Project = Field_Api_CMD("POST", "api/get_tasks", {'ticket': Field_ticket,'project_id': Current_Project_ID})

		print "Adding %s Tasks" % len(Get_Tasks_from_Project)

		All_Tasks.append(Get_Tasks_from_Project)

	SaveFile("Tasks_info", All_Tasks)

#get all Equipement from field
if harvest_info['equipment'] == True:

	All_Equipment = []

	for i in range(len(All_Project_IDs)):

		Current_Project_ID = All_Project_IDs[i]

		Get_Equipment_from_Project = Field_Api_CMD("POST", "api/get_equipment", {'ticket': Field_ticket,'project_id': Current_Project_ID,'details': "all"})

		for i in range(len(Get_Equipment_from_Project)):

			Get_Equipment_from_Project[i]['project_id'] = Current_Project_ID

		print "Adding %s Equipment" % len(Get_Equipment_from_Project)

		All_Equipment.append(Get_Equipment_from_Project)

	SaveFile("Equipment_info", All_Equipment)

#get all Areas from field
if harvest_info['areas'] == True:

	All_Areas = []

	for i in range(len(All_Project_IDs)):

		Current_Project_ID = All_Project_IDs[i]

		Get_Areas_from_Project = Field_Api_CMD("POST", "api/areas", {'ticket': Field_ticket,'project_id': Current_Project_ID})

		for i in range(len(Get_Areas_from_Project)):

			Get_Areas_from_Project[i]['project_id'] = Current_Project_ID

		print "Adding %s Areas" % len(Get_Areas_from_Project)

		All_Areas.append(Get_Areas_from_Project)

	SaveFile("Areas_info", All_Areas)

#get all Categories from field
if harvest_info['categories'] == True:

	All_Categories_Normal = []
	All_Categories_Custom = []
	All_Categories_EquipmentSets = []

	for i in range(len(All_Project_IDs)):

		Current_Project_ID = All_Project_IDs[i]

		Get_All_Categories_from_Project = Field_Api_CMD("POST", "api/get_categories", {'ticket': Field_ticket,'project_id': Current_Project_ID})

		Get_Categories_Normal = Get_All_Categories_from_Project['categories']
		for i in range(len(Get_Categories_Normal)):
			Get_Categories_Normal[i]['project_id'] = Current_Project_ID
		
		Get_Categories_Custom = Get_All_Categories_from_Project['customizable_categories']
		for i in range(len(Get_Categories_Custom)):
			Get_Categories_Custom[i]['project_id'] = Current_Project_ID
		
		Get_Categories_EquipmentSets = Get_All_Categories_from_Project['equipment_category_status_sets']
		for i in range(len(Get_Categories_EquipmentSets)):
			Get_Categories_EquipmentSets[i]['project_id'] = Current_Project_ID

		print "Adding %s Normal cat, %s Custom Cat and %s Equipment Status" % (len(Get_Categories_Normal),len(Get_Categories_Custom),len(Get_Categories_EquipmentSets))

		All_Categories_Normal.append(Get_Categories_Normal)
		All_Categories_Custom.append(Get_Categories_Custom)
		All_Categories_EquipmentSets.append(Get_Categories_EquipmentSets)

	SaveFile("Categories_normal_info",All_Categories_Normal)
	SaveFile("Categories_custom_info",All_Categories_Custom)
	SaveFile("Categories_Equipment_sets_info",All_Categories_EquipmentSets)

#get all Checklists from field
if harvest_info['checklists'] == True:

	All_Checklists = []

	for i in range(len(All_Project_IDs)):

		Current_Project_ID = All_Project_IDs[i]

		Get_Checklists_from_Project = Field_Api_CMD("GET", "fieldapi/checklists/v1.json", {'ticket': Field_ticket,'project_id': Current_Project_ID})

		for i in range(len(Get_Checklists_from_Project)):

			Get_Checklists_from_Project[i]['project_id'] = Current_Project_ID

		print "Adding %s Checklists" % len(Get_Checklists_from_Project)

		All_Checklists.append(Get_Checklists_from_Project)

	SaveFile("Checklists_info", All_Checklists)






print "- - Done - -"
