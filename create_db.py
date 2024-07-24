#!/usr/bin/python3
"""This script will create or update the database using a Layer JSON file exported/copied from ESRI
"""

import os
import argparse
import json
import sys
import logging
from typing import Optional
from getpass import getpass
from collections.abc import Iterable
import uuid
import mysql.connector

import a2database
from a2database import A2Database

"""
survey_item_id = '8ad7e11f82fa44c0a52db4ba435b864e' # test (Feature Server) (Form in My Content)
gis = GIS(survey123_api_url, survey123_username, survey123_password)
print(gis)
sr = gis.content.search('owner:schnaufer_uagis')
layer = sr[0] # sr[0].type == 'Feature Service'
json_schema = layer.properties # Same as downloading schema JSON from web
"""

# The default EPSG code of geometries
DEFAULT_GEOM_EPSG=4326

# The name of our script
SCRIPT_NAME = os.path.basename(__file__)

# Default host name to connect to the database
DEFAULT_HOST_NAME = 'localhost'

# Default name for logging output
DEFAULT_LOG_FILENAME = 'create_db.out'

# Argparse-related definitions
# Declare the progam description
ARGPARSE_PROGRAM_DESC = 'Create or updates a database schema from an ESRI Layer JSON file'
# Epilog to argparse arguments
ARGPARSE_EPILOG = 'Seriously consider backing up your database before running this script'
# Host name help
ARGPARSE_HOST_HELP = f'The database host to connect to (default={DEFAULT_HOST_NAME})'
# Name of the database to connect to
ARGPARSE_DATABASE_HELP = 'The database to connect to'
# User name help
ARGPARSE_USER_HELP = 'The username to connect to the database with'
# Password help
ARGPARSE_PASSWORD_HELP = 'Prompt for the password used to connect to the database'
# Declare the help text for the JSON filename parameter (for argparse)
ARGPARSE_JSON_FILE_HELP = 'Path to the JSON file containing the ESRI exported Layer JSON'
# Declare the help text for the force deletion flag
ARGPARSE_FORCE_HELP = 'Force the recreation of the scheme - Will Delete Existing Data!'
# Help text for verbose flag
ARGPARSE_VERBOSE_HELP = 'Display the SQL commands as they are executed'
# Help for supressing the creation of views
ARGPARSE_NOVIEWS_HELP = 'For tables created with foreign keys, do not create an associated ' \
                        'view that resolves the foreign keys. Associated views are created by ' \
                        'default'
# Help for read only mode - no DB changes
ARGPARSE_READONLY_HELP = 'Don\'t run the SQL commands that modify the database. ' \
                         'Can be combined with verbose'
# Help for specifying the EPSG code that geometry coordinates are in
ARGPARSE_GEOMETRY_EPSG_HELP = 'The EPSG code of the coordinate system for the geometric objects ' \
                           f'(default is {DEFAULT_GEOM_EPSG})'
# Help for changing the logging filename
ARGPARSE_LOG_FILENAME_HELP = 'Change the name of the file where logging gets saved. This is a ' \
                             'destructive overwrite of existing files. Default logging file is ' \
                             f'named {DEFAULT_LOG_FILENAME}'


def _get_name_uuid() -> str:
    """Creates a UUID with the hyphens removed
    Returns:
        Returns a modified UUID
    """
    return str(uuid.uuid4()).replace('-', '')


def get_arguments(logger: logging.Logger) -> tuple:
    """ Returns the data from the parsed command line arguments
    Arguments:
        logger: the logging instance to use
    Returns:
        A tuple consisting of a dict containing the loaded JSON to process, and
        a dict of the command line options
    Exceptions:
        A ValueError exception is raised if the filename is not specified
    Notes:
        If an error is found, the script will exit with a non-zero return code
    """
    parser = argparse.ArgumentParser(prog=SCRIPT_NAME,
                                     description=ARGPARSE_PROGRAM_DESC,
                                     epilog=ARGPARSE_EPILOG)
    parser.add_argument('json_file', nargs='+',
                        help=ARGPARSE_JSON_FILE_HELP)
    parser.add_argument('-o', '--host', default=DEFAULT_HOST_NAME,
                        help=ARGPARSE_HOST_HELP)
    parser.add_argument('-d', '--database', help=ARGPARSE_DATABASE_HELP)
    parser.add_argument('-u', '--user', help=ARGPARSE_USER_HELP)
    parser.add_argument('-f', '--force', action='store_true',
                        help=ARGPARSE_FORCE_HELP)
    parser.add_argument('--verbose', action='store_true',
                        help=ARGPARSE_VERBOSE_HELP)
    parser.add_argument('-p', '--password', action='store_true',
                        help=ARGPARSE_PASSWORD_HELP)
    parser.add_argument('--noviews', action='store_true',
                        help=ARGPARSE_NOVIEWS_HELP)
    parser.add_argument('--readonly', action='store_true',
                        help=ARGPARSE_READONLY_HELP)
    parser.add_argument('--geometry_epsg', type=int, default=DEFAULT_GEOM_EPSG,
                        help=ARGPARSE_GEOMETRY_EPSG_HELP)
    parser.add_argument('--log_filename', default=DEFAULT_LOG_FILENAME,
                        help=ARGPARSE_LOG_FILENAME_HELP)
    args = parser.parse_args()

    # Find the JSON file and the password (which is allowed to be eliminated)
    json_file = None
    if not args.json_file:
        # Raise argument error
        raise ValueError('Missing a required argument')

    if len(args.json_file) == 1:
        json_file = args.json_file[0]
    else:
        # Report the problem
        logger.error('Too many arguments specified for input file')
        parser.print_help()
        sys.exit(10)

    # Read in the JSON
    try:
        schema = None
        with open(json_file, encoding="utf-8") as infile:
            schema = json.load(infile)
    except FileNotFoundError:
        logger.error(f'Unable to open JSON file {json_file}')
        sys.exit(11)
    except json.JSONDecodeError:
        logger.error(f'File is not valid JSON {json_file}')
        sys.exit(12)

    cmd_opts = {'force': args.force,
                'verbose': args.verbose,
                'host': args.host,
                'database': args.database,
                'user': args.user,
                'password': args.password,
                'noviews': args.noviews,
                'readonly': args.readonly,
                'geometry_epsg': args.geometry_epsg,
                'log_filename': args.log_filename
               }

    # Return the loaded JSON
    return schema, cmd_opts


def init_logging(filename: str) -> logging.Logger:
    """Initializes the logging
    Arguments:
        filename: name of the file to save logging to
    Return:
        Returns the created logger instance
    """
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter('%(levelname)s: %(message)s')

    # Console handler
    cur_handler = logging.StreamHandler()
    cur_handler.setFormatter(formatter)
    logger.addHandler(cur_handler)

    # Output file handler
    cur_handler = logging.FileHandler(filename, mode='w')
    cur_handler.setFormatter(formatter)
    logger.addHandler(cur_handler)

    return logger


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


def get_relationships(new_relations: tuple, cur_relations: list, cur_table_name: str, \
                      cur_table_id: int) -> tuple:
    """Parses out relationship information and return a list of origin and destination
       relationships. Any newly found origin relationships are added to the current
       list and returned
    Arguments:
        new_relations: the list of new relationships to process
        cur_relations: the list of current origin relationships
        cur_table_name: the current name of the table
        curr_table_id: the ID of the current table
    Returns:
        A tuple consisting of the updated list of origin relationships, and a
        list of destination relationships
    """
    dest_rels = []
    orig_relations = []

    for one_rel in new_relations:
        if 'role' in one_rel and one_rel['role']:
            if one_rel['role'] == 'esriRelRoleDestination':
                # We don't need the table name here since destination relationships get
                # immediately processed
                dest_rels.append({
                                  'rel_name': one_rel['name'],
                                  'table_id': one_rel['relatedTableId'], # Source table ID
                                  'col_name': one_rel['keyField'] # Current column
                                })
            else:
                orig_relations.append({
                                      'table_id': one_rel['relatedTableId'], # Target table ID
                                      'table_name': cur_table_name, # The name of the table
                                      'rel_name': one_rel['name'],
                                      'col_name': one_rel['keyField'] # Column to connect to
                                    })

    cur_relations.append({'id': cur_table_id, 'relations': orig_relations})

    return cur_relations, dest_rels


def get_enum(domain: dict) -> list:
    """Processes the ESRI field domain information as a pre-populated table
    Arguments:
        domain: the ESRI declaraction of a data type
    Returns:
        A list consisting of a table declaration dict, and a list of values
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
    table_name = A2Database.sqlstr(domain['name'])
    table_cols = [ {
        'name': 'code',
        'type': 'VARCHAR(256)',
        'null_allowed': False,
        'primary': True,
        'auto_increment': False,
        'index': True
        }, {
        'name': 'name',
        'type': 'VARCHAR(256)',
        'null_allowed': False,
        }
    ]

    # Generate the values to add
    new_values = [None] * (len(domain['codedValues']))
    index = 0
    for one_enum in domain['codedValues']:
        new_values[index] = {'name': one_enum['name'], 'code': one_enum['code']}
        index = index + 1

    # Return the necessary information (new table info, and other returns)
    return ({
             'name': table_name,
             'primary_col_name': 'code',
             'display_col_name': 'name', 
             'columns': table_cols
            },{
             'table': table_name, 
             'values': new_values
            }  # Data insert info
           )


def get_column_info(col: dict, unique_field_id: str, table_id: int, dest_rels: tuple, \
                    orig_rels: tuple) -> dict:
    """Processes the ESRI Layer Field infomation into a standard format for the database
    Arguments:
        col: the ESRI column definition
        unique_field_id: the unique field ID that indicates a primary key
        table_id: the ID of the table associated with this column
        dest_rels: destination relationships
        orig_rels: origin relationships
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
    col_name = A2Database.sqlstr(col['name'])
    enum_table = None
    enum_values = None
    col_type = None
    null_allowed = col['nullable']
    default_value = col['defaultValue']
    is_primary = False
    make_index = False
    is_spatial = False
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
                col_type = 'VARCHAR(256)'
                make_index = True
                foreign_key = {'col_name': col_name,
                               'reference': enum_table['name'],
                               'reference_col': enum_table['primary_col_name'],
                               'display_col': enum_table['display_col_name']
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
            is_spatial = True

        case 'esriGeometryMultipoint':
            col_type = 'MULTIPOINT'
            is_spatial = True

        case 'esriGeometryPolyline':
            col_type = 'LINESTRING'
            is_spatial = True

        case 'esriGeometryPolygon':
            col_type = 'POLYGON'
            is_spatial = True

        case 'esriGeometryEnvelope' | 'esriGeometryRing' | 'esriGeometryAny':
            col_type = 'GEOMETRY'
            is_spatial = True

    # Checks before returning values
    if col_type is None:
        raise IndexError(f'Unknown ESRI field type {col["type"]} found')

    # Check for relationships
    found_rel = next((rel for rel in dest_rels if rel['col_name'] == col_name), None)
    if found_rel:
        # Find the origin relationship for this destination relationship
        target_table = next((rel for rel in orig_rels if rel['id'] == found_rel['table_id']), None)
        if not target_table:
            raise IndexError(f'Unknown target table for relation {found_rel["rel_name"]} ' \
                             f'with table index {found_rel["table_id"]}')
        target_rel = next((rel for rel in target_table['relations'] if \
                                    rel['table_id'] == table_id), None)
        if target_rel:
            foreign_key = {'col_name': col_name,
                           'reference': target_rel['table_name'],
                           'reference_col': target_rel['col_name']
                          }

    # Return the information
    return {
        'column': {
            'name': col_name,
            'type': col_type,
            'index': make_index,
            'is_spatial': is_spatial,
            'default': default_value,
            'foreign_key': foreign_key,
            'null_allowed': null_allowed,
            'primary': is_primary,
            'comment': 'ALIAS:[' + A2Database.sqlstr(col['alias']) + ']' \
                                if 'alias' in col and not col['alias'] == col['name'] else ''
        },
        'table': enum_table,
        'values': enum_values
    }


def get_geometry_columns(esri_geometry_type: str, geom_srid: int) -> Optional[tuple]:
    """Returns the column(s) representing the ESRI geometry type
    Arguments:
        esri_geometry_type: the string representing the geometry type
        geom_srid: the srid of the geometry type
    Returns:
        A tuple of column definitions that represent the geometry type, or None
        for esriGeometryNull
    Exceptions:
        Raises a TypeError if the geometery type is unknown
    """
    col_type = None

    # Get the column type
    match (esri_geometry_type):
        case 'esriGeometryNull':
            return None

        case 'esriGeometryPoint':
            col_type = 'POINT'

        case 'esriGeometryMultipoint':
            col_type = 'MULTIPOINT'

        case 'esriGeometryLine' | 'esriGeometryPolyline' | 'esriGeometryPath':
            col_type = 'LINESTRING'

        case 'esriGeometryCircularArc':
            col_type = 'GEOMETRY'

        case 'esriGeometryEllipticArc':
            col_type = 'GEOMETRY'

        case 'esriGeometryBezier3Curve':
            col_type = 'GEOMETRY'

        case 'esriGeometryRing':
            col_type = 'POLYGON'

        case 'esriGeometryPolygon':
            col_type = 'POLYGON'

        case 'esriGeometryEnvelope':
            col_type = 'GEOMETRY'

        case 'esriGeometryAny':
            col_type = 'GEOMETRY'

        case 'esriGeometryBag':
            col_type = 'GEOMETRY'

        case 'esriGeometryMultiPatch':
            col_type = 'GEOMETRY'

        case 'esriGeometryTriangleStrip':
            col_type = 'GEOMETRY'

        case 'esriGeometryTriangeFan':
            col_type = 'GEOMETRYCOLLECTION'

        case 'esriGeometryRay':
            col_type = 'GEOMETRY'

        case 'esriGeometrySphere':
            col_type = 'GEOMETRY'

        case 'esriGeometryTriangles':
            col_type = 'GEOMETRYCOLLECTION'

    # Checks before returning values
    if col_type is None:
        raise IndexError(f'Unknown ESRI field type {esri_geometry_type} specified')

    # Return the information as a tuple
    return ({
            'name': 'geom',
            'type': col_type,
            'index': True,
            'is_spatial': True,
            'srid': geom_srid,
            'default': None,
            'foreign_key': None,
            'null_allowed': False,
            'primary': False
            }
            ,)


def layer_table_get_indexes(table_name: str , indexes: tuple, columns: tuple,
                            logger: logging.Logger) -> tuple:
    """Processes ESRI index definitions into a standard format
    Arguments:
        table_name: the name of the table the index definitions belong to
        indexes: the list of defined indexes
        columns: the columns associated with the table - filters out invalid indexes
        logger: logging instance
    Returns:
        A list of indexes to create
    """
    return_idxs = []
    table_columns = set(one_col['name'] for one_col in columns)

    # Loop through and add index entries
    for one_index in indexes:
        index_fields = set(A2Database.sqlstr(one_field.strip()) for one_field in \
                                one_index['fields'].split(','))

        # An invalid index will have column names that don't exist
        if not index_fields.issubset(table_columns):
            logger.warning('Invalid index found (contains invalid columns) ' \
                           f'\"{one_index["name"]}\"')
            logger.warning(f'   Skipping invalid index with fields {index_fields}')
            continue

        return_idxs.append({
            'table': table_name,
            'column_names': list(index_fields),
            'ascending': one_index['isAscending'],
            'unique': one_index['isUnique'],
            'description': f'({one_index["name"]}) {one_index["description"]}'
            })

    return tuple(return_idxs)


def get_srid_from_extent(extent: dict) -> Optional[int]:
    """Parses the parameter for the defined SRID and returns it
    Arguments:
        extent: the ESRI defined extent JSON
    Returns:
        The found SRID or None
    """
    found_srid = None
    if 'spatialReference' in extent and extent['spatialReference']:
        if 'wkid' in extent['spatialReference'] and extent['spatialReference']['wkid']:
            found_srid = int(extent['spatialReference']['wkid'])

    return found_srid


def process_layer_table(esri_schema: dict, relationships: list, opts: dict) -> dict:
    """Processes the layer or table information into a standard format
    Arguments:
        esri_schema: the dict describing one layer or table
        relationships: a list of origin relationships
        opts: contains other command line options and the logger
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
    table_name = A2Database.sqlstr(esri_schema['name'])
    opts['logger'].info(f'HACK:   {table_name}')

    if 'uniqueIdField' in esri_schema:
        if isinstance(esri_schema['uniqueIdField'], dict) and \
                'name' in esri_schema['uniqueIdField']:
            unique_field_id = A2Database.sqlstr(esri_schema['uniqueIdField']['name'])
        else:
            msg = f'Unsupported "uniqueIdField" type found for {table_name} (expected object)'
            raise TypeError(msg)

    # Update the list of origin relationships
    if 'relationships' in esri_schema and esri_schema['relationships']:
        orig_relations, dest_relations = get_relationships(esri_schema['relationships'], \
                                                           relationships, table_name, \
                                                           esri_schema['id'])

    # Generate the columns (and supporting types)
    for one_col in (get_column_info(col, unique_field_id, esri_schema['id'], dest_relations, \
                                                orig_relations) for col in esri_schema['fields']):
        if 'column' in one_col:
            columns.append(one_col['column'])

        # Enumerated column types cause a table to be generated and populated
        if 'table' in one_col and one_col['table']:
            tables.append(one_col['table'])
        if 'values' in one_col and one_col['values']:
            values.append(one_col['values'])

    # Check for geometry types
    if 'geometryType' in esri_schema and esri_schema['geometryType']:
        cur_srid = get_srid_from_extent(esri_schema['extent']) \
                        if ('extent' in esri_schema and esri_schema['extent']) \
                        else opts['geometry_epsg']
        geom_columns = get_geometry_columns(esri_schema['geometryType'], cur_srid)
        if geom_columns:
            columns.extend(geom_columns)

    # Add in any new indexes
    new_indexes = layer_table_get_indexes(table_name, esri_schema['indexes'], columns, \
                                            opts['logger']) if 'indexes' in esri_schema else []
    if len(new_indexes) > 0:
        indexes.extend(new_indexes)

    tables.append({
        'name': esri_schema['name'],
        'columns': columns
        })

    return {'tables': tables, 'indexes': indexes, 'values': values}


def find_table_pk(table_name: str, tables: tuple) -> Optional[str]:
    """Tries to find the primary key associated with the table name
    Arguments:
        table_name: the name of the table of interest
        tables: the list of internal table definitions
    Returns:
        Returns the found primary key nane, or None if one isn't found
    """
    for one_table in tables:
        if one_table['name'] == table_name:
            for one_column in one_table['columns']:
                if 'primary' in one_column and one_column['primary']:
                    return one_column['name']
    return None


def db_process_table(conn: A2Database, table: dict, opts: dict) -> None:
    """Processes the information for a table and creates or updates the table as needed
    Arguments:
        conn: the database connector
        table: the internal information used to creagte/update a table
        opts: contains other command line options and the logger
    Exceptions:
        Raises a RuntimeError if the table already exists
    """
    verbose = 'verbose' in opts and opts['verbose']
    readonly = 'readonly' in opts and opts['readonly']
    force = 'force' in opts and opts['force']

    opts['logger'].info(f'Processing table: {table["name"]}')
    # Check if the table already exists
    matches = False
    if conn.table_exists(table['name']):
        matches = conn.table_cols_match(table['name'], table['columns'], verbose)
        if not matches:
            if not force and not readonly:
                raise RuntimeError(f'Table {table["name"]} already exists in the database, ' \
                                    'please remove it before trying again')

            if not readonly:
                opts['logger'].info(f'Forcing the drop of table {table["name"]}')
            else:
                opts['logger'].info(f'READONLY: table {table["name"]} exists and would need ' \
                       'the force flag specified')
                opts['logger'].info('          continuing in read only mode...')
            conn.drop_table(table['name'], verbose, readonly=readonly)
        elif force:
            if readonly:
                opts['logger'].info(f'READONLY: table {table["name"]} matches definition and ' \
                       'would be recreated with the force flag')
            else:
                opts['logger'].info(f'Forcing the drop of table {table["name"]} despite matching ' \
                                 'definition')
            conn.drop_table(table['name'], verbose, readonly=readonly)
        else:
            opts['logger'].info(f'Table {table["name"]} already exists and matches definition')

    # Create the table
    if not matches or force:
        new_fks, _ = conn.create_table(table['name'], table['columns'], verbose, readonly=readonly)

        # Create a view if foreign keys were created as part of the table
        if new_fks:
            view_name = table['name'] + '_view'
            if ('noviews' not in opts or not opts['noviews']):
                conn.create_view(view_name, table['name'], table['columns'], verbose,
                                 readonly=readonly)
            elif force:
                conn.drop_view(view_name, readonly=readonly)


def find_matching_index(conn: A2Database, table_name: str, index_column_names: list) \
        -> Optional[str]:
    """Tries to find a matching index in the database
    Arguments:
        conn: the database connection
        table_name: the name of the table to look at
        index_column_names: the list of column names to match
    Return:
        Returns the name of a found matching index or None
    """
    found_indexes = {}

    # Setup for index verification check
    query = 'SELECT index_name, column_name FROM INFORMATION_SCHEMA.STATISTICS WHERE ' \
            'table_schema = %s AND table_name = %s ORDER BY seq_in_index ASC'
    conn.execute(query, (conn.database, table_name))
    for (index_name, column_name) in conn.cursor:
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

    if not found_match:
        return None

    return index_to_remove


def db_process_indexes(conn: A2Database, indexes: tuple, opts: dict) -> None:
    """Added indexes to tables where they don't already exist
    Arguments:
        conn: the database connector
        indexes: the indexes to process
        opts: contains other command line options and the logger
    """
    readonly = 'readonly' in opts and opts['readonly']

    # Process the indexes one at a time
    for one_index in indexes:
        index_column_names = set(one_index['column_names'])
        opts['logger'].info(f'Processing index for table: {one_index["table"]} ' \
                         f'{index_column_names}')

        matching_index = find_matching_index(conn, one_index['table'], index_column_names)
        if matching_index:
            if ('force' not in opts or not opts['force'] or matching_index == 'PRIMARY') \
                        and not readonly:
                continue
            # Remove the index
            opts['logger'].info(('READONLY: ' if readonly else '') + \
                    f'Forcing removal of matching index \'{matching_index}\'')
            query = f'DROP INDEX {matching_index} ON {one_index["table"]}'
            if not readonly:
                try:
                    conn.execute(query)
                    conn.reset()
                except mysql.connector.errors.DatabaseError as ex:
                    opts['logger'].warning('Unable to remove matching index %s', str(ex))
                    opts['logger'].warning('    Skipping re-creation of index')
                    if 'verbose' in opts and opts['verbose']:
                        opts['logger'].info(f'   {query}')
                    continue

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
            opts['logger'].info(f'db_process_indexes: {idx_name}')
            opts['logger'].info(f'    {query} ({query_fields})')
        if not readonly:
            conn.execute(query, query_fields)
            conn.reset()


def db_process_values(conn: A2Database, values: tuple, tables: tuple, opts: dict) -> None:
    """Adds the additional data to the database
    Arguments:
        conn: the database connector
        values: list of prepared values to insert into the database
        tables: list of tables in the database - used to find primary key
        opts: contains other command line options and the logger
    """
    verbose = 'verbose' in opts and opts['verbose']
    readonly = 'readonly' in opts and opts['readonly']

    # Process each set of data for each table
    opts['logger'].info('Processing values for tables')
    processed = {}
    for one_update in values:
        table_name = one_update['table']
        if not table_name in processed:
            processed[table_name] = 0

        # Find the primary key name for the table
        primary_key = find_table_pk(table_name, tables)
        if primary_key is None:
            opts['logger'].warning('{table_name} does not have a primary key, inserting all rows')

        # Process each row for the table
        for one_value in one_update['values']:
            processed[table_name] = processed[table_name] + 1

            col_names = list(one_value.keys())
            col_values = list(one_value[key] for key in one_value.keys())
            data_match = conn.check_data_exists(table_name,
                                 col_names,
                                 col_values,
                                 primary_key=None, # Full row value check
                                 verbose=verbose)

            # Skip matching data
            if data_match:
                opts['logger'].info('    Skipping row with exact match')
                continue

            # If we have a primary key, determine if this is an update or an insert
            if primary_key:
                update_data = conn.check_data_exists(table_name,
                                     col_names,
                                     col_values,
                                     primary_key=primary_key,
                                     verbose=verbose)
            else:
                update_data = False

            conn.add_update_data(table_name,
                            col_names,
                            col_values,
                            col_alias={},
                            update=update_data,
                            primary_key=primary_key,
                            verbose=verbose,
                            readonly=readonly)

    if not readonly:
        conn.commit()

    for key, val in processed.items():
        opts['logger'].info(f'   {key}: {val} rows processed')


def update_database(conn: A2Database, schema: list, opts: dict) -> None:
    """Updates the database by adding and changing database objects
    Arguments:
        conn: the database connection
        schema: a list of database objects to create or update
        opts: contains other command line options and the logger
    """
    for one_schema in schema:
        # Process all the tables first
        try:
            for one_table in one_schema['tables']:
                db_process_table(conn, one_table, opts)
        except RuntimeError:
            opts['logger'].error('', exc_info=True, stack_info=True)
            opts['logger'].error('Specify the -f flag to force the removal of existing tables')
            sys.exit(200)

        # Process indexes
        db_process_indexes(conn, one_schema['indexes'], opts)

        # Process any values
        db_process_values(conn, one_schema['values'], one_schema['tables'], opts)


def create_update_database(schema_data: dict, opts: dict = None) -> None:
    """Parses the JSON data and checks if the database objects described are
        found - if not, it creates them; if they exist they are updated as needed
    Arguments:
        schema_data: the loaded database schema
        opts: contains other command line options and the logger
    """
    index = None
    layers = None
    tables = None
    relationships = []
    required_opts = ('host', 'database', 'password', 'user')

    # Check the opts parameter
    if opts is None:
        raise ValueError('Missing command line parameters')
    if not all(required in opts for required in required_opts):
        opts['logger'].error('Missing required command line database parameters')
        sys.exit(100)

    # Get the user password if they need to specify one
    if opts['password'] is not False:
        opts['password'] = getpass()

    # MySQL connection
    try:
        db_conn = a2database.connect(
            host=opts["host"],
            database=opts["database"],
            password=opts["password"],
            user=opts["user"],
            logger=opts["logger"]
        )
    except mysql.connector.errors.ProgrammingError:
        opts['logger'].error('', exc_info=True, stack_info=True)
        opts['logger'].error('Please correct errors and try again')
        sys.exit(101)

    try:
        # Process any layers
        index = 0
        if 'layers' in schema_data:
            opts['logger'].info('HACK: LAYERS')
            layers = [None] * len(schema_data['layers'])
            for one_layer in schema_data['layers']:
                layers[index] = process_layer_table(one_layer, relationships, opts)
                index = index + 1

        # Process any tables
        index = 0
        if 'tables' in schema_data:
            opts['logger'].info('HACK: TABLES')
            tables = [None] * len(schema_data['tables'])
            for one_table in schema_data['tables']:
                tables[index] = process_layer_table(one_table, relationships, opts)
                index = index + 1

    except TypeError:
        opts['logger'].error('', exc_info=True)
        opts['logger'].error(f'    Exception caught at index {index + 1}')
        raise

    # Processes the discovered database objects
    update_database(db_conn, layers + tables, opts)

    opts['logger'].info('Completed processing JSON file' + \
                    (' in READONLY mode' if opts['readonly'] else ''))


if __name__ == "__main__":
    try:
        json_data, other_opts = get_arguments(logging.getLogger())
        other_opts['logger'] = init_logging(other_opts['log_filename'])
        if validate_json(json_data):
            create_update_database(json_data, other_opts)
    except Exception:
        other_opts['logger'].error('Unhandled exception caught', exc_info=True, stack_info=True)
        sys.exit(250)
