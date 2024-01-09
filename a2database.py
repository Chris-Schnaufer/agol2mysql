"""Class instance for connecting to the database and managing requests
"""

import uuid
from typing import Any, Optional
import mysql.connector

def connect(user: str = None, password: str = None, host: str = None, database: str = None):
    """
    Arguments:
        user: the name of the database user
        password: the user's password
        host: the database's host
        database: the database to connect to
    """
    new_conn = A2Database()
    new_conn.connect(user, password, host, database)
    return new_conn

class A2Database:
    """Class handling connections to the database
    """
    # Characters to strip out of strings used in SQL statements
    _restricted_chars = ';()"\'%*'

    def __init__(self):
        """Initialize an instance
        """
        self._conn = None
        self._cursor = None
        self._verbose = False
        self._mysql_version = None
        self._epsg = None

    def __del__(self):
        """Handles closing the connection and other cleanup
        """
        if self._cursor is not None:
            self._cursor.reset()
            self._cursor.close()
            self._cursor = None
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _geom_col_names(self, num_pairs: int, **kwargs) -> tuple:
        """Finds the X,Y column names from the kwargs
        Arguments:
            num_pairs: the number of X,Y column name pairs to find
            kwargs: a dict with the column names defined
        Returns:
            Returns a tuple with the X,Y column names pairs (X1, Y1, X2, ...)
        Notes:
            The key names are of the format "colX<int>" and "rowY<int>" where <int> is a number
            starting at 1, and the values are the database column names.
            Column pairs are looked for until the number_pairs of pairs are found.
            The database column names of the found pairs are returned, it's up to the caller to
            determine if the correct number of pairs is returned.
            If a column or row is missing, searching stops and the found pairs are returned;
            for example: if colX20 and colX21 are specified but rowY20 is not, the pairs found
            up to that point are returned (in this case 19 pairs of database column names are
            returned)
        """
        found_cols = []
        idx = 1
        while idx <= num_pairs:
            found_x = None
            found_y = None

            # Find the columns
            cur_key = f'colX{idx}'
            if cur_key in kwargs:
                found_x = A2Database._sqlstr(kwargs[cur_key])
            cur_key = f'rowY{idx}'
            if cur_key in kwargs:
                found_y = A2Database._sqlstr(kwargs[cur_key])

            # Handle results of search
            if found_x is None or found_y is None:
                break

            found_cols.append(found_x)
            found_cols.append(found_y)
            idx += 1

        return tuple(found_cols)

    def __iter__(self):
        """Allows iteration over results"""
        return self._cursor.__iter__

    def _get_name_uuid(self) -> str:
        """Creates a UUID with the hyphens removed
        Returns:
            Returns a modified UUID
        """
        return str(uuid.uuid4()).replace('-', '')

    def connect(self, user: str = None, password: str = None, host: str = None, \
                 database: str = None):
        """Performs the actual connection to the database
        Arguments:
            user: the name of the database user
            password: the user's password
            host: the database's host
            database: the database to connect to
        """
        if self._conn is None:
            if self._verbose:
                print_params = (param for param in (
                                    f'host={host}' if host is not None else None,
                                    f'database={database}' if database is not None else None,
                                    f'user={user}' if user is not None else None,
                                     'password=*****' if password is not None else None
                               ) if param is not None)
                print('Connecting to the database', print_params, flush=True)
            self._conn = mysql.connector.connect(
                                    host=host,
                                    database=database,
                                    password=password,
                                    user=user
                                    )
            self._cursor = self._conn.cursor()

            # Get the database version
            self._cursor.execute('SELECT VERSION()')
            cur_row = next(self._cursor)
            if cur_row:
                self._mysql_version = list(int(ver) for ver in cur_row[0].split('-')[0].split('.'))
            self._cursor.reset()

    @staticmethod
    def _sqlstr(string: str) -> str:
        """Returns a string stripped of all restricted characters
        Arguments:
            string: the string to strip illegal characters from
        Return:
            The corrected string
        """
        ret_str = string
        for one_char in A2Database._restricted_chars:
            ret_str = ret_str.replace(one_char, '')
        return ret_str

    @staticmethod
    def sqlstr(string: str, replacement: str=None) -> str:
        """Returns a string with all restricted characters replaced or removed
        Arguments:
            string: the string to adjust
            replacement: the optional character to use as a replacement
        Return:
            The corrected string
        Note:
            All matching illegal characters are removed if no replacement is specified
        """
        if replacement is None:
            replacement = ''
        else:
            replacement = A2Database._sqlstr(replacement)

        ret_str = string
        for one_char in A2Database._restricted_chars:
            ret_str = ret_str.replace(one_char, replacement)
        return ret_str

    @staticmethod
    def _get_view_spatial_query_cols(geom_type: str, table_name: str, col_name: str) \
                                    -> Optional[str]:
        """Returns the query columns for an exploded view of the geometry type
        Arguments:
            geom_type: the PostGIS geometry type
            table_name: the name of the table
            col_name: the name of the geomtry column
        Returns:
            Returns the SQL fragment with exploded geometry information (such as X, Y, SRID)
            along with the original geometry column. None is returned if the geomety type
            is not supported
        """
        return_sql = None
        match geom_type.lower():
            case 'point':
                return_sql = f'{table_name}.{col_name} as {col_name}, ' \
                             f'st_x({table_name}.{col_name}) as {col_name}_x, ' \
                             f'st_y({table_name}.{col_name}) as {col_name}_y, ' \
                             f'st_srid({table_name}.{col_name}) as {col_name}_srid'

        return return_sql

    @staticmethod
    def _same_type_and_len(db_col_name: str, db_col_size: int, col_type: str,
                          size_opt: bool=False) -> bool:
        """Returns whether the column name and size match the column type
        Arguments:
            db_col_name: the name of the database column
            db_col_size: a size attribute of the column
            col_type: the column type definition to check against
            size_opt: when True, the size specification is optional
        Returns:
            Returns Trus if the definitions appear to be the same, and False otherwise
        """
        col_name = col_type.split('(')[0] if '(' in col_type else col_type
        if db_col_name.casefold() != col_name.casefold():
            return False

        # Check column size, if it's missing and optional we're OK. Otherwise the sizes
        # need to be the same
        col_size = int(col_type.split('(')[1].rstrip(')')) if '(' in col_type else None
        if col_size is None:
            if not size_opt:
                return False
        elif col_size != db_col_size:
            return False

        return True

    @staticmethod
    def _cols_match(db_col_type: str, db_col_len: str, db_numeric_len: str, col_type: str) -> bool:
        """Returns the comparison of the database column information against the
           current column type
        Arguments:
            db_col_type: the type of the column from the database
            db_col_len: optional length of a type (having length is type dependent)
            col_type: the column type definition
        Returns:
            Returns True if the type definitions are considered to be the same, and False
            otherwise
        """
        match(db_col_type.lower()):
            case 'char' | 'varchar' | 'binary' | 'varbinary'| 'tinyblob'| 'blob' | 'tinytext' \
                    | 'text':
                if A2Database._same_type_and_len(db_col_type, int(db_col_len), col_type,
                                                size_opt=True):
                    return True
            # TODO: case 'enum':
            # TODO: case 'set':
            case 'decimal' | 'numeric' | 'bit':
                if A2Database._same_type_and_len(db_col_type, int(db_numeric_len), col_type):
                    return True
            case _:
                if col_type.casefold() == db_col_type.casefold():
                    return True
        return False

    @property
    def verbose(self):
        """Returns the verbosity of the database calls """
        return self._verbose

    @verbose.setter
    def verbose(self, noisy: bool=True) ->None:
        """Sets the verbosity level of the database calls """
        self._verbose = noisy

    @property
    def epsg(self):
        """Returns the default epsg for geometries"""
        return self._epsg

    @epsg.setter
    def epsg(self, epsg: int) -> None:
        """Sets the default EPSG for geometry objects"""
        self._epsg = epsg

    @property
    def rowcount(self):
        """Returns the current number of rows"""
        return self._cursor.rowcount

    @property
    def database(self):
        """Returns the name of the connection database"""
        return self._conn.database

    @property
    def connection(self):
        """Returns the database connection for functions this class doesn't support"""
        return self._conn

    @property
    def cursor(self):
        """Returns the database cursor for functions this class doesn't support"""
        return self._cursor

    @property
    def version(self):
        """Returns the database version information"""
        return self._mysql_version

    @property
    def version_major(self):
        """Returns the database major revision number"""
        return self._mysql_version[0]

    @property
    def version_minor(self):
        """Returns the database minor revision number"""
        return self._mysql_version[1] if len(self._mysql_version) > 1 else 0

    def execute(self, sql_command: str, params: tuple=None, multi: bool=False) -> None:
        """Handles the execution of a SQL statement"""
        if self._verbose:
            if params is not None:
                print(sql_command, params, flush=True)
            else:
                print(sql_command, flush=True)
        self._cursor.execute(sql_command, params, multi)

    def fetchone(self):
        """Fetches one row"""
        return self._cursor.fetchone()

    def fetchall(self):
        """Returns all the rows"""
        return self._cursor.fetchall()

    def commit(self):
        """Performs a commit to the database"""
        if self._verbose:
            print('Committing to the database', flush=True)
        self._conn.commit()

    def reset(self):
        """Resets (clears) the current query"""
        if self._verbose:
            print('Resetting the cursor', flush=True)
        self._cursor.reset()

    def check_data_exists_pk(self, table_name: str, primarykey: str, primarykeyvalue: Any,
                             verbose: bool=False) -> bool:
        """Checks if a record exists using a primary key
        Arguments:
            table_name: the table to check
            primarykey: the name of the primarykey column
            primarykeyvalue: the value to look for
            verbose: override default for printing query information (prints if True)
        Return:
            Returns True if one or more rows contain the primary key value and False if no
            rows are found
        """
        if verbose is None:
            verbose = self._verbose

        table_name = A2Database._sqlstr(table_name)

        clean_key = A2Database._sqlstr(primarykey)
        query = f'SELECT count(1) FROM {table_name} WHERE {clean_key}=%s'

        if verbose is True:
            print(f'  {query}', flush=True)

        self._cursor.execute(query, (primarykeyvalue,))
        res = self._cursor.fetchone()
        self._cursor.reset()

        if res and len(res) > 0 and res[0] > 0:
            return True

        return False

    def get_col_info(self, table_name: str, col_names: tuple, geometry_epsg: int, **kwargs) \
                     -> tuple:
        """Returns alias information on the columns in the specified table and a found
           geometry column
        Arguments:
            table_name: the name of the table
            col_names: the names of the columns in the table
            geometry_epsg: the EPSG code of the geometry in the table
            colX(X): the column names for geometry X values - where X is a value starting from 1 \
                     (e.g.: colX1='location_X1', colX2='location_X2', ...)
            rowY(Y): the column names for geometry Y values - where Y is a value starting from 1 \
                     (e.g.: colY1='location_Y1', colY2='location_Y2', ...)
        Returns:
            Returns a tuple with information on the geometry column as a dict (or None if one 
            isn't found) and any column name aliases as a dict (alias' are the keys of the dict)
        Exceptions:
            ValueError is raised if the geometry type of a column isn't supported
        """
        table_name = A2Database._sqlstr(table_name)

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

        query = 'SELECT column_name,column_type,column_comment FROM INFORMATION_SCHEMA.COLUMNS ' \
                'WHERE table_schema = %s  AND table_name=%s'
        self._cursor.execute(query, (self._conn.database, table_name))

        # Try and find a geometry column while collecting comments with aliases
        col_aliases = {}
        geom_col, geom_type = None, None
        for col_name, col_type, col_comment in self._cursor:
            # Check for geometry
            if isinstance(col_type, bytes):
                col_type_str = col_type.decode("utf-8").upper()
            else:
                col_type_str = col_type.upper()
            if col_type_str in known_geom_types:
                geom_col = col_name
                geom_type = col_type_str
            # Check for an alias and strip it out of the comment
            if col_comment and col_comment.startswith('ALIAS:'):
                alias_name = col_comment.split('[')[1].split(']')[0]
                col_aliases[alias_name] = col_name

        if not geom_col:
            return None, col_aliases

        # Assemble the geometry type information
        return_info = None
        match(geom_type):
            case 'POINT':
                point_col_x, point_col_y = self._geom_col_names(1, **kwargs)
                if not point_col_x or not point_col_y:
                    raise ValueError(f'Point type found in table {table_name} but columns were '
                                      'not specified')
                if all(expected_col in col_names for expected_col in (point_col_x, point_col_y)):
                    if self.version_major >= 8 and geometry_epsg is not None \
                                                            and geometry_epsg != self._epsg:
                        col_sql = 'ST_TRANSFORM(ST_GeomFromText(\'POINT(%s %s)\', ' \
                                  f'{geometry_epsg}), {self._epsg})'
                    else:
                        col_sql = f'ST_GeomFromText(\'POINT(%s %s)\', {self._epsg})'
                    return_info = {'table_column': geom_col,
                                   'col_sql': col_sql,
                                   'sheet_cols': (point_col_x, point_col_y)
                                  }
                else:
                    raise ValueError(f'Expected point column names "{point_col_x}" and ' \
                                     f'"{point_col_y}" not found in specified column names: ', \
                                     col_names)
            # Add other cases here

        if return_info is None:
            raise ValueError(f'Unsupported geometry column found "{geom_col}"" of type ' \
                             f'{geom_type} in table "{table_name}"')

        return return_info, col_aliases

    def table_exists(self, table_name: str) -> bool:
        """Returns whether the table exists using the connection parameter
        Arguments:
            table_name: the name of the table to check existance for
        Returns:
            Returns True if the table exists and False if not
        """
        table_name = A2Database._sqlstr(table_name)

        query = 'SELECT table_schema, table_name FROM INFORMATION_SCHEMA.TABLES WHERE ' \
                'table_schema = %s AND table_name = %s'

        self._cursor.execute(query, (self._conn.database, table_name))

        _ = self._cursor.fetchall()

        return self._cursor.rowcount > 0

    def table_cols_match(self, table_name: str, col_info: tuple, verbose: bool=None) -> bool:
        """Determines if the current columns in the database table matches the specification
        Arguments:
            table_name: the name of the table to drop
            col_info: see create_table() for the list of fields used
            verbose: override default for printing query information (prints if True)
        """
        if verbose is None:
            verbose = self._verbose

        table_name = A2Database._sqlstr(table_name)

        query = 'SELECT column_name, data_type, character_maximum_length, column_key, ' \
                'column_comment, numeric_scale, is_nullable=\'YES\', ' \
                '(extra like \'%auto_increment%\') as auto_increment, ' \
                'column_default FROM ' \
                'INFORMATION_SCHEMA.COLUMNS WHERE table_schema = %s AND table_name=%s'

        self._cursor.execute(query, (self._conn.database, table_name))

        #_ = self._cursor.fetchall()

        # Prepare to loop through the data
        col_indexes = {A2Database._sqlstr(col_val['name']):col_idx for col_idx, col_val in \
                                                enumerate(col_info)}

        # Loop through the columns returned
        # column_key = 'PRI'
        found_cols = []
        for col_name, col_type, col_char_max_len, col_key, _, numeric_scale, \
                                is_nullable, auto_increment, column_default in self._cursor:
            if not col_name in col_indexes:
                if verbose:
                    print(f'Table "{table_name}" column "{col_name}" is not found in new ' \
                           'table definition')
                return False
            # Get the matched column information by name
            match_col = col_info[col_indexes[col_name]]

            if not A2Database._cols_match(col_type, col_char_max_len, numeric_scale,
                                            match_col['type']):
                return False

            if 'null_allowed' in match_col and bool(is_nullable) != bool(match_col['null_allowed']):
                return False

            if 'primary' in match_col and (col_key == 'PRI') != bool(match_col['primary']):
                return False

            if 'auto_increment' in match_col and bool(auto_increment) != \
                                                            bool(match_col['auto_increment']):
                return False

            if 'default' in match_col and match_col['default'] is not None and \
                            column_default.casefold() != match_col['default'].casefold():
                return False

            found_cols.append(col_name.casefold())

        self._cursor.reset()

        # Make sure we found everything that's specified in the column definitions
        if verbose and not len(found_cols) == len(col_info):
            extra_cols = set((A2Database._sqlstr(col_val['name']).casefold() for \
                                col_val in col_info))
            extra_cols = extra_cols - set(found_cols)
            print(f'Table {table_name} has fewer defined columns than it\'s definition')
            for one_col in extra_cols:
                print(f'    {one_col}')
        return len(found_cols) == len(col_info)

    def drop_table(self, table_name: str, verbose: bool=None, readonly: bool=False) -> None:
        """Drops the specified table from the database. Will remove any foreign keys dependent
           upon the table
        Arguments:
            table_name: the name of the table to drop
            verbose: override default for printing query information (prints if True)
            readonly: don't execute SQL statements that modify the database
        """
        if verbose is None:
            verbose = self._verbose

        table_name = A2Database._sqlstr(table_name)

        # Find and remove any foreign key that point to this table
        query = 'SELECT table_name, constraint_name FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE ' \
                'WHERE referenced_table_schema = %s AND referenced_table_name=%s'
        self._cursor.execute(query, (self._conn.database, table_name))
        fks = {}
        for parent_table_name, constraint_name in self._cursor:
            if parent_table_name not in fks:
                fks[parent_table_name] = [constraint_name]
            else:
                fks[parent_table_name].append(constraint_name)
        for parent_table_name, names in fks.items():
            for one_name in names:
                query = f'ALTER TABLE {parent_table_name} DROP FOREIGN KEY {one_name}'
                if verbose is True:
                    print(f'  {query}', flush=True)
                if not readonly:
                    self._cursor.execute(query)
                    self._cursor.reset()

        # Drop the table itself
        query = f'DROP TABLE {table_name}'
        if verbose is True:
            print(f'  {query}', flush=True)

        if not readonly:
            self._cursor.execute(query)
            self._cursor.reset()

    def create_table(self, table_name: str, col_info: tuple, verbose: bool=None,
                     readonly: bool=False) -> tuple:
        """Creates a table based upon the information passed in
        Arguments:
            table_name: name of the table to create
            col_info: a list of column information for the table
            verbose: override default for printing query information (prints if True)
            readonly: don't execute SQL statements that modify the database
        Notes:
            Referenced keys for each column information dict in the col_info list are: 
                'name': str: the column name
                'type': str: the database type of the column
                'null_allowed': bool: column allows NULL values
                'srid': int: the SRID of a geometry column
                'primary': bool: the column is a primary key
                'auto_increment': bool: the column auto-increments
                'default': ?: optional default value for the column (type matches column type)
                'comment': str: optional comment string
                'foreign_key': {'reference': <referenced table name>, 'reference_col': \
                                <referenced column name>}: foreign key definition
                'index': bool: create an index on the column
                'is_spatial': bool: is a spatial column when True
        Return:
            A tuple containing a dict of the foreign key column with the name of the referenced
            table and column as a tuple (in that order), and a dict of index names and a list of 
            their associated column names.
        """
        if verbose is None:
            verbose = self._verbose

        fks_created = {}
        idx_created = {}

        # Declare variables
        table_name = A2Database._sqlstr(table_name)

        # Open the statement to create the table
        query = f'CREATE TABLE {table_name} ('
        query_cols = []
        query_add = []

        # Process the columns
        for one_col in col_info:
            col_name = A2Database._sqlstr(one_col['name'])

            # Be sure to prefix a space before appending strings to the SQL
            # The order of processing the parameters is important (eg: NOT NULL)
            col_sql = f'{col_name} {one_col["type"]}'
            if 'null_allowed' in one_col and isinstance(one_col['null_allowed'], bool):
                if not one_col['null_allowed']:
                    col_sql += ' NOT NULL'

            if 'srid' in one_col and one_col['srid']:
                if self.version_major >= 8:
                    col_sql += f' SRID {one_col["srid"]}'

            if 'primary' in one_col and one_col['primary']:
                col_sql += ' PRIMARY KEY'
                idx_created['PRIMARY'] = (col_name,)

            if 'auto_increment' in one_col and one_col['auto_increment']:
                col_sql += ' AUTO_INCREMENT'

            if 'default' in one_col and one_col['default'] is not None:
                col_sql += f' DEFAULT {one_col["default"]}'

            if 'comment' in one_col and one_col['comment'] is not None:
                col_sql += f' COMMENT \'{one_col["comment"]}\''

            if 'foreign_key' in one_col and one_col['foreign_key']:
                fk_info = one_col['foreign_key']
                query_add.append(f'FOREIGN KEY ({col_name}) REFERENCES ' \
                                            f'{fk_info["reference"]}({fk_info["reference_col"]})')
                fks_created[col_name] = (fk_info['reference'], fk_info['reference_col'])

            if 'index' in one_col and one_col['index']:
                if 'is_spatial' in one_col and one_col['is_spatial']:
                    query_add.append(f'SPATIAL INDEX({col_name})')
                    idx_created[col_name] = (col_name,)
                else:
                    idx_name = f'{table_name}_' + self._get_name_uuid() + '_idx'
                    query_add.append(f'INDEX {idx_name} ({col_name})')
                    idx_created[idx_name] = (col_name,)

            query_cols.append(col_sql)

        # Join the SQL and close the statement
        query += ','.join(query_cols + query_add)
        query += ') COLLATE = utf8mb4_unicode_ci'

        if verbose:
            print(query, flush=True)

        if not readonly:
            self._cursor.execute(query)
            self._cursor.reset()

        return fks_created, idx_created

    def view_exists(self, view_name: str) -> bool:
        """Returns whether the view exists using the connection parameter
        Arguments:
            view_name: the name of the view to check existance for
        Returns:
            Returns True if the view exists and False if not
        """
        view_name = A2Database._sqlstr(view_name)

        query = 'SELECT table_schema, table_name FROM INFORMATION_SCHEMA.TABLES WHERE ' \
                'table_schema = %s AND table_name = %s'

        self._cursor.execute(query, (self._conn.database, view_name))

        _ = self._cursor.fetchall()

        return self._cursor.rowcount > 0

    def drop_view(self, view_name: str, verbose: bool=None, readonly: bool=False) -> None:
        """Drops the view from the database
        Arguments:
            view_name: the name of the view to create
            verbose: override default for printing query information (prints if True)
            readonly: don't execute SQL statements that modify the database
        """
        if verbose is None:
            verbose = self._verbose
        if self.view_exists(view_name):
            query = f'DROP VIEW {self.sqlstr(view_name)}'

            if verbose:
                print(query, flush=True)

            if not readonly:
                self._cursor.execute(query)
                self._cursor.reset()

    def create_view(self, view_name: str, table_name: str, col_info: tuple, verbose: bool=None,
                    readonly: bool=False) -> None:
        """Creates a view based upon the information passed in
        Arguments:
            view_name: the name of the view to create
            table_name: name of the table to use for the view
            col_info: a tuple of column information for the table
            verbose: override default for printing query information (prints if True)
            readonly: don't execute SQL statements that modify the database
        Notes:
            Referenced keys for each column information dict in the col_info list are: 
                'name': str: the column name
                'type': str: the database type of the column
                'null_allowed': bool: column allows NULL values
                'srid': int: the SRID of a geometry column
                'primary': bool: the column is a primary key
                'auto_increment': bool: the column auto-increments
                'default': ?: optional default value for the column (type matches column type)
                'comment': str: optional comment string
                'foreign_key': {'reference': <referenced table name>,
                                'reference_col': <referenced column name>,
                                'display_col': <display column name>}: foreign key definition
                'index': bool: create an index on the column
                'is_spatial': bool: is a spatial column when True
        """
        if verbose is None:
            verbose = self._verbose

        clean_table_name = A2Database._sqlstr(table_name)
        joins = []

        # Build up the basic query
        query = f'CREATE OR REPLACE VIEW {A2Database._sqlstr(view_name)} AS SELECT '
        col_separator = ' '
        for one_col in col_info:
            col_name = A2Database._sqlstr(one_col['name'])

            if 'foreign_key' not in one_col or not one_col['foreign_key']:
                if 'is_spatial' not in one_col or not one_col['is_spatial']:
                    query += f'{col_separator} {clean_table_name}.{col_name} AS {col_name}'
                else:
                    return_sql = A2Database._get_view_spatial_query_cols(one_col['type'],
                                                                clean_table_name, col_name)
                    if return_sql is None:
                        raise ValueError(f'Unsupported geometry column type found ' \
                                         f'"{one_col["type"]}" in column ' \
                                         f'"{clean_table_name}.{col_name}" while creating ' \
                                         f'view "{view_name}"')
                    query += col_separator + return_sql
            else:
                fk_info = one_col['foreign_key']
                if 'display_col' in fk_info and fk_info['display_col']:
                    query += col_separator + \
                                f'{fk_info["reference"]}.{fk_info["display_col"]} AS {col_name}'
                else:
                    query += col_separator + \
                                f'{fk_info["reference"]}.{fk_info["reference_col"]} AS {col_name}'
                join_sql = f'LEFT JOIN {fk_info["reference"]} ON ' + \
                                f'{clean_table_name}.{col_name} = ' + \
                                f'{fk_info["reference"]}.{fk_info["reference_col"]}'
                joins.append(join_sql)

            col_separator = ', '

        query += f' FROM {A2Database._sqlstr(clean_table_name)} '

        # Append to the query
        query += ' '.join(joins)

        # Run the query
        if verbose:
            print(query, flush=True)

        if not readonly:
            self._cursor.execute(query)
            self._cursor.reset()

    def check_data_exists(self, table_name: str, col_names: tuple, col_values: tuple, \
                          col_alias: dict=None, geom_col_info: dict=None, primary_key: str=None, \
                          verbose: bool=None) -> bool:
        """Checks if the data already exists in the database
        Arguments:
            table_name: the name of the table to check
            col_names: the names of the column in the table
            col_values: the values to use for checking
            col_alias: alias information on columns consisting of column alias' as keys with
                       database column names as values. e.g.: {'alias': 'column nanme'}
            geom_col_info: optional information on a geometry column
            primary_key: optional primary key column name
            verbose: override default for printing query information (prints if True)
        Returns:
            Returns True if the data is found and False if not
        Exceptions:
            Raises a ValueError if the number column names and column values don't match.
        Notes:
            The required key names and value descriptions in geom_col_info are:
            'col_sql': the SQL fragment representing the geometry including any coordinate system
                       transformations needed. For example: 'ST_GeomFromText(POINT(%s %s), %s)'
            'sheet_cols': tuple of column names corresponding to the geometry values found in the
                          col_names parameter. For example: (point_x, point_y, point_epsg) which
                          are the X, Y, and EPSG column names for a point
            'table_column': the geometry column name in the target table
        """
        if verbose is None:
            verbose = self._verbose

        table_name = A2Database._sqlstr(table_name)

        # Perform parameter checks
        if not len(col_names) == len(col_values):
            raise ValueError('The number of columns doesn\'t match the number of values ' \
                             f'in table {table_name}')
        if primary_key and not primary_key in col_names:
            raise ValueError(f'The primary key name "{primary_key}" is not found in ' \
                  f'column_names "{col_names}"')

        # Determine what columns we're checking
        if primary_key:
            check_cols = (primary_key,)
        else:
            if not geom_col_info:
                check_cols = tuple(one_name for one_name in col_names)
            else:
                # Strip out the column names that belong to geometry (for now)
                check_cols = tuple(one_name for one_name in col_names \
                                if one_name not in geom_col_info['sheet_cols'])

        # Check for column alias's and make the switch where needed
        if col_alias:
            # Check for alias on a column name
            check_cols = tuple((one_name if not one_name in col_alias else col_alias[one_name] \
                                                                        for one_name in check_cols))

        # Start building the query
        query = f'SELECT count(1) FROM {table_name} WHERE ' + \
                    ' AND '.join((f'{A2Database._sqlstr(one_name)}=%s' for one_name in check_cols))

        # Build up the values to pass
        query_values = list(col_values[col_names.index(one_name)] for one_name in check_cols)

        # Build up the geometry portion of the query
        if geom_col_info and not primary_key:
            query += f' AND {A2Database._sqlstr(geom_col_info["table_column"])}=' \
                     f'{geom_col_info["col_sql"]}'
            query_values.extend((col_values[col_names.index(one_name)] for one_name in \
                                                                    geom_col_info['sheet_cols']))

        # Run the query and determine if we have a row or not
        if verbose:
            print(query, query_values, flush=True)
        self._cursor.execute(query, query_values)

        res = self._cursor.fetchone()
        self._cursor.reset()

        if res and len(res) > 0 and res[0] == 1:
            return True

        return False

    def add_update_data(self, table_name: str, col_names: tuple, col_values: tuple, \
                        col_alias: dict, geom_col_info: dict=None, \
                        update: bool=False, primary_key: str=None, verbose: bool=None,
                        readonly: bool=False) -> None:
        """Adds or updated data in a table. Caller needs to commit the data after al the data is
           uploaded
        Arguments:
            table_name: the name of the table to add to/update
            col_names: the name of the columns to add/update
            col_values: the column values to use
            col_alias: alias information on columns consisting of column alias' as keys with
                       database column names as values. e.g.: {'alias': 'column nanme'}
            geom_col_info: information on the geometry column
            update: flag indicating whether to update or insert a row of data
            primary_key: the primary key column name to use when updating a record
            verbose: override default for printing query information (prints if True)
            readonly: don't execute SQL statements that modify the database
        Notes:
            The required key names and value descriptions in geom_col_info are:
            'col_sql': the SQL fragment representing the geometry including any coordinate system
                       transformations needed. For example: 'ST_GeomFromText(POINT(%s %s), %s)'
            'sheet_cols': tuple of column names corresponding to the geometry values found in the
                          col_names parameter. For example: (point_x, point_y, point_epsg) which
                          are the X, Y, and EPSG column names for a point
            'table_column': the geometry column name in the target table
        """
        if verbose is None:
            verbose = self._verbose

        table_name = A2Database._sqlstr(table_name)
        primary_key = A2Database._sqlstr(primary_key) if primary_key is not None else None

        # Setup the column names and values including any geometry columns
        if geom_col_info:
            # Without geom column
            query_cols = list((one_name for one_name in col_names if \
                                                one_name not in geom_col_info['sheet_cols']))
            query_types = list(('%s' for one_name in query_cols))
            query_values = list((col_values[col_names.index(one_name)] \
                                    for one_name in query_cols if \
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
            query += ', '.join((f'{A2Database._sqlstr(query_cols[idx])}={query_types[idx]}' \
                                        for idx in range(0, len(query_cols)) \
                                            if query_cols[idx].lower() != primary_key.lower()))
            query += f' WHERE {primary_key} = %s'

            # Remove the primary key from the regular list of values
            primary_key_index = next((idx for idx in range(0, len(query_cols)) \
                                            if query_cols[idx].lower() == primary_key.lower()))
            query_values = query_values[:primary_key_index] + query_values[primary_key_index+1:]
            query_values = list(query_values)+list((col_values[col_names.index(primary_key)],))
        else:
            query = f'INSERT INTO {table_name} (' + \
                            ','.join((A2Database._sqlstr(one_col) for one_col in query_cols)) + \
                            ') VALUES (' + \
                            ','.join(query_types) + ')'

        # Run the query
        if verbose:
            print(query, query_values, flush=True)

        if not readonly:
            self._cursor.execute(query, query_values)
            self._cursor.reset()
