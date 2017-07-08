__author__ = "Hayden Elza"
__email__ = "hayden.elza@gmail.com"


from apiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import argparse
import PyRSS2Gen
import datetime
import base64
import email

# User variables
user_id = "uwsg.gis.software@gmail.com"
label_name = "Label_5"
content_path = "C:/Apache24/htdocs/updates/index.html"
feed_path = "C:/Apache24/htdocs/updates/feed.xml"

# Limit scope to read only
SCOPES = "https://www.googleapis.com/auth/gmail.readonly"
CLIENT_SECRET = "client_secret.json"

# Store access token
store = file.Storage('storage.json')
# Get valid access token to make api calls
credz = store.get()
# If credentials are missing or invalid, create and run oauth flow
if not credz or credz.invalid:
	flow = client.flow_from_clientsecrets(CLIENT_SECRET, SCOPES)
	flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
	credz = tools.run_flow(flow, store, flags)

# Create gmail service endpoint for api
GMAIL = build('gmail', 'v1', http=credz.authorize(Http()))

# Get user's threads
threads = GMAIL.users().threads().list(userId=user_id).execute().get('threads', [])

# Initiate temporary storage variables
rss_items = []
html_string = '<!DOCTYPE html>\n<html>\n<head>\n<meta charset="UTF-8">\n<title>Release and Security Feed</title>\n<style>.message{max-height: 500px;overflow: auto;border: solid 1px;padding: 10px;}</style>\n</head>\n<body>\n<h1>University of Wisconsin - Madison Sea Grant Institute GIS Software Release and Security Feed</h1>\n<h3>Feed to track releases and security updates for software used in the Sea Grant\'s GIS stack.</h3>\n<br>\n<em>Last updated: ' + str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M')) + "</em>\n<br>\n"

# Iterate through threads
for thread in threads:

	# Get thread data
	tdata = GMAIL.users().threads().get(userId=user_id, id=thread['id'], format="full").execute()
	print tdata

	# Only look at lable 5 (Release and Security)
	if not any( label == label_name for label in tdata['messages'][0]['labelIds']): continue

	# Get number of messages, the first message, thread id, and date
	nmsgs = len(tdata['messages'])
	msg = tdata['messages'][0]['payload']
	uid = tdata['messages'][0]['id']
	internalDate = tdata['messages'][0]['internalDate']

	# Initiate variables
	mailing_list = ""
	subject = ""
	author = ""
	date = ""

	# Iterate through headers to populate variables
	for header in msg['headers']:

		# Check for needed headers
		if header['name'] == "List-Post": mailing_list = header['value'].partition(':')[-1].partition('>')[0]
		if header['name'] == "Subject": subject = header['value']
		if header['name'] == "From": author = header['value']
		if header['name'] == "Date": date = header['value']

		# Break once we have everything we need
		if subject and mailing_list and author:

			# Generate rss item for thread
			rss_items.append(
				PyRSS2Gen.RSSItem(
					title = subject,
					link = "http://maps.aqua.wisc.edu/updates/#" + str(uid),
					description = '%s (%d messages in thread)\n<a href="http://maps.aqua.wisc.edu/updates/#%s">Link to email.</a>' % (mailing_list,nmsgs,uid),
					guid = PyRSS2Gen.Guid(uid),
					pubDate = datetime.datetime.fromtimestamp(int(internalDate[:-3])).strftime('%Y-%m-%d %H:%M:%S')
				)
			)

			# Break because we have all the headers we need
			break

	# Add anchor for thread
	html_string += '<hr><br><br><h3 id="' + str(uid) + '">Tread: ' + str(uid) + '</h3></a>\n<em>' + date + '</em>\n'

	# Interate through messages in thread
	for i in xrange(nmsgs):

		# Get message id
		msg_id = tdata['messages'][i]['id']

		# Retrieve message from gmail
		message = GMAIL.users().messages().get(userId=user_id, id=msg_id, format='raw').execute()

		# Try to write the message to file, if it fails gracefully report in content
		try:

			# Decode message
			message_decoded = email.message_from_string(base64.urlsafe_b64decode(message['raw'].encode('ASCII')))

			# Check if multipart message
			if message_decoded.is_multipart():

				# Get each payload
				for payload in message_decoded.get_payload():
					payload = payload.get_payload()
			else:

				# Get payload
				payload = message_decoded.get_payload()

			# Write message to file	
			msg_string = "<h4>" + subject + "</h4><p>List:\t\t" + mailing_list + "</p>\n<p>From:\t\t" + author + '</p>\n<p class="message">' + payload.replace("\n","\n<br>\n") + "</p>\n<br><br><br><br>\n"
		
		except: msg_string = "<h4>" + subject + "</h4><p>List:\t\t" + mailing_list + "</p>\n<p>From:\t\t" + author + "</p>\n<em>Could not load message. See uwsg.gis.software@gmail.com for message.</em>\n<br><br><br><br>\n"
		
		# Add message to the html storage variable
		html_string += msg_string


# Write rss feed to xml
rss = PyRSS2Gen.RSS2(
	title = "University of Wisconsin - Madison GIS Software Release and Security Feed",
	link = "http://maps.aqua.wisc.edu/updates",
	description = 	"Feed to track releases and sucurity updates for software used in Seagrant's GIS stack.",
	lastBuildDate = datetime.datetime.now(),
	items = rss_items
)
rss.write_xml(open(feed_path, "w"))

# Finish html_string and write to file
html_string += "</div>\n</body>\n</html>"
with open(content_path, "wb") as html_file: html_file.write(html_string.encode('ascii', 'ignore'))