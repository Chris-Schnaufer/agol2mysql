# Data Migration

The legacy data was stored in Access Databases.
The data was migated from these databases by first exporting to Excel, then uploading to MySQL, and finally merged with the new Survey123 data.

The merged legacy records can be identified by their `objectid` values which start at 1000000000.

## Excel Spreadsheet Requirements

The Excel workbook needs at least two tabs, or spreadsheets.
The workbook can have multiple data spreadsheets, but needs to have another spreadsheet that describes the data being uploaded.
Extra spreadsheets that are not used for uploading data can be in the workbook and are ignored.

Another important workbook requirement is that the spreadsheets also need to be named uniquely.
It's helpful to name each spreadsheet after the table the data came from, or some other meaningful name.

The data spreadsheets don't have any restictions.
While not required, it's helpful for the columns to have a header line where they are named.

The data format spreadsheet is expected to have a minimum of four columns; these are `table name`, `field name`, `type`, and `size`.
An optional description column can also be defined which provides additional information on the field.
These column names are suggestions and can be called anything.

- *table name*: is the name of the spreadsheet (tab) that the fields are for
- *field name*: is the column name being described
- *type*: the data type of that column
- *size*: is the size of the data type, when it's relevent (such as with text columns)

For example, the following tables show the contents of a sample data spreadsheet and the associated descriptions (which are in another spreadsheet).

Spreadsheet Name: **Cartoons**

| name   | age | occupation |
| ------ | --- | ---------- |
| Yogi   |  15 | bear       |
| Booboo |   7 | young bear |
| Felix  |   2 | cat        |


Spreadsheet Name: **Field Descriptions**

| table name | field name | type       | size |
| ---------- | ---------- | ---------- | ---- |
| Cartoons   | name       | Short Text |   50 |
| Cartoons   | age        | Integer    |      |
| Cartoons   | occupation | Short Text |   75 |

Note that the **Field Descriptions** spreadsheet can have entries for multiple data spreadsheets.

## Upload to MySQL

The `populate_from_excel.py` script is used to upload one spreadsheet's worth of legacy data from an Excel Workbook to MySQL.
Run the script one time for each data spreadsheet in the workbook that's to be uploaded.


#### Command Example

Here's a sample command line for uploading the **Cartoon** data to the database.

```
./populate_from_excel.py -u redsq_dba -p -d redsq -o rds-mysql.cals.arizona.edu -k "Type" -dt Cartoons -st "Field Descriptions" -stn "Table Name" -sfn "Field Name" -sft "Type" -sfd "Description" -sfl "Size" -sc 1 --geometry_epsg 26912 tblMasterPoints_NewFields_14Dec23.xlsx
```

When running the script, the user is prompted to enter the MySQL database password.
The command line parameters are in the [Parameters](#parameters) section.

#### Parameters

Information on the available parameters is in the table below.

It's recommended to run the following command to see all the available paramters and their default values.

```
./populate_from_excel.py -help
```

| Flag                    | Alternate form | Description |
| :---------------------- | :------------: | :---------- |
| excel_file              |      | The name of the Excel to load from |
| --database              | -d   | The name of the database on the server to use after connecting |
| --database_epsg         |      | The [EPSG](https://spatialreference.org/ref/epsg/) code of the geometry column in the database |
| --data_col_names_row    | -dn  | The header row that contains the column (field) names |
| --data_header           | -dh  | Number of header lines of the data spreadsheet (these are skipped) |
| --data_sheet_name       | -dt  | The spreadsheet name of the data to load |
| --debug                 |      | Increases the logging level to **DEBUG** (which produces many more messages) |
| --force                 | -f   | See the [force](#force-flag) flag details below |
| --geometry_epsg         |      | The [EPSG](https://spatialreference.org/ref/epsg/) code of the geometry in the data spreadsheet |
| -help                   |      | Display help |
| --host                  | -o   | The host name or IP address of the database server |
| --ignore_col            |      | Name of a column to ignore in the data spreadsheet. Can be specified multiple times. Can also be an index (starting at 1) |
| --key_name              | -k   | The name of the primary key column in the data spreadsheet |
| --log_filename          |      | An alternate logging file name |
| --no_primary            |      | Indicates that there is no primary key for the data spreadsheet |
| --noviews               |      | Do not create views into the created/updated database table. Views are created by default |
| --password              | -p   | Prompt for the database password. Otherwise no password is used to connect to the database|
| --pk_force_text         |      | Primary keys are expected to be integer values by default. This flag allows them to have unique text values |
| --point_cols            |      | The X and Y column names to use in creating a point geometry. eg: `--point_cols "\<x name\>,\<y name\>"` |
| --schema_col_names_row  | -sc  | The header row that contains the name of the columns in the schema spreadsheet |
| --schema_data_len_col   | -sfl | Name of column in schema spreadsheet that has the field data lengths. Can also be an index (starting at 1)|
| --schema_data_type_col  | -sft | Name of column in schema spreadsheet that has the field data types. Can also be an index (starting at 1) |
| --schema_description_col | -sfd | Name of column in schema spreadsheet that has the field descriptions. Can also be an index (starting at 1) |
| --schema_field_name_col | -sfn | Name of column in schema spreadsheet that has the field names. Can also be an index (starting at 1) |
| --schema_header         | -sh  | Number of header rows in the shema spreadsheet (these are skipped) |
| --schema_only           |      | Only create the database schema. Do not upload the data |
| --schema_sheet_name     | -st  | The name of the spreadsheet that contains the field definitions |
| --schema_table_name_col | -stn | Name of column in schema spreadsheet that has the table names. Can also be an index (starting at 1) |
| --user                  | -u   | The database user to log in with |
| --use_schema_cols       |      | All the columns in the data spreadsheet should be defined. It's an error if any are missing from the schema |
| --verbose               |      | Display additional information while processing schema |

##### Additional flag details
This section contains additional information on select flags that might have greater consequences than expected.
 
###### force flag
WARNING: using this flag can cause data to be lost forever! Back up your data before using this flag.

Forces a change to the database schema; tables and associated schema elements are deleted and recreated

The force flag will cause the schema to be recreated in the database.
Only database schema objects that are defined in the JSON file, or pulled down from AGOL, are impacted.

All relevant tables, indexes, foreign key constraints, and data are deleted.
Any database objects that reference these items may need to be restored, or may work differently.
This includes triggers, functions, and stored procedures.

###### noviews flag
This flag prevents views from being created for tables in the database.

When a table is created, an associated view is also created.
The purpose of the view is to resolve foreign keys for a record, and to expand geometries.

Foreign keys are "pointers" into another table for a specific value (or row, we don't use a row).
The view will have performed any needed lookups and display the correct values, instead of the foreign key.
For example, a foreign key of 'N' could be mapped to 'None'; the view would display 'None'.

Geometries are geo-located objects in the database that are not human readable, but are handy for spatial searches.
The view will display the X, Y, and EPSG codes of the geometries so those values are easier to access.
Currently, only POINT geometries are supported.

##### Primary Keys

There are three flags related to primary keys:

- `--key_name`: the column name in the data spreadsheet that contains the key values
- `--no_primary`: there isn't a primary key; specified when the data spreadsheet doesn't have a primary key column
- `--pk_force_text`: force the primary key to be text and not integer (its schema definition needs to be a text type)

If `--no_primary` is specified on the command line along with one or more of the other primary key flags, it is ignored.
