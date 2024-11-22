# Overview
The [data_xfer_excel.py](https://github.com/Chris-Schnaufer/agol2mysql/blob/main/data_xfer_excel.py) script is able to load data from an ESRI Excel file, or directly from AGOL using a feature ID, into the database.

## Command Example
The following example will download the data from AGOL directly.
The user is prompted for the database password first, will then need to log onto AGOL through the provided browser window, and then enter the AGOL login code.

```bash
# Replace remote-host, my-database, and data.xlxs with your values
./data_xfer_excel.py -u myusername -p -o remote-host -d my-database
```

## Outputs
Various information is displayed as the script runs.
This information is also saved to the `data_xfer_excel.log` file unless the log filename is changed (see [Parameters](#parameters) below).
The amount of information displayed and logged is much greater when using the `--verbose` flag.

## Parameters
More information on each of the paramters follows in the table below.

Run the following command to see all the options along with any default values.

```bash
./data_xfer_excel.py -help
```

| Flag              | Alternate form | Description |
| :---------------- | :------------: | :---------- |
| --col_names       |     | Comma separated list of column names to use when they aren't specified in the Excel file |
| --col_name_map    |     | Maps a column name to a new name. Can specify multiple times |
| --col_names_row   |     | The row in the spreadsheet that contains the names of the columns |
| --database        | -d  | The name of the database on the server to use after connecting |
| --database_epsg   |     | The [EPSG](https://spatialreference.org/ref/epsg/) code of the shapes in the database |
| --esri_client_id  | -ec | The Client ID of the ESRI application to connect through |
| --esri_endpoint   | -ee | The URL endpoint to connect to for the database schema and the data |
| --esri_feature_id | -ef | The feature ID to create a schema for |
| -excel_file       |     | The name of the Excel to load data from |
| --force           | -f  | See the [force](#force-flag) flag details below |
| --geometry_epsg   |     | The [EPSG](https://spatialreference.org/ref/epsg/) code of the spreadsheets geometry |
| --header          |     | The count of header rows in the spreadsheet to skip over |
| --host            | -o  | The host name or IP address of the database server |
| -key_name         | -k  | The name of the primary key column in the spreadsheet |
| --log_filename    |     | An alternate logging file name |
| --map_name        | -m  | Maps a table name to a new name. Can specify multiple times |
| --password        | -p  | Prompt for the database password. Otherwise no password is used to connect to the database|
| --point_cols      |     | The spreadsheet column names for the X and Y values of a point |
| --reset           |     | See the [reset](#reset-flag) flag details below  |
| --user            | -u  | The database user to log in with |
| --verbose         |     | Display additional information while processing schema |

#### Additional flag details
This section contains additional information on select flags that might have greater consequences than expected.

##### col_names_map flag
This flag is used to map a changed column name to an existing column name.
The intent is to make it easy to keep using the same column names in the database even though the name has changed in AGOL.

The format of this flag is `--col_names_map "<previous_name>=<new_name>`.
The previous name will be used for the database and the new name is the AGOL column name.

The column name in the database can also be changed to match the new name so that this flag isn't needed.

This flag can be specified multiple times, or none times, on the command line.

##### force flag
WARNING: using this flag can cause data to be lost forever! Back up your data before using this flag.

Forces the update of the data in the database.
By default, only new records are added to the database tables.

When changes are made to the AGOL data, specifying the `--force` flag will cause an additional check to be made against the database.
If the check shows that the AGOL data is newer, the asssociated database entry will be updated.

All new records that are found will be added to the database.

##### key_name flag
Specifies the name of the database primary key column in the spreadsheet.
This key is used to perform a data lookup when detecting if a row is in the database.

When this flag isn't used, a full row lookup is used to determine if the data already exists.

##### map_name flag
This flag is used to map a changed table name to an existing table name.
The intent is to make it easy to keep using the same table name in the database even though the name has changed in AGOL.

The format of this flag is `--map_name "<previous_name>=<new_name>`.
The previous name will be used for the database and the new name is the AGOL name.

The table name in the database can also be changed to match the new name so that this flag isn't needed.

This flag can be specified multiple times, or none times, on the command line.

##### point_cols flag
This flag is used to specify the spreadsheet's column names of a point's X and Y values.

The format of this flag is `--point_cols "<X column name>, <Y column name>"`.
The X and Y values will be combined with the EPSG code to create or update a point in the database.

The spreadsheet point's coordinate system (see --geometry_epsg) will be converted to the database's if needed.

##### reset flag
WARNING: this flag can cause data to be lost forever! Back up your data before using this flag.

When this flag is specified, the existing data in the table is deleted before the spreadsheet data is uploaded.
The existing data is deleted regardless of whether the upload of spreadssheet data is successful, or not.
