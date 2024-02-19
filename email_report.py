#!/usr/bin/python3
""" Generates a report from a log file generated with logging
"""

import os
import argparse
import pathlib
import time
import smtplib
from getpass import getpass
from enum import Enum
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class ReportLevel(Enum):
    """Class used fo argparse options"""
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'

    def __str__(self):
        return self.value

# The name of our script
SCRIPT_NAME = os.path.basename(__file__)

# The max number of blank spaces before a line is considered indented (after Logger tag)
MAX_SPACES_FOR_IGNORE = 2

# Default reporting level
DEFAULT_REPORT_LEVEL = ReportLevel.WARNING

# Default number of lines per report level to include
DEFAULT_REPORT_LEVEL_LINES = 5

# Default email from field
DEFAULT_EMAIL_FROM = 'schnaufer@arizona.edu'

# Default email server
DEFAULT_EMAIL_SERVER = 'ob1.hc4604-54.iphmx.com'

# The environment variable name from which to get user name
EMAIL_USER_ENV_NAME = 'REPORT_EMAIL_USER'

# The environment variable name from which to get password
EMAIL_PASSWORD_ENV_NAME = 'REPORT_EMAIL_PW'

# Argparse-related definitions
# Declare the progam description
ARGPARSE_PROGRAM_DESC = 'Parses a log file and generates a report that is emailed'
# The help text epilog
ARGPARSE_EPILOG = 'No attempt is made to verify the format or validity of email addresses'
# Log file help
ARGPARSE_LOG_FILE_HELP = 'Specify the log file to process'
# Reprting level help
ARGPARSE_REPORT_LEVEL_HELP = 'The minimum logging level to report on. Defaults to ' \
                            f'{DEFAULT_REPORT_LEVEL} and more severe logging'
# Number of logging lines to include in the email for each level
ARGPARSE_LEVEL_LINES_HELP = 'The maximum number of lines per logging level to include in the ' \
                            f'report. Default is {DEFAULT_REPORT_LEVEL_LINES} lines per level'
# Report title
ARGPARSE_TITLE_HELP = 'The title to use in the report. Overrides the default title'
# Email subject
ARGPARSE_SUBJECT_HELP= 'The subject line of the sent email. Overrides the default subject'
# Additional email addresses to send report to
ARGPARSE_EXTRA_EMAIL_HELP = 'A list of one or more additional email addresses separated by '\
                            'colons'
# The primary email address to send report to
ARGPARSE_MAIN_EMAIL_HELP = 'The email address to send the report to'
# Email address used to say who email is from
ARGPARSE_FROM_HELP = 'Change the from email field from {DEFAULT_EMAIL_FROM}'
# Include debug logging in report if specified
ARGPARSE_REPORT_DEBUG_HELP = 'Include debug logging in the report'
# The server to send email through
ARGPARSE_EMAIL_SERVER_HELP = f'SMTP server to send email fom. Default is {DEFAULT_EMAIL_SERVER}'
# The email server user name
ARGPARSE_EMAIL_USER = 'The email server username. If not specified, it is fetched from ' \
            f'the {EMAIL_USER_ENV_NAME} environment variable'
# The email password help
ARGPARSE_EMAIL_PASSWORD = 'Prompt for the email password. When not specified, the password ' \
            f'is fetched from the {EMAIL_PASSWORD_ENV_NAME} environment variable'


def get_arguments() -> dict:
    """Handles the command line arguments
    Returns:
        A dict with the arguments
    """
    parser = argparse.ArgumentParser(prog=SCRIPT_NAME,
                                     description=ARGPARSE_PROGRAM_DESC,
                                     epilog=ARGPARSE_EPILOG)
    parser.add_argument('log_file', type=pathlib.Path, help=ARGPARSE_LOG_FILE_HELP)
    parser.add_argument('email', help=ARGPARSE_MAIN_EMAIL_HELP)
    parser.add_argument('--extra_emails', help=ARGPARSE_EXTRA_EMAIL_HELP)
    parser.add_argument('--report_level', type=ReportLevel, choices=list(ReportLevel),
                        default=DEFAULT_REPORT_LEVEL, help=ARGPARSE_REPORT_LEVEL_HELP)
    parser.add_argument('--level_lines', type=int, default=DEFAULT_REPORT_LEVEL_LINES,
                        help=ARGPARSE_LEVEL_LINES_HELP)
    parser.add_argument('--title', help=ARGPARSE_TITLE_HELP)
    parser.add_argument('--email_server', default=DEFAULT_EMAIL_SERVER,
                        help=ARGPARSE_EMAIL_SERVER_HELP)
    parser.add_argument('--user', help=ARGPARSE_EMAIL_USER)
    parser.add_argument('--password', '-p', action='store_true', help=ARGPARSE_EMAIL_PASSWORD)
    parser.add_argument('--subject', help=ARGPARSE_SUBJECT_HELP)
    parser.add_argument('--email_from', default=DEFAULT_EMAIL_FROM, help=ARGPARSE_FROM_HELP)
    parser.add_argument('--report_debug', action='store_true', help=ARGPARSE_REPORT_DEBUG_HELP)
    args = parser.parse_args()

    # Return the options
    cmd_opts = {'log_file': args.log_file,
                'report_level': args.report_level,
                'level_lines': args.level_lines,
                'title': args.title,
                'server': args.email_server,
                'user': args.user,
                'password': args.password,
                'email': args.email,
                'extra_emails': args.extra_emails,
                'subject': args.subject,
                'from': args.email_from,
                'report_debug': args.report_debug
               }

    if not cmd_opts['user']:
        cmd_opts['user'] = os.environ.get(EMAIL_USER_ENV_NAME)
        if cmd_opts['user'] is None or not cmd_opts['user']:
            raise ValueError('Unable to retrieve user name from environment variable ' \
                             f'{EMAIL_USER_ENV_NAME}')

    if cmd_opts['password'] is True:
        cmd_opts['password'] = getpass()
    else:
        cmd_opts['password'] = os.environ.get(EMAIL_PASSWORD_ENV_NAME)
        if cmd_opts['password'] is None or not cmd_opts['password']:
            raise ValueError(f'Unable to retrieve password from environment variable ' \
                             f'{EMAIL_PASSWORD_ENV_NAME}')

    return cmd_opts


def generate_report_data(opts: dict) -> dict:
    """Generates the report
    Arguments:
        opts: user options
    """
    # Process the logging file
    mod_time = time.strftime('%c (%z)', time.localtime(os.path.getmtime(opts['log_file'])))
    cur_time = time.strftime('%c (%z)', time.localtime())
    total_lines = 0
    found_fields = {
        'debug': 0,
        'info': 0,
        'warning': 0,
        'error': 0,
        'critical': 0,
        'unclassified': 0
    }
    found_field_keys = tuple(found_fields.keys())
    lines_interest = {
        'debug': [],
        'warning': [],
        'error': [],
        'critical': []
    }
    lines_interest_keys = lines_interest.keys()

    # Process each line in the file
    with open(opts['log_file'], 'r', encoding='utf-8') as in_file:
        for one_line in in_file:
            total_lines += 1

            # Skip blanks
            if one_line is None or len(one_line) == 0:
                continue

            # Process the line
            parts = one_line.split(':', 1)
            tag_lower = parts[0][0:15].lower()
            if tag_lower in found_field_keys:
                found_fields[tag_lower] += 1
                if tag_lower in lines_interest_keys:
                    # Only append the number of lines we need for reporting (plus a few more)
                    if len(lines_interest[tag_lower]) < opts['level_lines'] + 3:
                        lines_interest[tag_lower].append(parts[1].lstrip())
            else:
                found_fields['unclassified'] += 1

    return {
        'log_date': mod_time,
        'report_date': cur_time,
        'total_lines': total_lines,
        'counts': found_fields,
        'lines': lines_interest
    }


def send_email(data: dict, opts: dict) -> None:
    """Sends the email to the specified addresses
    Arguments:
        report_data: the generated report data
        opts: user options
    """
    # Get variable fields
    cur_title = opts['title'] if opts['title'] is not None else \
                    os.path.splitext(os.path.basename(opts['log_file']))[0]
    subject = opts['subject'] if opts['subject'] is not None else \
                    f'Automated reporting: {os.path.basename(opts["log_file"])}'


    msg = MIMEMultipart()
    msg['From'] = opts['from']
    msg['To'] = opts['email']
    if opts['extra_emails']:
        msg['Cc'] = ','.join(opts['extra_emails'].split(':'))
    msg['Date'] = data['report_date']
    msg['Subject'] = subject

    report = [f'Title: {cur_title}',
              f'Report date: {report_data["report_date"]}',
              f'Log date: {data["log_date"]}',
              f'Log file: {opts["log_file"]}',
              f'Total lines: {data["total_lines"]}'
              ' ']

    if opts['report_level'] in (ReportLevel.CRITICAL, ReportLevel.ERROR, ReportLevel.WARNING):
        report.append(f'Critical count: {data["counts"]["critical"]}')
        for idx in range(0, min(opts['level_lines'], len(data['lines']['critical']))):
            report.append('>   ' + data['lines']['critical'][idx])
        if len(data['lines']['critical']) >= opts['level_lines']:
            report.append('>   ... (more in log file)')
        report.append(' ')

    if opts['report_level'] in (ReportLevel.ERROR, ReportLevel.WARNING):
        report.append(f'Error count: {data["counts"]["error"]}')
        for idx in range(0, min(opts['level_lines'], len(data['lines']['error']))):
            report.append('>   ' + data['lines']['error'][idx])
        if len(data['lines']['error']) >= opts['level_lines']:
            report.append('>   ... (more in log file)')
        report.append(' ')

    if opts['report_level'] == ReportLevel.WARNING:
        report.append(f'Warning count: {data["counts"]["warning"]}')
        for idx in range(0, min(opts['level_lines'], len(data['lines']['warning']))):
            report.append('>   ' + data['lines']['warning'][idx])
        if len(data['lines']['warning']) >= opts['level_lines']:
            report.append('>   ... (more in log file)')
        report.append(' ')

    if opts['report_debug']:
        report.append(f'Debug count: {data["counts"]["debug"]}')
        for idx in range(0, min(opts['level_lines'], len(data['lines']['debug']))):
            report.append('>   ' + data['lines']['debug'][idx])
        if len(data['lines']['debug']) >= opts['level_lines']:
            report.append('>   ... (more in log file)')
        report.append(' ')

    msg.attach(MIMEText('\n'.join(report)))

    # Attach log file
    with open(opts['log_file'], 'rb') as in_file:
        part = MIMEApplication(in_file.read(),
                                Name=os.path.basename(opts['log_file'])
                              )
    part['Content-Disposition'] = f'attachment; filename="{os.path.basename(opts["log_file"])}"'
    msg.attach(part)

    # Send the email
    if opts['extra_emails']:
        email_addrs = list(opts['extra_emails'].split(':'))
        email_addrs.append(opts['email'])
    else:
        email_addrs = [opts['email']]
    with smtplib.SMTP(opts['server']) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(opts['user'],opts['password'])
        smtp.sendmail(opts['email'], ','.join(email_addrs), msg.as_string())
        smtp.quit()

if __name__ == '__main__':
    user_opts = get_arguments()
    report_data = generate_report_data(user_opts)
    send_email(report_data, user_opts)
