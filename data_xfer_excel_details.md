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
The amount of information displayed and saved is much greater when using the `--verbose` flag.

## Parameters
More information on each of the paramters follows the table below.

Run the following command to see all the options with any default values.

```bash
./data_xfer_excel.py -help
```

| Flag              | Alternate form | Description |
| :---------------- | :------------: | :---------- |
| --esri_client_id  | -ec | The Client ID of the ESRI application to connect through |
| --esri_endpoint   | -ee | The URL endpoint to connect to for the database schema and the data |
| --esri_feature_id | -ef | The feature ID to create a schema for |
| -excel_file       |    |  |
| --host            | -o |  |
| --database        | -d |  |
| --user            | -u |  |
| --force           | -f | See the [force](#force-flag) flag details below |
| --verbose         |    |  |
| --password        | -p |  |
| --header          |    |  |
| --col_names_row   |    |  |
| --col_names       |    |  |
| --col_name_map    |    |  |
| --point_cols      |    |  |
| --geometry_epsg   |    |  |
| --database_epsg   |    |  |
| -key_name         | -k |  |
| --reset           |    |  |
| --log_filename    |    |  |
| --map_name        | -m  | Maps a table name to a new name. Can specify multiple times |

#### Additional flag details
