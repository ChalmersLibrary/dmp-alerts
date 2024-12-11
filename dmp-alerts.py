#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import sys
from dotenv import load_dotenv
import smtplib
from email.utils import formataddr
from email.message import EmailMessage
import os
from datetime import datetime
import csv

# Script for monitoring new and updated DMPs and creating alerts for relevant stakeholders.
# urban.andersson@chalmers.se

# Configuration
load_dotenv()

# Other
d = datetime.now()
current_date = d.strftime("%Y-%m-%dT%H:%M:%S.%f")
current_date_short = d.strftime("%Y-%m-%d")

# Read last run timestamp from file
with open(os.getenv("LASTRUN_FILE"), 'r') as file:
    lastrun_date = file.read().rstrip()
# Debug, test
# lastrun_date = '2021-09-01T00:00:00'

# API queries (Lucene syntax)
all_dmps_created_since_date_q = 'dmp.created:[' + lastrun_date + ' TO *]+OR+dmp.modified:[' + lastrun_date + ' TO *]'

# Request data from DMP API as string
api_auth = 'Bearer ' + str(os.getenv("DMP_API_AUTH_KEY"))
headers = {'Accept': 'application/json',
           'Authorization': api_auth,
           'include-metadata': 'True'}

# DO NOT use verify=False in production!!
dsw_getallnewurl = os.getenv("DMP_API_ENDPOINT") + all_dmps_created_since_date_q
data = requests.get(url=dsw_getallnewurl, headers=headers, verify=True).text

# convert string to Json
data = json.loads(data)
# print(data)

if data:
    for i in data['items']:
        send_new_alert = 1
        send_pers_alert = 1
        send_ethical_alert = 1
        print('title:' + str(i['dmp']['title']))
        dsw_title = i['dmp']['title']
        dsw_id = i['dmp']['dmp_id']['identifier']
        if 'created' in i['dmp']:
            dsw_created = i['dmp']['created']
            dsw_created_date = dsw_created[0:10]
        else:
            dsw_created_date = current_date_short
        if 'modified' in i['dmp']:
            dsw_modified = i['dmp']['modified']
            dsw_modified_date = dsw_modified[0:10]
        else:
            dsw_modified_date = current_date_short
        dsw_creator = ''
        if 'dmp_owner' in i['metadata']:
            if 'name' in i['metadata']['dmp_owner']:
                dsw_creator = i['metadata']['dmp_owner']['name']
            else:
                dsw_creator = '(okänd)'
        else:
            dsw_creator = '(okänd)'

        # if 'contact' in i['dmp']:
        #    dsw_creator = i['dmp']['contact']['name']
        # else:
        #    dsw_creator = '(okänd)'

        # Check if alert has already been sent
        with open(os.getenv("LOG_RUNS_FILE"), mode='r', ) as infile:
            for row in csv.reader(infile, dialect='excel-tab'):
                if row[0] == 'NEW_ALERT' and row[1] == dsw_id:
                    print('Alert has already been sent, ' + row[2])
                    send_new_alert = 0
                elif row[0] == 'PERSONAL_DATA_ALERT' and row[1] == dsw_id:
                    print('Personal data alert has already been sent, ' + row[2])
                    send_pers_alert = 0
                else:
                    continue

        # Check if some mandatory fields are present. There should at least be a title and a research project.
        if 'title' not in i['dmp']:
            send_new_alert = 0
            send_pers_alert = 0
            send_ethical_alert = 0
        if 'project' not in i['dmp']:
            send_new_alert = 0
            send_pers_alert = 0
            send_ethical_alert = 0
        if 'project' in i['dmp'] and len(i['dmp']['project']) > 0:
            if 'title' not in i['dmp']['project'][0]:
                send_new_alert = 0
                send_pers_alert = 0
                send_ethical_alert = 0

        # Send new dmp alert
        if send_new_alert == 1:
            msg = EmailMessage()
            message = '<p>Hej!</p><p>En ny datahanteringsplan (' + dsw_title + ') har skapats av ' + dsw_creator + ': <br /><a href="' + dsw_id + '">' + dsw_id + '</a></p><p>Skapad: ' + dsw_created_date + '<br/>Senast uppdaterad: ' + dsw_modified_date + '</p><p>Med vänliga hälsningar,<br />Chalmers Data Stewardship Wizard</p>'
            msg['From'] = formataddr(('Chalmers DS Wizard', 'dsw-noreply@dsw.chalmers.se'))
            msg['To'] = formataddr(('Chalmers Data Office', os.getenv("NEW_DMP_RECIPIENT")))
            msg['Subject'] = '[Chalmers DSW] Ny datahanteringsplan!'
            msg.set_content(message, subtype='html')

            # send the e-mail
            try:
                server = smtplib.SMTP(os.getenv("SMTP_SERVER"), os.getenv("SMTP_PORT"))
                server.ehlo()
                server.starttls()
                server.login(os.getenv("SMTP_UID"), os.getenv("SMTP_PW"))
                server.send_message(msg)
                print('email was sent to ' + os.getenv("NEW_DMP_RECIPIENT"))
                with open(os.getenv("LOG_RUNS_FILE"), 'a') as lr:
                    lr.write('NEW_ALERT\t' + dsw_id + '\t' + current_date + '\t' + os.getenv("NEW_DMP_RECIPIENT") + '\n')
                server.quit()
            except:
                e = sys.exc_info()[0]
                print('email could not be sent: %s' % e)
                with open(os.getenv("LOGFILE"), 'a') as lf:
                    lf.write('New alert could not be sent: %s' % e + '\n')

        # Check if project handles personal and/or sensitive data and alert if so
        personal_data = 'no'
        if 'ethical_issues_exist' in i['dmp']:
            if i['dmp']['ethical_issues_exist'] == 'yes':
                personal_data = 'yes'

        if personal_data == 'yes':

            if send_pers_alert == 1:
                # Send new dmp alert
                msg = EmailMessage()
                message = '<p>Hej!</p><p>En ny datahanteringsplan som omfattar hantering av persondata och/eller ' \
                          'känsliga data har skapats eller uppdaterats av ' + dsw_creator + ': <br /><a ' \
                                                                                                    'href="' + dsw_id \
                          + '">' + dsw_id + '</a></p><p>Skapad: ' + dsw_created_date + '<br/>Senast uppdaterad: ' + dsw_modified_date + '</p><p> Följ länken för att se datahanteringsplanen.</p><p>Med ' \
                                            'vänliga hälsningar,<br />Chalmers datakontor (CDO)<br ' \
                                            '/>dataoffice@chalmers.se</p>'
                msg['From'] = formataddr(('Chalmers DS Wizard', 'dsw-noreply@dsw.chalmers.se'))
                msg['To'] = formataddr(('Chalmers dataskyddsombud', os.getenv("PERSONAL_DATA_RECIPIENT")))
                msg['Cc'] = formataddr(('cc', os.getenv("BCC_RECIPIENT")))
                msg['Subject'] = '[Chalmers DSW] Ny datahanteringsplan med persondata'
                msg.set_content(message, subtype='html')

                # send the e-mail
                try:
                    server = smtplib.SMTP(os.getenv("SMTP_SERVER"), os.getenv("SMTP_PORT"))
                    server.ehlo()
                    server.starttls()
                    server.login(os.getenv("SMTP_UID"), os.getenv("SMTP_PW"))
                    server.send_message(msg)
                    print('personal data alert email was sent to ' + os.getenv("PERSONAL_DATA_RECIPIENT"))
                    with open(os.getenv("LOG_RUNS_FILE"), 'a') as lr:
                        lr.write('PERSONAL_DATA_ALERT\t' + dsw_id + '\t' + current_date + '\t' + os.getenv("PERSONAL_DATA_RECIPIENT") + '\n')
                    server.quit()
                except:
                    e = sys.exc_info()[0]
                    print('email could not be sent: %s' % e)
                    with open(os.getenv("LOGFILE"), 'a') as lf:
                        lf.write('Personal data alert could not be sent: %s' % e + '\n')

        # Check if project need to apply for ethical review (or need support) and alert if so
        ethical_review_needed = 'no'
        if 'ethical_review_needed' in i['metadata']:
            if i['metadata']['ethical_review_needed'] == 'yes':
                ethical_review_needed = 'yes'

        if ethical_review_needed == 'yes':

            if send_ethical_alert == 1:
                # Send new dmp alert
                msg = EmailMessage()
                message = '<p>Hej!</p><p>En ny datahanteringsplan för ett projekt som har ansökt om etikprövning och/eller ' \
                          'behöver support kring detta har skapats eller uppdaterats av ' + dsw_creator + ': <br /><a ' \
                                                                                                    'href="' + dsw_id \
                          + '">' + dsw_id + '</a></p><p>Skapad: ' + dsw_created_date + '<br/>Senast uppdaterad: ' + dsw_modified_date + '</p><p> Följ länken för att se datahanteringsplanen.</p><p>Med ' \
                                            'vänliga hälsningar,<br />Chalmers datakontor (CDO)<br ' \
                                            '/>dataoffice@chalmers.se</p>'
                msg['From'] = formataddr(('Chalmers DS Wizard', 'dsw-noreply@dsw.chalmers.se'))
                msg['To'] = formataddr(('Chalmers dataskyddsombud', os.getenv("ETHICAL_REVIEW_RECIPIENT")))
                msg['Cc'] = formataddr(('cc', os.getenv("BCC_RECIPIENT")))
                msg['Subject'] = '[Chalmers DSW] Ny datahanteringsplan, projekt med behov av etikprövning'
                msg.set_content(message, subtype='html')

                # send the e-mail
                try:
                    server = smtplib.SMTP(os.getenv("SMTP_SERVER"), os.getenv("SMTP_PORT"))
                    server.ehlo()
                    server.starttls()
                    server.login(os.getenv("SMTP_UID"), os.getenv("SMTP_PW"))
                    server.send_message(msg)
                    print('personal data alert email was sent to ' + os.getenv("ETHICAL_REVIEW_RECIPIENT"))
                    with open(os.getenv("LOG_RUNS_FILE"), 'a') as lr:
                        lr.write('ETHICAL_REVIEW_ALERT\t' + dsw_id + '\t' + current_date + '\t' + os.getenv("ETHICAL_REVIEW_RECIPIENT") + '\n')
                    server.quit()
                except:
                    e = sys.exc_info()[0]
                    print('email could not be sent: %s' % e)
                    with open(os.getenv("LOGFILE"), 'a') as lf:
                        lf.write('Ethical review alert could not be sent: %s' % e + '\n')


    # Update lastrun.txt with new timestamp
    with open(os.getenv("LASTRUN_FILE"), 'w') as out:
        out.write(current_date)

else:
    print('No new DMPs found')
