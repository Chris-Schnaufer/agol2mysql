# About
This project has the scripts that can help you move your AGOL data to a MySQL database.

Refer to the [Starting document](https://github.com/Chris-Schnaufer/agol2mysql/blob/main/STARTING_OUT.md) for information on connecting to the database with SQL Workbenchand executing queries.

The scripts can be used in a less automated fasion (Manual) and a more automated fashion (Direct).
The sections below reflect that diffence and are names as such.
The [Direct](#direct-steps) steps connect directly to ESRI and automatically fetches the schema and the data.
Follow the [Manual](#manual-steps) steps if you have ESRI schema JSON files and/or ESRI exported Excel files.

# Prerequisites
The scripts in this repository use Python3.10 or later.
To check what Python version you have, open a console (or terminal) window and type the following command.
```bash
python3 --version
```
To ensure you have all the needed Python modules installed you can run the [pip3](https://pip.pypa.io/en/stable/) command.
The following command will attempt to install the required Python modules.
You can find the [requirements.txt](https://github.com/Chris-Schnaufer/agol2mysql/blob/main/requirements.txt) file in this repository.
This file contains the Python modules that need to be installed for the scripts.
```bash
pip3 install -r requirements.txt
```

You may need to install some system requirements before you are able to finish installing these python modules.

If you are using a MySQL database that's earlier than version 8 you will also need to install [GDAL](https://gdal.org/download.html) and [pygdal](https://pypi.org/project/pygdal/).
These are used to convert geometric data between coordinate systems, and other features as well.

# Scripts

The following Python scripts are used when loading ESRI data into the MySQL database.

[create_db.py](https://github.com/Chris-Schnaufer/agol2mysql/blob/main/create_db.py) creates or updates the database schema.
More information on the script parameters are documented in [create_db_details.md](https://github.com/Chris-Schnaufer/agol2mysql/blob/main/create_db_details.md).

[data_xfer_excel.py](https://github.com/Chris-Schnaufer/agol2mysql/blob/main/data_xfer_excel.py) loads and updates data into the database.
More information on this script's parameters can be found in [data_xfer_excel_details.md](https://github.com/Chris-Schnaufer/agol2mysql/blob/main/data_xfer_excel_details.md).

For loading legacy data the [populate_from_excel.py](https://github.com/Chris-Schnaufer/agol2mysql/blob/main/data_migration/populate_from_excel.py) python script is used.
Caution must be used with this script so that legacy data doesn't overwrite the existing data that's in same-named tables.
More information on this script it [TBD].

# Direct Steps
The steps here can be used to directly access ESRI schemas and data.

## Creating/Updating a Schema

The [create_db.py](https://github.com/Chris-Schnaufer/agol2mysql/blob/main/create_db.py) script is able to directly connect to ESRI and use the [Feature](https://support.esri.com/en-us/gis-dictionary/feature) schema to create and update the database.
A detailed explanation of the options available with this script is (available).

Open a command window and run the following command to see all the options available with this script
```bash
./create_db.py -h
```

The following command creates the schema in a database that is on the current machine.
```bash
# Replace myusername with your username
./create_db.py -u myusername -p 
```
When running this script you will be prompted to enter your database password.
You will also need to log into AGOL and use the code provided to give the script access to the schema data.

If the database is on another machine, you will need to specify the address of the host on the command line.
In this next example we specify both the host and database names within which the schema is created.
```bash
# Replace myusername, remote-host, and my-database with your values
./create_db.py -u myusername -p -o remote-host -d my-database
```
As before, you will be prompted to enter your database password and to provide the AGOL code after logging in to AGOL.

## Getting the data
The [data_xfer_excel.py](https://github.com/Chris-Schnaufer/agol2mysql/tree/main) script is used to populate the database.
It can be used to download data directly from AGOL and update/populate the database.

By default only new data is added to the database.
If a primary key is specified on the command line it is used to determine if the data is already in the database.
Otherwise all the columns are checked for a matching row and added to the database if a match isn't found.

To see all the options available to this script, along with any default command line values, open a command window and run the following command.
```bash
./data_xfer_excel.py -h
```
A detailed explanation of the options available with this script is (available).

The following command adds new data to the database on the current machine.
Data that already exists in the database is left alone.
```bash
# 
./data_xfer_excel.py -u myusername -p 
```
You will be prompted to enter your database password and to provide the AGOL code after logging in to AGOL.

If the database is on another machine, you will need to specify the address of the host on the command line.
In this next example we specify both the host and database names to where the new data will be added.
```bash
# Replace myusername, remote-host and my-database with your values
./data_xfer_excel.py -u myusername -p -o remote-host -d my-database
```
As before, you will be prompted to enter your database password and to provide the AGOL code after logging in to AGOL.

# Manual Steps
Use the steps here if you want to use an ESRI JSON schema file and/or an ESRI-exported Excel spreadsheet data file.

## Creating/Updating a Schema
[AGOL](https://www.arcgis.com/index.html) provides JSON data that is used to create the MySQL database schema.
It's necessary to have the JSON in a file provided to the script.

### Getting the Schema JSON
Follow the following steps to get the schema JSON into a file
1. First log onto your AGOL account and navigate to your Content - it should be a tab at the top of the page
2. Click the **Title** to the left of the *Feature Layer* you want. There may be several entries with the same title, only one of them should be a *Feature Layer*
3. On the new page, scroll down to find the **URL** label
4. Click on the *View* button that's near the **URL** label. If there isn't a `View` button, open the URL in another tab by copying and pasting it
5. On the new page there will be a `JSON` link on the left side, near the title. Click the `JSON` link to view the JSON
6. Click once in the black box containing the JSON and select all the text. On Windows you can use \<CMD\>+A, on MacOS you can use \<COMMAND\>+A. Only the JSON text in the black box should be highlighted. If all the text on the __page__ is highlighted, click in the black box and try again
7. Copy the JSON from the web page and open your favorite text editor. Paste the JSON from the clipboard into the editor and save the JSON as a file

### Creating the Database Schema
The [create_db.py](https://github.com/Chris-Schnaufer/agol2mysql/tree/main) script is used to create the database schema from the [Schema JSON](#getting-the-schema-json) file.
A detailed explanation of the options available with this script is (available).

Open a command window and run the following command to see all the options available with this script
```bash
./create_db.py -h
```

The following command creates the schema in a database that is on the current machine.
```bash
# Replace myusername with your username and schema.json with the path of your JSON file
./create_db.py -u myusername -p schema.json
```
When running this script you will be prompted to enter your database password.

If the database is on another machine, you will need to specify the address of the host on the command line.
In this next example we specify both the host and database names within which the schema is created.
```bash
# Replace myusername, remote-host, my-database, and schema.json with your values
./create_db.py -u myusername -p -o remote-host -d my-database schema.json
```
As before, you will be prompted to enter your password.

##### Notes on using the **--force** flag

Always back up your database before using this flag!

Specifying the '--force' flag will delete tables, indexes, foreign keys, and their associated data when they match the schema objects being created.
Database objects that reference the new schema will also be impacted; for example, a foreign key referencing a re-created table will also be deleted.
Database objects that have no connection to the created schema object will be left alone.

In this final example we force the destructive recreation of the schema objects by specifying the `--force` flag.

```bash
# Dangerous command that will remove database data and objects matching the schema being created
# Replace myusername, remote-host, my-database, and schema.json with the correct values
./create_db.py -u myusername -p -o remote-host -d my-database --force schema.json
```

## Populating the Database
The database can be populated with the data stored on [AGOL](https://www.arcgis.com/index.html) after it's been downloaded as an Excel spreadsheet.

### Downloading the Data
The following steps can be used to download the data from AGOL
1. First log onto your AGOL account and navigate to your Content - it should be a tab at the top of the page
2. Click the **Title** to the left of the *Feature Layer* you want. There may be several entries with the same title, only one of them should be a *Feature Layer*
3. On the right side of the new page, find the `Export Data` button (you can find it on the **Overview** page)
4. Click the `Export Data` button and then click the *Export to Excel* option to begin downloading the data

### Adding/Updating Data to the Database
The [data_xfer_excel.py](https://github.com/Chris-Schnaufer/agol2mysql/tree/main) script is used to populate the database using [data downloaded](#downloading-the-data) from AGOL as an Excel spreadheet.

By default only new data is added to the database.
If a primary key is specified on the command line it is used to determine if the data is already in the database.
Otherwise all the columns are checked for a matching row and added to the database if a match isn't found.

To see all the options available to this script, along with any default command line values, open a command window and run the following command.
```bash
./data_xfer_excel.py -h
```
A detailed explanation of the options available with this script is (available).

The following command adds new data to the database on the current machine.
Data that already exists in the database is left alone.
```bash
# Replace data.xlxs with the name of your file
./data_xfer_excel.py -u myusername -p data.xlxs
```
You will be prompted to enter your database password.

If the database is on another machine, you will need to specify the address of the host on the command line.
In this next example we specify both the host and database names to where the new data will be added.
```bash
# Replace remote-host, my-database, and data.xlxs with your values
./data_xfer_excel.py -u myusername -p -o remote-host -d my-database data.xlxs
```
As before, you will be prompted to enter your password.

##### Notes on the **--force** flag

Always back up your database before using this flag!

The use of this flag when populating the database will cause existing data to be updated to new values; the old values are replaced.

This next example adds new data and forces existing data to be updated.
Here, when the primary key in the spreadsheet matches one or more rows in the database those rows are updated.
The database is running on the current machine.
```bash
# Replace primary_key and data.xlxs with your primary key column name and file
./data_xfer_excel.py -u myusername -p --force --key_name primary_key data.xlxs
```
