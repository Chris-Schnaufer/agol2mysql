# Overview
The [create_db.py](https://github.com/Chris-Schnaufer/agol2mysql/blob/main/create_db.py) script is able to create and update a database schema.
The script can use the JSON definition from AGOL, or it can query AGOL with a feature ID for the information.

## Command Example
The following example will download the definition from AGOL directly.
The user is prompted for the database password first, will then need to log onto AGOL through the provided browser window, and then enter the AGOL login code.

```bash
# Replace myusername, remote-host, and my-database with your values
./create_db.py -u myusername -p -o remote-host -d my-database
```

## Outputs
Various information is displayed as the script runs.
This information is also saved to the `create_db.log` file unless the log filename is changed (see [Parameters](#parameters) below).
The amount of information displayed and logged is much greater when using the `--verbose` flag.

## Parameters
More information on each of the paramters follows in the table below.

Run the following command to see all the options with any default values.

```bash
./create_db.py -help
```

| Flag              | Alternate form | Description |
| :---------------- | :------------: | :---------- |
| --database        | -d  | The name of the database on the server to use after connecting |
| --esri_client_id  | -ec | The Client ID of the ESRI application to connect through |
| --esri_endpoint   | -ee | The URL endpoint to connect to for the database schema and the data |
| --esri_feature_id | -ef | The feature ID to create a schema for |
| --force           | -f  | See the [force](#force-flag) flag details below |
| --geometry_epsg   |     | The [EPSG](https://spatialreference.org/ref/epsg/) code of any geometry columns in the database |
| -help             |     | Display help |
| --host            | -o  | The host name or IP address of the database server |
| --ignore_missing_cols |     | Ignore columns that exist in the database but not in the ESRI schema |
| -json_file        |     | The ESRI JSON file to base the schema off of |
| --log_filename    |     | An alternate logging file name |
| --map_name        | -m  | Maps a table name to a new name. Can specify multiple times |
| --noviews         |     | Don't create views associated with the tables |
| --password        | -p  | Prompt for the database password. Otherwise no password is used to connect to the database|
| --readonly        |     | Don't make any changes to the database. Can be used to "test-run" what would get changed in the database |
| --user            | -u  | The database user to log in with |
| --verbose         |     | Display additional information while processing schema |

#### Additional flag details
This section contains additional information on select flags that might have greater consequences than expected.

##### force flag
WARNING: using this flag can cause data to be lost forever! Back up your data before using this flag.

Forces a change to the database schema; tables and associated schema elements are deleted and recreated

The force flag will cause the schema to be recreated in the database.
Only database schema objects that are defined in the JSON file, or pulled down from AGOL, are impacted.

All relevant tables, indexes, foreign key constraints, and data are deleted.
Any database objects that reference these items may need to be restored, or may work differently.
This includes triggers, functions, and stored procedures.

##### ignore_missing_cols flag
By default, processing a table that has a column not in the JSON definition will halt the script.
This flag will indicate that the script should continue after detecting that a column has been removed.
This is done so that data isn't lost by removing a column.
The column can be manually removed from the table when desired.

Any new columns in the definition are added to the table and don't stop the script from running.

##### map_name flag
This flag is used to map a changed table name to an existing table name.
The intent is to make it easy to keep using the same table name in the database even though the name has changed in AGOL.

The format of this flag is `--map_name "<previous_name>=<new_name>`.
The previous name will be used for the database and the new name is the AGOL name.

The table name in the database can also be changed to match the new name so that this flag isn't needed.

This flag can be specified multiple times, or none times, on the command line.

##### noviews flag
This flag prevents views from being created for tables in the database.

When a table is created, an associated view is also created.
The purpose of the view is to resolve foreign keys for a record, and to expand geometries.

Foreign keys are "pointers" into another table for a specific value (or row, we don't use a row).
The view will have performed any needed lookups and display the correct values, instead of the foreign key.
For example, a foreign key of 'N' could be mapped to 'None'; the view would display 'None'.

Geometries are geo-located objects in the database that are not human readable, but are handy for spatial searches.
The view will display the X, Y, and EPSG codes of the geometries so those values are easier to access.
Currently, only POINT geometries are supported.
