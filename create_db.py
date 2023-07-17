"""This script will create or update the database using a Layer JSON file exported/copied from ESRI
"""

import os
import argparse
import json
from collections.abc import Iterable
import uuid
import mysql.connector

# Define MySQL connection parameters
MYSQL_HOST = 'localhost'
MYSQL_USER = 'chris'
MYSQL_PASSWORD = 'F1reDr4g0n'
MYSQL_DATABASE = 'redsquirrel'

# The name of our script
SCRIPT_NAME = os.path.basename(__file__)

# Argparse-related definitions
# Declare the progam description
ARGPARSE_PROGRAM_DESC = 'Create or updates a database schema from an ESRI Layer JSON file'
# Epilog to argparse arguments
ARGPARSE_EPILOG = 'Seriously consider backing up your database before running this script'
# Declare the help text for the JSON filename parameter (for argparse)
ARGPARSE_JSON_FILE_HELP = 'Path to the JSON file containing the ESRI exported Layer JSON'
# Declare the help text for the force deletion flag
ARGPARSE_FORCE_HELP = 'Force the recreation of the scheme - Will Delete Existing Data!'
# Help text for verbose flag
ARGPARSE_VERBOSE_HELP = 'Display the SQL commands as they are executed'


def _get_name_uuid() -> str:
    """Creates a UUID with the hyphens removed
    Returns:
        Returns a modified UUID
    """
    return str(uuid.uuid4()).replace('-', '')

def _sql_str(haystack: str, replacement: str = None) -> str:
    """Removed characters that could be used for SQL injection (and replaces them with an 
       optional character)
    Arguments:
        haystack: reference string for removing/replacing characters
        replacement: optional string to use as a replacement for disallowed characters
    Returns:
        The updated string
    """
    if replacement is None:
        replacement = ''
    return haystack.replace(';', replacement).replace('(', replacement).replace(')', replacement) \
                   .replace('"', replacement).replace("'", replacement).replace('%', replacement) \
                   .replace('*', replacement)


def get_arguments() -> dict:
    """ Returns the data from the parsed command line arguments
    Returns:
        A string containing the JSON file name to process
    Notes:
        The returned file name is not checked for JSON contents
    Exceptions:
        Throws an exception if the file is not JSON compatible
    """
    parser = argparse.ArgumentParser(prog=SCRIPT_NAME,
                                     description=ARGPARSE_PROGRAM_DESC,
                                     epilog=ARGPARSE_EPILOG)
    parser.add_argument('json_file',
                        type=argparse.FileType('r'),
                        help=ARGPARSE_JSON_FILE_HELP)
    parser.add_argument('-f', '--force', action='store_true',
                        help=ARGPARSE_FORCE_HELP)
    parser.add_argument('--verbose', action='store_true',
                        help=ARGPARSE_VERBOSE_HELP)
    args = parser.parse_args()

    # Read in the JSON
    with args.json_file as infile:
        schema = json.load(infile)

    cmd_opts = {'force': args.force, 'verbose': args.verbose}

    # Return the loaded JSON
    return schema, cmd_opts


def validate_json(schema_json: dict) -> bool:
    """Performs some validation on the loaded JSON and throws an exception if the
       check fails
    Arguments:
        schema_json: the JSON to process
    Returns:
        True is returned when the checks succeed
    Exceptions:
        A TypeError exception is thrown if the JSON fails the checks
    """
    # Perform the basic checks (schema is a dict and we have a layer or table)
    if not isinstance(schema_json, dict) and \
            not ('layers' in schema_json or 'tables' in schema_json):
        raise TypeError('Loaded JSON is not in a known format')

    # Check if the layers and/or tables value is/are the correct type
    if 'layers' in schema_json:
        if not (isinstance(schema_json['layers'], Iterable) and \
                not isinstance(schema_json['layers'], (str, bytes))):
            raise TypeError('Loaded JSON has an invalid "layers" type, needs to be an array')

    if 'tables' in schema_json:
        if not (isinstance(schema_json['tables'], Iterable) and \
                not isinstance(schema_json['tables'], (str, bytes))):
            raise TypeError('Loaded JSON has an invalid "tables" type, needs to be an array')

    # Passed all checks
    return True


def get_enum(domain: dict) -> list:
    """Processes the ESRI field domain information as a pre-populated table
    Arguments:
        domain: the ESRI declaraction of a data type
    Returns:
        A list consisting of a table declaration, 
    """
    # Declare required fields
    req_fields = ('type', 'name')

    # Check on fields
    if not all(req in domain for req in req_fields):
        raise TypeError('Column domain is missing one or more required fields ' + str(req_fields))

    if not domain['type'] == 'codedValue':
        raise IndexError('Unknown column domain type found - expected "codedValue"')
    if not 'codedValues' in domain:
        raise IndexError('Unknown column domain type key found - expected "codedValues"')

    # Generate a table declaration for the values
    table_name = _sql_str(domain['name'])
    table_cols = [ {
        'name': 'id',
        'type': 'INT',
        'null_allowed': False,
        'primary': True,
        'auto_increment': True
        }, {
        'name': 'name',
        'type': 'VARCHAR(256)',
        'null_allowed': False,
        }, {
        'name': 'code',
        'type': 'VARCHAR(256)',
        'null_allowed': False
        }
    ]

    # Generate the values to add
    new_values = [None] * (len(domain['codedValues']))
    index = 0
    for one_enum in domain['codedValues']:
        new_values[index] = {'name': one_enum['name'], 'code': one_enum['code']}
        index = index + 1

    # Return the necessary information
    return ({'name': table_name, 'primary_col_name': 'id', 'columns': table_cols}, # New table info
            {'table': table_name, 'values': new_values}  # Data insert info
           )


def get_column_info(col: dict, unique_field_id: str) -> dict:
    """Processes the ESRI Layer Field infomation into a standard format for the database
    Arguments:
        col: the ESRI column definition
        unique_field_id: the unique field ID that indicates a primary key
    Returns:
        The definition information used for the database
    """
    # Declare required column fields
    req_fields = ('name', 'type')

    # Check on fields
    if not all(req in col for req in req_fields):
        raise TypeError('Column is missing one or more required fields ' + str(req_fields))

    # Check the unique field ID
    if unique_field_id is None:
        unique_field_id = 'objectid'

    # Generate the column information
    col_name = _sql_str(col['name'])
    enum_table = None
    enum_values = None
    col_type = None
    null_allowed = col['nullable']
    default_value = col['defaultValue']
    is_primary = False
    make_index = False
    foreign_key = None
    match (col['type']):
        case 'esriFieldTypeOID':
            col_type = 'char(36)'
            if not is_primary and col['name'] == unique_field_id:
                is_primary = True

        case 'esriFieldTypeGlobalID' | 'esriFieldTypeGUID':
            col_type = 'char(36)'

        case 'esriFieldTypeInteger':
            col_type = 'INT'

        case 'esriFieldTypeDouble':
            col_type = 'DOUBLE'

        case 'esriFieldTypeString':
            if 'domain' in col and col['domain']:
                enum_table, enum_values = get_enum(col['domain'])
                col_type = 'INT'
                make_index = True
                foreign_key = {'col_name': col_name,
                               'reference': enum_table['name'],
                               'reference_col': enum_table['primary_col_name']
                              }
            elif 'length' in col:
                col_len = int(col['length'])
                col_type = f'VARCHAR({col_len})'
            else:
                col_type = 'VARCHAR(255)'

        case 'esriFieldTypeDate':
            col_type = 'TIMESTAMP'

        case 'esriGeometryPoint':
            col_type = 'POINT'

        case 'esriGeometryMultipoint':
            col_type = 'MULTIPOINT'

        case 'esriGeometryPolyline':
            col_type = 'LINESTRING'

        case 'esriGeometryPolygon':
            col_type = 'POLYGON'

        case 'esriGeometryEnvelope' | 'esriGeometryEnvelope':
            col_type = 'GEOMETRY'

    # Checks before returning values
    if col_type is None:
        raise IndexError(f'Unknown ESRI field type {col["type"]} found')

    # Return the information
    return {
        'column': {
            'name': col_name,
            'type': col_type,
            'index': make_index,
            'default': default_value,
            'foreign_key': foreign_key,
            'null_allowed': null_allowed,
            'primary': is_primary
        },
        'table': enum_table,
        'values': enum_values
    }


def layer_table_get_indexes(table_name: str , indexes: tuple, columns: tuple) -> tuple:
    """Processes ESRI index definitions into a standard format
    Arguments:
        table_name: the name of the table the index definitions belong to
        indexes: the list of defined indexes
        columns: the columns associated with the table - filters out invalid indexes
    Returns:
        A list of indexes to create
    """
    return_idxs = []
    table_columns = set(one_col['name'] for one_col in columns)

    # Loop through and add index entries
    for one_index in indexes:
        index_fields = set(_sql_str(one_field.strip()) for one_field in \
                                one_index['fields'].split(','))

        # An invalid index will have column names that don't exist
        if not index_fields.issubset(table_columns):
            print(f'Invalid index found (contains invalid columns) \"{one_index["name"]}\"')
            print( '   Skipping invalid index')
            continue

        return_idxs.append({
            'table': table_name,
            'column_names': list(index_fields),
            'ascending': one_index['isAscending'],
            'unique': one_index['isUnique'],
            'description': f'({one_index["name"]}) {one_index["description"]}'
            })

    return tuple(return_idxs)



def process_layer_table(esri_schema: dict) -> dict:
    """Processes the layer or table information into a standard format
    Arguments:
        esri_schema: the dict describing one layer or table
    Exceptions:
        A TypeError exception is raised if required fields are missing
        An IndexError exception is raised if there's an problem with the JSON definition
    """
    # Declare required fields of interest
    req_fields = ('name', 'fields')

    # Check on fields
    if not all(req in esri_schema for req in req_fields):
        raise TypeError('Schema is missing one or more required fields ' + str(req_fields))

    # Initialize variables before processing the JSON
    tables = []
    columns = []
    indexes = []
    values = []
    unique_field_id = 'objectid'
    table_name = _sql_str(esri_schema['name'])

    if 'uniqueIdField' in esri_schema:
        if isinstance(esri_schema['uniqueIdField'], dict) and \
                'name' in esri_schema['uniqueIdField']:
            unique_field_id = _sql_str(esri_schema['uniqueIdField']['name'])
        else:
            msg = f'Unsupported "uniqueIdField" type found for {table_name} (expected object)'
            raise TypeError(msg)

    # Generate the columns (and supporting types)
    for one_col in (get_column_info(col, unique_field_id) for col in esri_schema['fields']):
        if 'column' in one_col:
            columns.append(one_col['column'])

        # Enumerated column types cause a table to be generated and populated
        if 'table' in one_col and one_col['table']:
            tables.append(one_col['table'])
        if 'values' in one_col and one_col['values']:
            values.append(one_col['values'])

    # Add in any new indexes
    new_indexes = layer_table_get_indexes(table_name, esri_schema['indexes'], columns) \
                                                            if 'indexes' in esri_schema else []
    if len(new_indexes) > 0:
        indexes.extend(new_indexes)

    tables.append({
        'name': esri_schema['name'],
        'columns': columns
        })

    return {'tables': tables, 'indexes': indexes, 'values': values}


def db_table_exists(cursor, table_name: str, conn) -> bool:
    """Returns whether the table exists using the connection parameter
    Arguments:
        cursor: the database cursor
        table_name: the name of the table to check existance for
        conn: the database connector
    Returns:
        Returns True if the table exists and False if not
    """
    query = 'SELECT table_schema, table_name FROM INFORMATION_SCHEMA.TABLES WHERE ' \
            'table_schema = %s AND table_name = %s'

    cursor.execute(query, (conn.database, table_name))

    _ = cursor.fetchall()

    return cursor.rowcount > 0


def db_drop_table(cursor, table_name: str, conn, opts: dict) -> None:
    """Drops the specified table from the database. Will remove any foreign keys dependent
       upon the table
    Arguments:
        cursor: the database cursor
        table_name: the name of the table to drop
        conn: the database connection
        opts: command line options
    """
    # Find and remove any foreign key that point to this table
    query = 'select table_name, constraint_name from information_schema.key_column_usage where ' \
            'referenced_table_name=%s'
    cursor.execute(query, (table_name,))
    fks = {}
    for parent_table_name, constraint_name in cursor:
        if parent_table_name not in fks:
            fks[parent_table_name] = [constraint_name]
        else:
            fks[parent_table_name].append(constraint_name)
    for parent_table_name, names in fks.items():
        for one_name in names:
            query = f'ALTER TABLE {parent_table_name} DROP FOREIGN KEY {one_name}'
            if 'verbose' in opts and opts['verbose']:
                print(f'  {query}')
            cursor.execute(query)
            cursor.reset()

    # Drop the table itself
    query = f'DROP TABLE {table_name}'
    if 'verbose' in opts and opts['verbose']:
        print(f'  {query}')
    cursor.execute(query)
    cursor.reset()


def db_create_table(cursor, table: dict, opts: dict) -> None:
    """Creates a new table in the database
    Arguments:
        cursor: the database cursor
        table: the internal information used to creagte/update a table
        opts: command line options
    Returns:
        Returns a list containing new foreign keys and indexes (in that order). The list
        may contain None or an empty tuple for the foreign keys and indexes
    """
    # Declare variables
    table_name = _sql_str(table["name"])

    # Open the statement to create the table
    query = f'CREATE TABLE {table_name} ('
    query_cols = []
    query_add = []

    # Process the columns
    for one_col in table['columns']:
        col_name = one_col["name"]

        # Be sure to prefix a space before appending strings to the SQL
        # The order of processing the parameters is important (eg: NOT NULL)
        col_sql = f'{col_name} {one_col["type"]}'
        if 'null_allowed' in one_col and isinstance(one_col['null_allowed'], bool):
            if not one_col['null_allowed']:
                col_sql += ' NOT NULL'

        if 'primary' in one_col and one_col['primary']:
            col_sql += ' PRIMARY KEY'

        if 'auto_increment' in one_col and one_col['auto_increment']:
            col_sql += ' AUTO_INCREMENT'

        if 'default' in one_col and one_col['default'] is not None:
            col_sql += f' DEFAULT {one_col["default"]}'

        if 'foreign_key' in one_col and one_col['foreign_key']:
            fk_info = one_col['foreign_key']
            query_add.append(f'FOREIGN KEY ({col_name}) REFERENCES ' \
                                        f'{fk_info["reference"]}({fk_info["reference_col"]})')

        if 'index' in one_col and one_col['index']:
            query_add.append(f'INDEX {table_name}_' + _get_name_uuid() + f'_idx ({col_name})')

        query_cols.append(col_sql)

    # Join the SQL and close the statement
    query += ','.join(query_cols + query_add)
    query += ')'

    if 'verbose' in opts and opts['verbose']:
        print(f'db_create_table: {table_name}')
        print(f'    {query}')
    cursor.execute(query)

    cursor.reset()


def db_process_table(cursor, table: dict, conn, opts: dict) -> None:
    """Processes the information for a table and creates or updates the table as needed
    Arguments:
        cursor: the database cursor
        table: the internal information used to creagte/update a table
        conn: the database connector
        opts: contains other command line options
    Exceptions:
        Raises a RuntimeError if the table already exists
    """
    print(f'Processing table: {table["name"]}')
    # Check if the table already exists
    if db_table_exists(cursor, table['name'], conn):
        if 'force' not in opts or not opts['force']:
            raise RuntimeError(f'Table {table["name"]} already exists in the database, ' \
                                'please remove it before trying again')

        print(f'Forcing the drop of table {table["name"]}')
        db_drop_table(cursor, table["name"], conn, opts)

    # Create the table
    db_create_table(cursor, table, opts)


def db_process_indexes(cursor, indexes: tuple, conn, opts: dict) -> None:
    """Added indexes to tables where they don't already exist
    Arguments:
        cursor: the database cursor
        indexes: the indexes to process
        conn: the database connector
        opts: contains other command line options
    """
    # Process the indexes one at a time
    for one_index in indexes:
        found_indexes = {}
        index_column_names = set(one_index['column_names'])
        print(f'Processing index for table: {one_index["table"]}', index_column_names)

        # Setup for index verification check
        query = 'SELECT index_name, column_name FROM INFORMATION_SCHEMA.STATISTICS WHERE ' \
                'table_schema = %s AND table_name = %s ORDER BY seq_in_index ASC'
        cursor.execute(query, (conn.database, one_index['table']))
        for (index_name, column_name) in cursor:
            if not index_name in found_indexes:
                found_indexes[index_name] = [column_name]
            else:
                found_indexes[index_name].append(column_name)

        # Verify that there isn't already an index on the table with the requested columns
        found_match = False
        index_to_remove = None
        for index_name, col_names in found_indexes.items():
            if index_column_names.issubset(set(col_names)):
                found_match = True
                index_to_remove = index_name
                break
        if found_match:
            if 'force' not in opts or not opts['force'] or index_to_remove == 'PRIMARY':
                continue
            # Remove the index
            print(f'Forcing removal of matching index {index_to_remove}')
            query = f'DROP INDEX {index_to_remove} ON {one_index["table"]}'
            cursor.execute(query)
            cursor.reset()

        # Prepare to create the query string
        idx_name = one_index['table'] + '_' + _get_name_uuid() + '_idx'
        if 'ascending' in one_index and isinstance(one_index['ascending'], bool) and \
                not one_index['ascending']:
            sort_order = ' DESC'  # be sure to have a leading space
        else:
            sort_order = ''
        query_col_str = ','.join(list(index_column_names))

        # Create the index SQL
        query_fields = []
        query = 'CREATE '
        if 'unique' in one_index and one_index['unique']:
            query += ' UNIQUE'
        query += f' INDEX {idx_name} ON {one_index["table"]} ({query_col_str}{sort_order})'
        if 'description' in one_index and one_index['description']:
            query += ' COMMENT %s'
            query_fields.append(one_index['description'])

        if 'verbose' in opts and opts['verbose']:
            print(f'db_process_indexes: {idx_name}')
            print(f'    {query} ({query_fields})')
        cursor.execute(query, query_fields)

        cursor.reset()


def db_process_values(cursor, values: tuple, conn, opts: dict) -> None:
    """Adds the additional data to the database
    Arguments:
        cursor: the database cursor
        values: list of prepared values to insert into the database
        conn: the database connector
        opts: contains other command line options
    """
    # Process each set of data for each table
    print('Processing values for tables')
    processed = {}
    for one_update in values:
        table_name = one_update['table']
        if not table_name in processed:
            processed[table_name] = 0

        for one_value in one_update['values']:
            processed[table_name] = processed[table_name] + 1

            col_names = ','.join(one_value.keys())
            col_values = list(one_value[key] for key in one_value.keys())
            col_params_sql = list(('%s',)) * len(list(col_values))
            col_values_sql = ','.join(col_params_sql)
            query = f'INSERT INTO {table_name} ({col_names}) VALUES({col_values_sql})'

            if 'verbose' in opts and opts['verbose']:
                print(f'db_process_values: {table_name}')
                print(f'    {query}')
                print(f'    {col_values}')
            cursor.execute(query, col_values)

    conn.commit()

    for key, val in processed.items():
        print(f'   {key}: {val} rows added')


def update_database(cursor, schema: list, conn, opts: dict) -> None:
    """Updates the database by adding and changing database objects
    Arguments:
        cursor: the database cursor
        schema: a list of database objects to create or update
        conn: the database connector
        opts: contains other command line options
    """

    # Process all the tables first
    for one_schema in schema:
        for one_table in one_schema['tables']:
            db_process_table(cursor, one_table, conn, opts)

        # Process indexes
        db_process_indexes(cursor, one_schema['indexes'], conn, opts)

        # Process any values
        db_process_values(cursor, one_schema['values'], conn, opts)


def create_update_database(schema_data: dict, opts: dict = None) -> None:
    """Parses the JSON data and checks if the database objects described are
        found - if not, it creates them; if they exist they are updated as needed
    Arguments:
        schema_data: the loaded database schema
        opts: contains other command line options
    """
    index = None
    layers = None
    tables = None

    # Default the opts paramter if it's not specified
    if opts is None:
        opts = {}

    # MySQL connection
    db_conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )
    cursor = db_conn.cursor()

    try:
        # Process any layers
        index = 0
        if 'layers' in schema_data:
            layers = [None] * len(schema_data['layers'])
            for one_layer in schema_data['layers']:
                layers[index] = process_layer_table(one_layer)
                index = index + 1

        # Process any tables
        index = 0
        if 'tables' in schema_data:
            tables = [None] * len(schema_data['tables'])
            for one_table in schema_data['tables']:
                tables[index] = process_layer_table(one_table)
                index = index + 1

    except TypeError as ex:
        msg = str(ex)
        print(msg, flush=True)
        print(f'    Exception caught at index {index + 1}', flush=True)
        raise

    # Processes the discovered database objects
    update_database(cursor, tables + layers, db_conn, opts)


if __name__ == "__main__":
    json_data, other_opts = get_arguments()
    if validate_json(json_data):
        create_update_database(json_data, other_opts)
