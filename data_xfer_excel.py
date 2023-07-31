#!/usr/bin/python3
""" This script movs data from an EXCEL spreadsheet to a MySql database
"""

import os
import argparse
import sys
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

# Default row that has the column names
DEFAULT_COL_NAMES_ROW = 1

# The default primary key database name for the sheet data
DEFAULT_PRIMARY_KEY_NAME = 'ObjectID'

# Default EPSG code for points
DEFAULT_GEOM_EPSG = 4326

# Argparse-related definitions
# Declare the progam description
ARGPARSE_PROGRAM_DESC = 'Uploads data from an ESRI generated excel spreadsheet to the ' \
                        'MySQL database'
# Epilog to argparse arguments
ARGPARSE_EPILOG = 'Duplicates are avoided by checking if the data already exists in the database'
# Host name help
ARGPARSE_HOST_HELP = f'The database host to connect to (default={DEFAULT_HOST_NAME})'
# Name of the database to connect to
ARGPARSE_DATABASE_HELP = 'The database to connect to'
# User name help
ARGPARSE_USER_HELP = 'The username to connect to the database with'
# Password help
ARGPARSE_PASSWORD_HELP = 'The password used to connect to the database (leave empty to be prompted)'
# Declare the help text for the EXCEL filename parameter (for argparse)
ARGPARSE_EXCEL_FILE_HELP = 'Path to the EXCEL file to upload'
# Declare the help text for the force deletion flag
ARGPARSE_UPDATE_HELP = 'Update existing data with new values (default is to skip updates)'
# Declare the help for no headers
ARGPARSE_HEADER_HELP = 'Specify the number of lines to consider as headings ' \
                       f'(default {DEFAULT_NUM_HEADER_LINES} lines)'
# Declare the help for where the column names are
ARGPARSE_COL_NAMES_ROW_HELP = 'Specify the row that contains the column names ' \
                              f'(default row is {DEFAULT_COL_NAMES_ROW})'
# Help text for specifying all the column names for the excel file
ARGPARSE_COL_NAMES_HELP = 'Comma seperated list of column names (used when column names are not ' \
                          'specified in the file)'
# Help text fo specifying the primary key to use
ARGPARSE_PRIMARY_KEY_HELP = 'The name of the primary key to use when checking if data is ' \
                            f'already in the database (default "{DEFAULT_PRIMARY_KEY_NAME}"). ' \
                            'Also needs to be a column in the spreadsheet'
# Help text for verbose fla g
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
    parser.add_argument('--col_names_row', type=int, default=DEFAULT_COL_NAMES_ROW,
                        help=ARGPARSE_COL_NAMES_ROW_HELP)
    parser.add_argument('--col_names', help=ARGPARSE_COL_NAMES_HELP)
    parser.add_argument('-k', '--key_name', default=DEFAULT_PRIMARY_KEY_NAME,
                        help=ARGPARSE_PRIMARY_KEY_HELP)
    args = parser.parse_args()

    # Find the EXCEL file and the password (which is allowed to be eliminated)
    excel_file, user_password = None, None
    if not args.excel_file:
        # Raise argument error
        raise ValueError('Missing a required argument')

    if len(args.excel_file) == 1:
        excel_file = args.excel_file[0]
    elif len(args.excel_file) == 2:
        user_password = args.excel_file[0]
        excel_file = args.excel_file[1]
    else:
        # Report the problem
        print('Too many arguments specified for input file', flush=True)
        parser.print_help()
        sys.exit(10)

    # Check that we can access the EXCEL file
    try:
        with open(excel_file, encoding="utf-8"):
            pass
    except FileNotFoundError:
        print(f'Unable to open EXCEL file {excel_file}', flush=True)
        sys.exit(11)

    # Check if we need to prompt for the password
    if args.password and not user_password:
        user_password = getpass()

    cmd_opts = {'force': args.force,
                'verbose': args.verbose,
                'host': args.host,
                'database': args.database,
                'user': args.user,
                'password': user_password,
                'header_lines': args.header,
                'col_names_row': args.col_names_row,
                'col_names': tuple(one_name.strip() for one_name in args.col_names.split(',')) \
                                        if args.col_names else None,
                'primary_key': args.key_name
               }

    # Return the loaded JSON
    return excel_file, cmd_opts


def check_data_exists(table_name: str, col_names: tuple, col_values: tuple, geom_col_info: dict, \
                      cursor, opts: dict) -> bool:
    """Checks if the data already exists in the database
    Arguments:
        table_name: the name of the table to check
        col_names: the names of the column i the table
        col_values: the values to use for checking
        geom_col_info: optional information on a geometry column
        cursor: the database cursor
        opts: additional options
    Returns:
        Returns True if the data is found and False if not
    """
    primary_key = opts['primary_key'] if 'primary_key' in opts else None

    # Perform parameter checks
    if not len(col_names) == len(col_values):
        raise ValueError('The number of columns doesn\'t match the number of values ' \
                         f'in table {table_name}')
    if primary_key and not primary_key in col_names:
        print(f'Warning: Specified primary key name "{primary_key}" not found in ' \
              f'table "{table_name}"', flush=True)
        print('    Defaulting to checking every column', flush=True)
        primary_key = None

    # Determine what columns we're checking
    if primary_key:
        check_cols = (primary_key,)
    else:
        if not geom_col_info:
            check_cols = col_names
        else:
            # Strip out the column names that belong to geometry
            check_cols = tuple(one_name for one_name in col_names if one_name not in \
                                                                geom_col_info['sheet_cols'])

    # Start building the query
    query = f'SELECT count(1) FROM {table_name} WHERE ' + \
                ' AND '.join((f'{one_name}=%s' for one_name in check_cols))

    # Build up the values to pass
    query_values = list(col_values[col_names.index(one_name)] for one_name in check_cols)

    # Build up the geometry portion of the query
    if geom_col_info and not primary_key:
        query += f' AND {geom_col_info["table_column"]}={geom_col_info["col_sql"]}'
        query_values.extend((col_values[col_names.index(one_name)] for one_name in \
                                                                    geom_col_info["sheet_cols"]))

    # Run the query and determine if we have a row or not
    if 'verbose' in opts and opts['verbose']:
        print(query, query_values, flush=True)
    cursor.execute(query, query_values)

    res = cursor.fetchone()
    cursor.reset()

    if res and len(res) > 0 and res[0] == 1:
        return True

    return False


def add_update_data(table_name: str, col_names: tuple, col_values: tuple, geom_col_info:dict, \
                    col_alias: dict, cursor, update: bool, opts: dict) -> None:
    """Adds or updated data in a table
    Arguments:
        table_name: the name of the table to add to/update
        col_names: the name of the columns to add/update
        col_values: the column values to use
        geom_col_info: information on the geometry column
        col_alias: alias information on columns
        cursor: the database cursor
        update: flag indicating whether to update or insert a row of data
        opts: additional options
    """
    # Setup the column names and values including any geometry columns
    if geom_col_info:
        # Without geom column
        query_cols = list((one_name for one_name in col_names if \
                                            one_name not in geom_col_info['sheet_cols']))
        query_types = list(('%s' for one_name in query_cols))
        query_values = list((col_values[col_names.index(one_name)] for one_name in query_cols if \
                                                    not one_name in geom_col_info['sheet_cols']))
        # Adding in geom column
        query_cols.append(geom_col_info['table_column'])
        query_types.append(geom_col_info['col_sql'])
        query_values.extend((col_values[col_names.index(one_name)] \
                                                    for one_name in geom_col_info['sheet_cols']))
    else:
        query_cols = col_names
        query_types = list(('%s' for one_name in query_cols))
        query_values = list(col_values)

    # Check for alias on a column name
    query_cols = list((one_name if not one_name in col_alias else col_alias[one_name] \
                                                                    for one_name in query_cols))

    # Generate the SQL
    if update:
        query = f'UPDATE {table_name} SET '
        query += ', '.join((f'{query_cols[idx]}={query_types[idx]}' \
                                    for idx in range(0, len(query_cols)) \
                                        if query_cols[idx].lower() != opts["primary_key"].lower()))
        query += f' WHERE {opts["primary_key"]} = %s'

        # Remove the primary key from the regular list of values
        primary_key_index = next((idx for idx in range(0, len(query_cols)) \
                                        if query_cols[idx].lower() == opts["primary_key"].lower()))
        query_values = query_values[:primary_key_index] + query_values[primary_key_index+1:]
        query_values = list(query_values)+list((col_values[col_names.index(opts["primary_key"])],))
    else:
        query = f'INSERT INTO {table_name} (' + ','.join(query_cols) + ') VALUES (' + \
                        ','.join(query_types) + ')'

    # Run the query
    if 'verbose' in opts and opts['verbose']:
        print(query, query_values, flush=True)
    cursor.execute(query, query_values)
    cursor.reset()


def get_col_info(table_name: str, col_names: tuple, cursor, conn) -> tuple:
    """Returns information on the columns in the specified table
    Arguments:
        table_name: the name of the table
        col_names: the names of the columns in the table
        cursor: the database cursor
        conn: the database connection
    Returns:
        Returns a tuple with information on the geometry column as a dict (or None if one 
        isn't found) and any column name aliases
    """
    known_geom_types = [
                        'GEOMETRY',
                        'POINT',
                        'LINESTRING',
                        'POLYGON',
                        'MULTIPOINT',
                        'MULTILINESTRING',
                        'MULTIPOLYGON',
                        'GEOMETRYCOLLECTION'
                       ]

    query = 'SELECT column_name,column_type,column_comment FROM INFORMATION_SCHEMA.COLUMNS WHERE ' \
            'table_schema = %s  AND table_name=%s'
    cursor.execute(query, (conn.database, table_name))

    # Try and find a geometry column while collecting comments with aliases
    col_aliases = {}
    found_col, found_type = None, None
    for col_name, col_type, col_comment in cursor:
        # Check for geometry
        if isinstance(col_type, bytes):
            col_type_str = col_type.decode("utf-8").upper()
        else:
            col_type_str = col_type.upper()
        if col_type_str in known_geom_types:
            found_col = col_name
            found_type = col_type_str
        # Check for an alias and strip it out of the comment
        if col_comment and col_comment.startswith('ALIAS:'):
            alias_name = col_comment.split('[')[1].split(']')[0]
            col_aliases[alias_name] = col_name

    if not found_col:
        return None, col_aliases

    # Assemble the geometry type information
    return_info = None
    match(found_type):
        case 'POINT':
            if all(expected_col in col_names for expected_col in ('x', 'y')):
                return_info = {'table_column': found_col,
                               'col_sql': f'ST_GeomFromText(\'POINT(%s %s)\', {DEFAULT_GEOM_EPSG})',
                               'sheet_cols': ('x', 'y')
                              }
        # Add other cases here

    if not return_info:
        raise ValueError(f'Unsupported geometry column found {found_col} of type ' \
                         f'{found_type} in table {table_name}')

    return return_info, col_aliases


def process_sheet(sheet: openpyxl.worksheet.worksheet.Worksheet, cursor, conn, opts: dict) -> None:
    """Uploads the data in the worksheet
    Arguments:
        sheet: the worksheet to upload
        cursor: the database cursor
        conn: the database connection
        opts: additional options
    """
    # Get the table name from the sheet title
    table_name = '_'.join(sheet.title.split('_')[:-1])

    print(f'Updating table {table_name} from tab {sheet.title}', flush=True)

    # Get the rows iterator
    rows_iter = sheet.iter_rows()

    # Get the column names
    if 'col_names' in opts and opts['col_names']:
        # User specified column names
        col_names = opts['col_names']
    else:
        # Find the row with the column names
        col_names = []
        # Skip to the row with the names
        cnt = 1
        while cnt < opts['col_names_row']:
            _ = next(rows_iter)
        for one_col in next(rows_iter):
            col_names.append(one_col.value)

    # Find geometry columns
    geom_col_info, col_alias = get_col_info(table_name, col_names, cursor, conn)

    # Process the rows
    skipped_rows = 0
    added_updated_rows = 0
    for one_row in rows_iter:
        col_values = tuple(one_cell.value for one_cell in one_row)

        # Check for existing data and skip this row if it exists and we're not forcing
        data_exists = check_data_exists(table_name, col_names, col_values, geom_col_info, \
                                        cursor, opts)
        if data_exists and not opts['force']:
            skipped_rows = skipped_rows + 1
            continue

        added_updated_rows = added_updated_rows + 1
        add_update_data(table_name, col_names, col_values, geom_col_info, col_alias, cursor, \
                        data_exists, opts)

    if skipped_rows:
        print('    Processed', added_updated_rows + skipped_rows, \
                        f'rows with {skipped_rows} not updated', flush=True)
    else:
        print('    Processed', added_updated_rows + skipped_rows, 'rows', flush=True)


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
        print('Missing required command line database parameters', flush=True)
        sys.exit(100)

    # MySQL connection
    try:
        db_conn = mysql.connector.connect(
            host=opts["host"],
            database=opts["database"],
            password=opts["password"],
            user=opts["user"]
        )
    except mysql.connector.errors.ProgrammingError as ex:
        print('Error', ex, flush=True)
        print('Please correct errors and try again', flush=True)
        sys.exit(101)

    cursor = db_conn.cursor()

    # Get the database version and add it to the options
    cursor.execute('SELECT VERSION()')
    cur_row = next(cursor)
    if cur_row:
        opts['mysql_version'] = list(int(ver) for ver in cur_row[0].split('-')[0].split('.'))
    cursor.reset()

    # Open the EXCEL file and process each tab
    workbook = load_workbook(filename=filepath, read_only=True, data_only=True)

    print(f'Updating using {filepath}')

    for one_sheet in workbook.worksheets:
        process_sheet(one_sheet, cursor, db_conn, opts)

    db_conn.commit()


if __name__ == '__main__':
    excel_filename, user_opts = get_arguments()
    load_excel_file(excel_filename, user_opts)
