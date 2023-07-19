""" This script movs data from an EXCEL spreadsheet to a MySql database
"""

import os
import argparse
from getpass import getpass
import openpyxl
from openpyxl import load_workbook
import mysql.connector

# The name of our script
SCRIPT_NAME = os.path.basename(__file__)

# Default host name to connect to the database
DEFAULT_HOST_NAME = 'localhost'

# Default number of heading lines in the EXCEL file
DEFAULT_NUM_HEADER_LINES = 1

# Argparse-related definitions
# Declare the progam description
ARGPARSE_PROGRAM_DESC = 'Uploads data from an ESRI generated excel spreadsheet to the MySQL database'
# Epilog to argparse arguments
ARGPARSE_EPILOG = 'Duplicates are avoided by checking if a data field exists'
# Host name help
ARGPARSE_HOST_HELP = f'The database host to connect to (default={DEFAULT_HOST_NAME})'
# Name of the database to connect to
ARGPARSE_DATABASE_HELP = 'The database to connect to'
# User name help
ARGPARSE_USER_HELP = 'The username to connect to the database with'
# Password help
ARGPARSE_PASSWORD_HELP = 'The password use to connect to the database (leave empty to be prompted)'
# Declare the help text for the EXCEL filename parameter (for argparse)
ARGPARSE_EXCEL_FILE_HELP = 'Path to the EXCEL file to upload'
# Declare the help text for the force deletion flag
ARGPARSE_UPDATE_HELP = 'Update existing data with new values (default is to skip updates)'
# Declare the help for no headers
ARGPARSE_HEADER_HELP = 'Specify the number of lines to consider as headings ' \
                       f'(default {DEFAULT_NUM_HEADER_LINES} lines)'
# Help text for verbose flag
ARGPARSE_VERBOSE_HELP = 'Display additional information as the script is run'


def get_arguments() -> tuple:
    """ Returns the data from the parsed command line arguments
    Returns:
        A tuple consisting of a string containing the EXCEL file name to process, and
        a dict of the command line options
    Exceptions:
        A ValueError exception is raised if the filename is not specified
    Notes:
        If an error is found, the script will exit with a non-zero return code
    """
    parser = argparse.ArgumentParser(prog=SCRIPT_NAME,
                                     description=ARGPARSE_PROGRAM_DESC,
                                     epilog=ARGPARSE_EPILOG)
    parser.add_argument('excel_file', nargs='+',
                        help=ARGPARSE_EXCEL_FILE_HELP)
    parser.add_argument('-o', '--host', default=DEFAULT_HOST_NAME,
                        help=ARGPARSE_HOST_HELP)
    parser.add_argument('-d', '--database', help=ARGPARSE_DATABASE_HELP)
    parser.add_argument('-u', '--user', help=ARGPARSE_USER_HELP)
    parser.add_argument('-f', '--force', action='store_true',
                        help=ARGPARSE_UPDATE_HELP)
    parser.add_argument('--verbose', action='store_true',
                        help=ARGPARSE_VERBOSE_HELP)
    parser.add_argument('-p', '--password', action='store_true',
                        help=ARGPARSE_PASSWORD_HELP)
    parser.add_argument('--header', type=int, default=DEFAULT_NUM_HEADER_LINES,
                        help=ARGPARSE_HEADER_HELP)
    args = parser.parse_args()

    # Find the EXCEL file and the password (which is allowed to be eliminated)
    excel_file, user_password = None, None
    if not args.excel_file:
        # Raise argument error
        raise ValueError('Missing a required argument')
    elif len(args.excel_file) == 1:
        excel_file = args.excel_file[0]
    elif len(args.excel_file) == 2:
        user_password = args.excel_file[0]
        excel_file = args.excel_file[1]
    else:
        # Report the problem
        print('Too many arguments specified for input file')
        parser.print_help()
        exit(10)

    # Check that we can access the EXCEL file
    try:
        with open(excel_file) as infile:
            pass
    except FileNotFoundError:
        print(f'Unable to open EXCEL file {excel_file}')
        exit(11)

    # Check if we need to prompt for the password
    if args.password and not user_password:
        user_password = getpass()

    cmd_opts = {'force': args.force,
                'verbose': args.verbose,
                'host': args.host,
                'database': args.database,
                'user': args.user,
                'password': user_password,
                'header_lines': args.header
               }

    # Return the loaded JSON
    return excel_file, cmd_opts


def process_sheet(sheet: openpyxl.worksheet.worksheet.Worksheet, cursor, conn, opts: dict) -> None:
    """Uploads the data in the worksheet
    Arguments:
        sheet: the worksheet to upload
        cursor: the database cursor
        conn: the database connector
        opts: additional options
    """
    # Get the table name from the sheet title
    table_name = '_'.join(sheet.title.split('_')[:-1])


def load_excel_file(filepath: str, opts: dict) -> None:
    """Loads the excel file into the database
    Arguments:
        filepath: the path to the file to load
        opts: additional options
    """
    required_opts = ('host', 'database', 'password', 'user')

    # Check the opts parameter
    if opts is None:
        raise ValueError('Missing command line parameters')
    if not all(required in opts for required in required_opts):
        print('Missing required command line database parameters')
        exit(100)

    # MySQL connection
    try:
        db_conn = mysql.connector.connect(
            host=opts["host"],
            database=opts["database"],
            password=opts["password"],
            user=opts["user"]
        )
    except mysql.connector.errors.ProgrammingError as ex:
        print('Error', ex)
        print('Please correct errors and try again')
        exit(101)

    cursor = db_conn.cursor()

    # Open the EXCEL file and process each tab
    workbook = load_workbook(filename=filepath, read_only=True, data_only=True)
    print(f"Worksheet names: {workbook.sheetnames}")
    sheet = workbook.active
    print(sheet)
    print(f"The title of the Worksheet is: {sheet.title}")

    for one_sheet in workbook.worksheets:
        process_sheet(one_sheet, cursor, conn, opts)


if __name__ == '__main__':
    excel_filename, opts = get_arguments()
    load_excel_file(excel_filename, opts)