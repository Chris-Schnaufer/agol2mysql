# About
This project has scripts that can move your AGOL ([ArcGIS Online](https://www.arcgis.com/index.html)) data to a MySQL database.

Refer to the [Starting document](STARTING_OUT.md) for information on connecting to the database with SQL Workbench and executing queries.

The scripts can be used in a less automated fasion (Manual) and a more automated fashion (Direct).
The sections below reflect that difference and are named as such.
The [Direct](#direct-steps) steps connect _directly_ to AGOL and automatically fetches the schema and the data.
Follow the [Manual](#manual-steps) steps if you have AGOL schema JSON files and/or AGOL exported Excel files.

There are also [Example Situations](#example_situations) documented for many common scenarios.
For uncommon scenarios, and for certain documented scenarios, manual intervention with the MySQL database may be required.

Finally, an example of [connecting to the database](#connecting-to-the-database) using [R](https://www.r-project.org/about.html) is provided.

Support inforrmation can be found on [Google Drive](https://docs.google.com/document/d/11V0e99n5_L4HjAJUwkyvUcDpMk17nP9eGEfhQYizxcA/edit?usp=sharing).

# Prerequisites

### Python
[Python](https://www.python.org/) is a widely used programming language that has many applications.
The scripts in this repository use Python to access AGOL, retrieve data stored there, and use the data to change/update a MySQL database.

Note that the `arcgis` package might not use the latest version of Python.
At the time this README was written, Python 3.11 was the latest version ESRI supported.

The scripts in this repository use Python3.10 or later.
To check what Python version you have, open a console (or terminal) window and type the following command.
```bash
python3 --version
```

If Python is not installed on your system, or if you need to upgrade your version of Python, it's available for [download](https://www.python.org/downloads/).
Generally, the latest release is the only one that has installers which can be downloaded and used.
Some operating systems, such as **Ubuntu 24.04.1 LTS**, have their own mechanisms for installing and updating Python and can be used instead of downloads.

To ensure you have all the needed Python modules installed you can use [pip3](https://pip.pypa.io/en/stable/) to install what's missing.
The following command will attempt to install the required Python modules.
You can find the [requirements.txt](requirements.txt) file in this repository.
This file contains the names of additional Python modules that are used by the scripts.
```bash
pip3 install -r requirements.txt
```

If you don't have `pip3` on your system, you will have to install it.

You may also need to install some system requirements before you are able to finish installing these python modules.

If you are experiencing problem when the `arcgis` module is being installed, check your Python version number against what this module supports.
It's possible that your Python version is too new (or too old) for the module.

If you are using a MySQL database that's **earlier than version 8** you will also need to install [GDAL](https://gdal.org/download.html) and [pygdal](https://pypi.org/project/pygdal/).
These are used to convert geometric data between coordinate systems, and other features as well.
Note that installing GDAL can be difficult and complicated.

# AGOL Configuration

AGOL has security features that can be used to restrict and permit users from one account to access the data from another account.
When using the scripts to access data where permission has been granted, an application needs to be created on AGOL.
It's through this application that the scripts are able to access the data.
The application won't be needed if the account used with the scripts is the owner of the data.

### Creating an AGOL Application
Select the **Content** tab after logging into AGOL with your browser.

1. Click the *New Item* button to start creating an application that allows the scripts to access data
2. Click the *Application* button to open the Application type window
3. Select the *Other Application* option and click the **Next** button
4. Fill in the form's fields as directed, including a meaningful title and click the **Save** button

After the application is created you will be directed to a page where information on the application is shown, including the *Client ID*.
This *Client ID* is needed by the scripts to access the data.

# Scripts

The following Python scripts are used when loading ESRI data into the MySQL database.

[create_db.py](create_db.py) creates or updates the database schema.
More information on the script parameters are documented in [create_db_details.md](create_db_details.md).

[data_xfer_excel.py](data_xfer_excel.py) loads and updates data into the database.
More information on this script's parameters can be found in [data_xfer_excel_details.md](data_xfer_excel_details.md).

For loading legacy data the [populate_from_excel.py](populate_from_excel.py) python script is used.
Caution must be used with this script so that legacy data doesn't overwrite the existing data that's in same-named tables.
More information on this script is available in the data_migration [README.md](data_migration).

The script [a2database.py](a2database.py) is used by the other scripts to access the MySQL database and cannot be run on its own.

# Direct Steps
The steps here can be used to directly access ESRI schemas and data.

## Creating/Updating a Schema

The [create_db.py](create_db.py) script is able to directly connect to ESRI and use the [Feature](https://support.esri.com/en-us/gis-dictionary/feature) schema to create and update the database schema.
A detailed explanation of the options available with this script is [available](create_db_details.md).

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
You will also need to log into AGOL via a new browser window and use the code provided to give the script access to the schema data.

If the database is on another machine, you will need to specify the address of the host on the command line.
In this next example we specify both the host and database names within which the schema is created.
```bash
# Replace myusername, remote-host, and my-database with your values
./create_db.py -u myusername -p -o remote-host -d my-database
```
As with the previous command, you will be prompted to enter your database password and to provide the AGOL code after logging into AGOL via a new browser window.

**NOTE**: See the section on using the [--force](#create_db_force) flag with the *create_db.py* script for important warnings on its use.

## Getting the data
The [data_xfer_excel.py](data_xfer_excel.py) script is used to populate the database.
It can be used to download data directly from AGOL and update/populate the database.

By default only new data is added to the database.
If a primary key is specified on the command line it is used to determine if the data is already in the database.
Otherwise all the columns are checked for a matching row and added to the database if a match isn't found.

To see all the options available to this script, along with any default command line values, open a command window and run the following command.
```bash
./data_xfer_excel.py -h
```
A detailed explanation of the options available with this script is [available](data_xfer_excel_details.md).

The following command adds new data to the database on the local machine.
Data that already exists in the database is left alone.
```bash
# Add new data to the database on the local machine
./data_xfer_excel.py -u myusername -p 
```
You will be prompted to enter your database password and to provide the AGOL code after logging into AGOL via a new browser window.

If the database is on another machine, you will need to specify the address of the host on the command line.
In this next example we specify both the host and database name where the new data will be added.
```bash
# Replace myusername, remote-host and my-database with your values
./data_xfer_excel.py -u myusername -p -o remote-host -d my-database
```
As with the example above, you will be prompted to enter your database password and to provide the AGOL code after logging into AGOL via a new browser window.

**NOTE**: See the section on using the [--force](#populate_db_force) flag with the *data_xfer_excel.py* script for important warnings on its use.

# Manual Steps
Use the steps here if you want to use an ESRI JSON schema file and/or an ESRI-exported Excel spreadsheet file.

## Creating/Updating a Schema
[AGOL](https://www.arcgis.com/index.html) provides JSON data that is used to create the MySQL database schema.
It's necessary to have this JSON in a file for the script.

### Getting the Schema JSON
Follow the following steps to get the schema JSON into a file
1. First log onto your AGOL account and navigate to your **Content** - it should be a tab at the top of the page
2. Click the `Title` to the left of the *Feature Layer* you want. There may be several entries with the same title, only one of them should be a *Feature Layer*
3. On the new page, scroll down to find the `URL` label
4. Click on the *View* button that's near the `URL` label. If there isn't a **View** button, open the displayed URL in another broser tab by copying and pasting it
5. On the new page there will be a JSON link on the left side, near the title. Click the **JSON** link to view the JSON
6. Click once in the black box containing the JSON and select all the text. On Windows you can use \<CMD\>+A, on MacOS you can use \<COMMAND\>+A. Only the JSON text in the black box should be highlighted. If all the text on the page is highlighted, click in the black box and try again
7. Copy the JSON from the web page and open your favorite text editor. Paste the JSON into the editor and save the JSON as a file

### Creating the Database Schema
The [create_db.py](create_db.py) script is used to create the database schema from the [Schema JSON](#getting-the-schema-json) file.
A detailed explanation of the options available with this script is [available](create_db_details.md).

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

#### Notes on using the **--force** flag <a id="create_db_force" />

Always back up your database before using this flag!

Specifying the `--force` flag will delete tables, indexes, foreign keys, and their associated data when they match the schema objects being created.
Database objects that reference the new schema will also be impacted; for example, a foreign key referencing a re-created table will also be deleted.
Database objects that have no connection to created schema objects will be left alone.

In the final example for this section we force the destructive recreation of the schema objects by specifying the `--force` flag.

```bash
# Dangerous command that will remove database data and objects matching the schema being created
# Replace myusername, remote-host, my-database, and schema.json with the correct values
./create_db.py -u myusername -p -o remote-host -d my-database --force schema.json
```

## Populating the Database
The database can be populated with the data stored on [AGOL](https://www.arcgis.com/index.html) after it's been downloaded as an Excel spreadsheet.

### Downloading the Data
The following steps can be used to download the data from AGOL
1. First log onto your AGOL account and navigate to your **Content** - it should be a tab at the top of the page
2. Click the `Title` to the left of the *Feature Layer* you want. There may be several entries with the same title, only one of them should be a *Feature Layer*
3. On the right side of the new page, find the **Export Data** button (you can find it on the *Overview* page)
4. Click the **Export Data** button and then click the **Export to Excel** option to begin downloading the data

### Adding/Updating Data to the Database
The [data_xfer_excel.py](data_xfer_excel.py) script is used to populate the database using [data downloaded](#downloading-the-data) from AGOL as an Excel spreadheet.

By default only new data is added to the database.
If a primary key is specified on the command line it is used to determine if the data is already in the database.
Otherwise all the columns are checked for a matching row and added to the database if a match isn't found.

To see all the options available to this script, along with any default command line values, open a command window and run the following command.
```bash
./data_xfer_excel.py -h
```
A detailed explanation of the options available with this script is [available](data_xfer_excel_details.md).

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

#### Notes on the **--force** flag  <a id="populate_db_force" />

Always back up your database before using this flag!

The use of this flag will cause data that was changed on AGOL to be updated in the database; the old values are replaced with the changed values.

This next example adds new data and forces existing data that was modified on AGOL to be updated in the database.
The database is running on the current machine.
```bash
# Replace primary_key and data.xlxs with your primary key column name and file name
./data_xfer_excel.py -u myusername -p --force --key_name primary_key data.xlxs
```

# Example Situations

### Survey name changes
There are times when you might want to save an updated survey under a new name.
The scripts that create the schema in the MySQL database use the Survey Name as part of the main table (it's encoded in the JSON fetched from AGOL).
When the data gets pulled down from the updated survey under the new name, there's a mismatch due to the name change.

By specifying the `--map_name` (or the `-m` equivelent) switch on the command line it's possible to map the new AGOL name to the old MySQL name.
```bash
# Example for mapping a new ESRI table name to an old one in MySQL
# This example maps the new table new 'MySurvey New' to 'MySurvey'
./data_xfer_excel.py -m "MySurvey New=MySurvey" -u myusername -p -o remote-host -d my-database
```
When the scripts encounter the new name it will be mapped to the old name and the old name is then used for the database operations.
The `--map_name` flag can be specified multiple times on the command line to map additional table names.

NOTE: it's also possible to change the name of the table in the MySQL data.
This may be a good option if the impact of changing the MySQL table name is acceptable.
For example, is it easy to change all the SQL commands?

### Changed data
Sometimes it's necessary to change the data that's stored on AGOL.
These changes then need to be reflected in the MySQL database.

Once solution is to manually change the MySQL database.
With the right tool, such as [dbeaver](https://dbeaver.io/) or [MySQL Workbench](https://www.mysql.com/products/workbench/), this might be easy to do.

The `data_xfer_excel.py` script is also able to update the data in the database, meaning you only need to change it in AGOL and run the script.
The MySQL database will be updated with the changes made.

Normally tables are only updated with new records.
The script checks if the primary key is already in the MySQL database, and the row is added if the key is not found.
If the primary key is found, that row is left alone and the script continues.

When the `--force` flag is specified and the primary key is found, an additional check is made to see if the data has changed.
If the data has changed, the row is updated.
New rows are added to the table as usual.

```bash
# Example of forcing updates to existing rows that've changed (any new rows will be added)
./data_xfer_excel.py --force -u myusername -p -o remote-host -d my-database
```

### Deleting MySQL rows
There may be occasions when a row in AGOL needs to be deleted.
In these cases, it's necessary to manually delete the row from the MySQL database.

A decision was made to not include this functionality in the scripts since data deletion is destructive and automating this could result in permenantly lost data.
For example, if the wrong row in AGOL is deleted, the data could be recovered from the MySQL database.
Likewise, if the wrong row in MySQL is deleted, the next `data_xfer_excel.py` run will update the MySQL database from AGOL and the data restored.

### Adding, modifying, and deleting Survey123 fields
The `create_db.py` script is resonsible for managing the MySQL database's schema (within certain limits).

The Survey123 editor is a dynamic application and allows the easy addition, modification and deletion of survey fields.
The `create_db.py` script can update the MySQL database in certain circumstances.

The main goal of the script is to protect the integrity of the database schema and data.
When something occurs that the script determines is outside of its scope, it will report the issue and may stop running.
When this happens, command line flags may be able to work around the issue, or manual intervention in the MySQL database might be required.

#### Adding
New columns are automatically added to table schemas in the database.
This means that as a survey matures, new tables and columns can be easily added to the MySQL database by running the script.

#### Modification
If the underlying data type of a field is unchanged, the Survey123 changes may be transparent to the database.

For example, changing a free form text field to a dropdown selection field most likely wouldn't require a change to the MySQL database.

A change from a text to an integer type is a more impactful change and may require a manual intervention in the database.
This is because the existing MySQL data might not be compatible with an integer type.

When the underlying data type changes, a manual update to the database schema and associated data may be needed.

#### Deletion
When a field in Survey123 is deleted, it's considered an error by the `create_db.py` script unless the `--ignore_missing_cols` flag is specified on the command line.
This flag allows legacy data to be kept around while protecting the schema.

If it is desirable to remove the column, it needs to be manually deleted from the table in the database.

#### Changing a field name
It's possible to change a field's name in Survey123.
This impacts the column that the data is stored under in the MySQL database.

The `data_xfer_excel.py` script can handle this situation with the `--col_name_map` flag.
Similarly to mapping table names, this flag maps an new AGOL field name to the older MySQL column name.

```bash
# Example mapping an AGOL column name to its MySQL name
./data_xfer_excel.py --col_name_map "New field name=MySQL_column_name" -u myusername -p -o remote-host -d my-database
```

Another option is to manually modify the MySQL database to update the column name.
Note that AGOL field names are transformed to a database-compatible name when necessary.
Spaces are converted to underscores(\_) and special characters are converted to periods (.).

# Connecting to the Database
A step-by-step example is given below using the [RMySQL](https://github.com/r-dbi/RMySQL) package.
The RMySQL package is being replaced by the [RMariaDB](https://github.com/r-dbi/RMariaDB) package.
More information on MariaDB can be found on their [website](https://mariadb.com/kb/en/rmariadb/).

The first step is to make sure the correct library is loaded for accessing a MySQL database.
```
# Import the library
library(RMySQL)
```

Next, provide connection and login information fo the database.
Replace all the values on the right side of the statement with your values.
```
# The connection settings
db_user <- 'your_name'
db_password <- 'your_password'
db_name <- 'database_name'
db_host <- '127.0.0.1' # IP address of server
db_port <- 3306
```

Connect to the database.
```
# Connect to the database
mydb <-  dbConnect(MySQL(), user = db_user, password = db_password,
                 dbname = db_name, host = db_host, port = db_port)
```

Run a query to obtain data from the database.
```
# Run a query
db_table <- 'your_data_table'
s <- paste0("select * from ", db_table)
rs <- dbSendQuery(mydb, s)
```

Fetch the data from the database.
```
# Fetch the data
df <-  fetch(rs, n = -1)
```

Optionally, disconnect from the database on exit.
You can also manually disconnect from the database
```
on.exit(dbDisconnect(mydb))
```
