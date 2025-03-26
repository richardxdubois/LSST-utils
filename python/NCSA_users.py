import numpy as np
import argparse
import smtplib
from datetime import datetime, timedelta, date
import pandas
from collections import OrderedDict
from email.message import EmailMessage
import argparse
import os
import subprocess


class NCSA_users():

    def __init__(self):

        self.google_sheet = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTFsGAJ8gB8d1gyxz0Uc2PoN-" \
                            "XakAig6EmLNHwuDL9L6T2MRIJj3aLfMJZ_fMqChE75Kn3Ryzthh8Gb/pub?gid=1148231181&single=" \
                            "true&output=csv"
        #self.google_inkind = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwt1Mq10_UL4zMLTfWq_YZX19bzXXaC_Fy0M-" \
        #                     "Gdw7gyImGeFFEUIdzkHZul1L9Ayzdt5qsKWdooiM9/pub?gid=0&single=true&output=csv"
        self.google_inkind = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTFsGAJ8gB8d1gyxz0Uc2PoN-" \
                             "XakAig6EmLNHwuDL9L6T2MRIJj3aLfMJZ_fMqChE75Kn3Ryzthh8Gb/pub?gid=1402748630" \
                             "&single=true&output=csv"
        self.use_ncsa = False
        self.use_inkind = False
        self.users = OrderedDict()
        self.invite_list = ""
        self.debug = False
        self.remind = False
        self.check_account = False
        self.send_mail = False
        self.has_slac = False

        self.mail_subject = "[action required] USDF onboarding for NCSA users"
        self.mail_subject_inkind = "[action required] USDF onboarding for inkind commissioners"
        self.mail_subject_has_slac = "[action required] USDF onboarding for existing SLAC account holders"
        self.mail_body_ncsa = "Rubin's USDF (US Data Facility) at SLAC is ramping up to welcome users from NCSA as" \
                         " services there will end mid August 2022. We are transferring data from NCSA to SLAC,"\
                         " and setting up hardware and services here.\n\n" \
                         "Though the USDF is not yet fully functional, we do need you to get your account created" \
                         " to avoid the" \
                         " bottleneck of a large number of on-boardings at the last moment, and to being able to" \
                         " reconnect you to your NCSA data sooner.\n\n" \
                         "Please find a moment soon to follow the onboarding instructions here:\n\n" \
                         "https://developer.lsst.io/v/PREOPS-892/usdf/onboarding.html#overview \n\n" \
                         "...to obtain a computing account at SLAC for access to the USDF. We will maintain your" \
                         " NCSA account name if it is not already taken at SLAC. Let us know if either you do not" \
                         " want a USDF account or you would prefer a different" \
                         " account name. You should use the LSSTC #ops-usdf " \
                         " slack channel for asking questions during the transition. Announcements will go " \
                         " to #ops-usdf-announce. \n\n" \
                         "   Thanks for your timely attention!\n\n" \
                         " Richard\n --\n Richard Dubois\n Rubin US Data Facility\n"

        self.mail_body_inkind = "Rubin's USDF (US Data Facility) at SLAC is welcoming named" \
                          " commissioners. \n\n" \
                          "Please find a moment soon to follow the onboarding instructions here:\n\n" \
                          "https://developer.lsst.io/usdf/onboarding.html#overview \n\n" \
                          "...to obtain a computing account at SLAC for access to the USDF" \
                          " (let us know if you do not" \
                          " want an account). You should use the LSSTC #ops-usdf " \
                          " slack channel for asking questions. Announcements will go" \
                          " to #ops-usdf-announce.\n\n" \
                          "   Welcome to the USDF!\n\n" \
                          " Richard\n --\n Richard Dubois\n Rubin US Data Facility\n"
        self.mail_body_has_slac = "Rubin's USDF (US Data Facility) at SLAC is ramping up to welcome users from NCSA and" \
                                  " commissioners as services there will end mid August 2022. We are transferring data from" \
                                  " NCSA to SLAC," \
                                  " and setting up hardware and services here. You already have a SLAC unix account" \
                                  " but will need a Windows account to authenticate to the cluster (this is " \
                                  "temporary, but currently necessary.\n\n" \
                                  "Please find a moment soon to follow the onboarding instructions here:\n\n" \
                                  "https://developer.lsst.io/v/PREOPS-892/usdf/onboarding.html#overview \n\n" \
                                  "to obtain a SLAC windows account, used for authentication to SDF. There is a simple" \
                                  " self-serve web interface to get one. Then follow instructions for first login to SDF at:" \
                                  "\n\nhttps://developer.lsst.io/v/PREOPS-892/usdf/lsst-login.html \n\n" \
                                  "You should use the LSSTC #ops-usdf " \
                                  "slack channel for asking questions during the transition. Announcements will go" \
                                  " to #ops-usdf-announce." \
                                  "\n\n Richard\n --\n Richard Dubois\n Rubin US Data Facility\n"

        self.mail_body_reminder = "Please do initiate the onboarding process soon!\n\n------\n\n"

    def read_sheet_ncsa(self):

        if self.debug:
            print("debug mode")

        google_sheet = self.google_sheet

        csv_assign = pandas.read_csv(google_sheet, header=0, skipinitialspace=True)

        user_frame = csv_assign.set_index('username', drop=False)
        print("csv read in: ", self.google_sheet)
        id_col = user_frame["username"]

        self.users = OrderedDict()

        # parse the account name from the username tab
        for account in id_col:

            if self.debug:
                if user_frame.loc[account, "username"] != "rxdubois" and user_frame.loc[account, "username"] !=\
                        "fritzm":
                    continue
            elif self.has_slac:
                keep = "account" in str(user_frame.loc[account, "Comment"]).lower() and "stanford" not in \
                    str(user_frame.loc[account, "Email"]).lower()
                if not keep:
                    continue
            elif self.remind:
                keep = str(user_frame.loc[account, "Invited?"]).lower() == "y" and \
                       pandas.isna(user_frame.loc[account, "Submitted SLUO form"])
                if not keep:
                    continue
            else:
                try:
                    if user_frame.loc[account, "Transfer user?"] == "No" or user_frame.loc[account, "Transfer user?"] == \
                            "special user":
                        print(account)
                        continue
                except:
                    print("error with ", account)
                    break
                if user_frame.loc[account, "Last Login"] == "never":
                    continue
                if str(user_frame.loc[account, "Invited?"]).lower() == "y" and self.check_account is False:
                    continue

            self.users.setdefault(account, OrderedDict())

            self.users[account]["uidn"] = user_frame.loc[account, "uidn"]
            self.users[account]["Name"] = user_frame.loc[account, "Name"]
            self.users[account]["Email"] = user_frame.loc[account, "Email"]
            self.users[account]["Last Login"] = user_frame.loc[account, "Last Login"]
            self.users[account]["Transfer"] = user_frame.loc[account, "Transfer user?"]
            self.users[account]["Comment"] = user_frame.loc[account, "Comment"]
            self.users[account]["Approved"] = user_frame.loc[account, "Approve account request"]
            alt_account = user_frame.loc[account, "Account name at SLAC (if different)"]

            if pandas.isna(alt_account):
                self.users[account]["username"] = account
            else:
                self.users[account]["username"] = alt_account

        print("Completed parse of google sheet with ", len(self.users.keys()), " eligible users")

    def read_sheet_inkind(self):

        if self.debug:
            print("debug mode")

        google_sheet = self.google_inkind

        csv_assign = pandas.read_csv(google_sheet, header=0, skipinitialspace=True)
        username_string = "username"

        user_frame = csv_assign.set_index(username_string, drop=False)
        print("csv read in: ", self.google_sheet)
        id_col = user_frame[username_string]

        self.users = OrderedDict()

        # parse the account name from the username tab
        for account in id_col:

            if self.remind:
                keep = str(user_frame.loc[account, "Invited?"]).lower() == "y" and \
                       pandas.isna(user_frame.loc[account, "Submitted SLUO form"])
                if not keep:
                    continue
            else:
                try:
                    if user_frame.loc[account, "Transfer user?"] == "No":
                        continue
                    if str(user_frame.loc[account, "Invited?"]).lower() == "y" and self.check_account is False:
                        continue
                except:
                    print("error with ", account)
                    break
            print(account)
            self.users.setdefault(account, OrderedDict())

            self.users[account][username_string] = account
            self.users[account]["Last Name"] = user_frame.loc[account, "Last Name"]
            self.users[account]["First Name"] = user_frame.loc[account, "First Name"]
            self.users[account]["Email"] = user_frame.loc[account, "Email"]
            self.users[account]["Approved"] = user_frame.loc[account, "Approve account request"]

            alt_account = user_frame.loc[account, "Account name at SLAC (if different)"]

            if pandas.isna(alt_account):
                self.users[account]["username"] = account
            else:
                self.users[account]["username"] = alt_account

        print("Completed parse of google sheet with ", len(self.users.keys()), " eligible users")

    def check_account_ready(self):
        done = []
        pending = []
        add_group = []

        for who in self.users:
            if pandas.isna(self.users[who]["Approved"]):
                continue

            used_account = self.users[who]["username"]
            account_check = os.system("/usr/bin/id -g " + used_account)

            if account_check == 0:
                done.append(used_account)
                groups = subprocess.Popen(["groups", used_account], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                (gout, gerr) = groups.communicate()
                if "rubin_users" not in str(gout):
                    add_group.append(used_account)
            else:
                pending.append(used_account)

        print("Accounts Done: ", done)
        print("Accounts needing add to rubin_users: ", add_group)
        print("Accounts Pending: ", pending)

    def prep_invite_list_ncsa(self):

        self.invite_list = []

        for who in self.users:
            last_login = self.users[who]["Last Login"]
            if not self.has_slac:
                try:
                    ll_date = datetime.strptime(last_login, '%Y-%m-%d')
                except TypeError:
                    print("bad time for ", who)
                if (datetime.now() - ll_date).days < 180 or self.remind:
                    self.invite_list.append(who)
            else:
                used_account = self.users[who]["username"]
                has_home = subprocess.Popen(["/usr/bin/ls", "-l",
                                             f"/sdf/home/{used_account[0]}/{used_account}"],
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
                (gout, gerr) = has_home.communicate()
                if "No such" in str(gerr):
                    self.invite_list.append(who)

        print("Done preparing list", self.invite_list)

    def prep_invite_list_inkind(self):

        self.invite_list = []

        for who in self.users:
            if self.users[who]["Email"] == "jsmith@institution.edu":
                continue
            self.invite_list.append(who)

        print("Done preparing list", self.invite_list)

    def send_invites(self):

        for who in self.invite_list:
            email = self.users[who]["Email"]
            if self.use_ncsa:
                name = self.users[who]["Name"].split()
            else:
                name = (self.users[who]["First Name"], self.users[who]["Last Name"])

            first_name = name[0]
            if len(name) == 2:
                last_name = name[1]
            else:
                last_name = name[1] + " " + name[2]

            print(who, email, first_name, last_name)
            mail_subject = self.mail_subject

            if self.has_slac:
                mail_body = self.mail_body_has_slac
                mail_subject = self.mail_subject_has_slac
            elif self.use_ncsa:
                mail_body = self.mail_body_ncsa
            else:
                mail_body = self.mail_body_inkind
                mail_subject = self.mail_subject_inkind
            self.send_request(email=email, first=first_name, last=last_name, msg_subject=mail_subject,
                              msg_text=mail_body)

        print(len(self.invite_list), " invitations to send")

    def send_request(self, email=None, first=None, last=None, msg_subject=None, msg_text=None):

        msg_body = "Dear " + first + "," + "\n\n"
        msg_body += msg_text

        msg = EmailMessage()
        msg.set_content(msg_body)

        # me == the sender's email address
        # you == the recipient's email address
        msg['Subject'] = msg_subject
        msg['To'] = first + " " + last + " <" + email + ">"
        msg['From'] = "Richard Dubois <richard@slac.stanford.edu>"

        # Send the message via our own SMTP server.
        if self.send_mail is False:
            print(msg)
        else:
            s = smtplib.SMTP('smtp.slac.stanford.edu')
            s.send_message(msg)
            s.quit()


if __name__ == "__main__":

    # Command line arguments
    parser = argparse.ArgumentParser(description='Perform functions on NCSA accounts lists for USDF transition')

    parser.add_argument('--ncsa', default='n', help="select y/n NCSA accounts list (default=%(default)s)")
    parser.add_argument('--inkind', default='y', help="select y/n in-kinds accounts list (default=%(default)s)")
    parser.add_argument('--account', default='y', help="check accounts ready y/n (default=%(default)s)")
    parser.add_argument('--debug', default='n', help="debug mode y/n (default=%(default)s)")
    parser.add_argument('--remind', default='n', help="send a reminder? y/n (default=%(default)s)")
    parser.add_argument('--sendmail', default='n', help="send mail? y/n (default=%(default)s)")
    parser.add_argument('--has_slac', default='n', help="send to existing SLAC holders? y/n (default=%(default)s)")

    args = parser.parse_args()

    u = NCSA_users()
    if args.ncsa == "y":
        u.use_ncsa = True
    if args.inkind == "y":
        u.use_inkind = True
    if args.debug == "y":
        u.debug = True
    if args.account == "y":
        u.check_account = True
    if args.sendmail == "y":
        u.send_mail = True
    if args.sendmail == "y":
        u.send_mail = True
    if args.has_slac == "y":
        u.has_slac = True
    if args.remind == "y":
        u.remind = True
        u.mail_body_ncsa = u.mail_body_reminder + u.mail_body_ncsa
        u.mail_body_inkind = u.mail_body_reminder + u.mail_body_inkind
        if u.use_ncsa:
            u.mail_subject = "Reminder: " + u.mail_subject
        else:
            u.mail_subject = "Reminder: " + u.mail_subject_inkind

    if u.use_ncsa:
        u.read_sheet_ncsa()
        u.prep_invite_list_ncsa()
    else:
        u.read_sheet_inkind()
        u.prep_invite_list_inkind()

    if u.check_account:
        u.check_account_ready()
    else:
        u.send_invites()
