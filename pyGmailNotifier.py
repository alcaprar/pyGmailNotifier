import time
import httplib2
import os

from apiclient import discovery, errors
import oauth2client
from oauth2client import client
from oauth2client import tools
from gi.repository import Notify
from gi.repository import Gtk
import webbrowser

#readonly scope
SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Gmail Inbox Notifier'
UPDATE_TIME = 15
userId='me'

newMessages = 0
messages = []

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None


def main():
    #inizializza il notificatore
    Notify.init(APPLICATION_NAME)
    #recupera le credenziali
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())


    flag = True
    while flag:
        try:
            service = discovery.build('gmail', 'v1', http=http)
            flag = False
        except httplib2.ServerNotFoundError, error:
    	    print 'An error occurred: %s' % error
            flag = True
            time.sleep(UPDATE_TIME)

    global userId

    while True:
        checkNewEmail(service, userId)
        time.sleep(UPDATE_TIME)

def checkNewEmail(service, user_id):
    print "START - checkNewEmail"
    global newMessages
    global messages

    messages = []
    #query per cercare i nuovi messaggi
    query="in:inbox is:unread"
    try:
        response = service.users().messages().list(userId=user_id,q=query).execute()
        if 'messages' in response:
            messages.extend(response['messages'])
        while 'nextPageToken' in response:
            page_token = response['nextPageToken']
            response = service.users().messages().list(userId=user_id, q=query,pageToken=page_token).execute()
            messages.extend(response['messages'])
        if len(messages) > newMessages :
            print "New message! Unread messages: " +str(len(messages))
            sendNotification(service,user_id, len(messages),messages)
        else:
            print "No new messages. Unread messages: " +str(len(messages))
        newMessages = len(messages)
    except errors.HttpError, error:
    	print 'An error occurred: %s' % error
    print "FINISH - checkNewEmail"

def getMessage(service, user_id, message_id):
    print"START - getMessage"
    try:
        message = service.users().messages().get(userId=user_id, id=message_id).execute()
        return message
    except errors.HttpError, error:
        print 'An error occurred: %s' % error
    print "FINISH - getMessage"

#ritorna le credenziali
#se sono gia in locale, controlla se sono valide.
#se non ci sono o non sono valide rifa il processo di autorizzazione
        
def get_credentials():
    print "START - get_credentials"
    #directory home
    home_dir = os.path.expanduser('~')
    #directory delle credenziali
    credential_dir = os.path.join(home_dir, '.credentials')
    #se non esiste la crea
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    #path al file delle credenziali
    credential_path = os.path.join(credential_dir,
                                   'gmail-quickstart.json')
    #prende le credenziali dal file
    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    #se non ci sono o sono invalide richiede l'auth
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatability with Python 2.6
            credentials = tools.run(flow, store)
        print 'Storing credentials to ' + credential_path
    else:
        print 'Credenziali gia presenti'
    print "FINISH - get_credentials"
    return credentials

def sendNotification(service,user_id,newMessages, messages):
    print newMessages
    print "START - sendNotification"
    titoloNotifica = str(newMessages)+ " nuov"+ ('o' if newMessages==1 else 'i')+" messaggi."
    testoNotifica = "LAST MESSAGE:\n"
    #compongo il testo della notifica
    ultimoMessaggio = getMessage(service, user_id, messages[0]['id'] )
    for campo in ultimoMessaggio['payload']['headers']:
        if campo['name'] == "From":
            sender = campo['value'].replace('>','').split('<')
        if campo['name'] == "Subject":
            subject = campo['value']
    testoNotifica = testoNotifica + "FROM: " +sender[0]+"\n"
    testoNotifica = testoNotifica + "EMAIL: "+sender[1] +"\n"
    testoNotifica = testoNotifica + "SUBJECT: "+ subject +"\n"
    testoNotifica = testoNotifica + "SNIPPET: " +ultimoMessaggio['snippet']
    print testoNotifica
    tipoNotifica = "notification-message-im"
    notifica = Notify.Notification.new(titoloNotifica, testoNotifica,tipoNotifica)
    notifica.set_category("email.arrived")
    notifica.set_timeout(20000)
    notifica.add_action("inbox","Open Inbox", callback_function)
    notifica.add_action("gmail","Open Gmail", callback_function)
    notifica.connect("closed",handle_closing)
    notifica.show()
    Gtk.main()
    print"FINISH - sendNotification"

def callback_function(notification=None, action=None, data=None):
     if action == "inbox":
         webbrowser.open("https://inbox.google.com",new=2,autoraise=True)
     elif action == "gmail":
         webbrowser.open("https://gmail.google.com",new=2,autoraise=True)
     Gtk.main_quit()

def handle_closing(notification):
    Gtk.main_quit()
    
if __name__ == '__main__':
    main()
