# About
This project has the scripts that can help you move your AGOL data to a MySQL database.

# Creating/Recreating a Schema
AGOL provides JSON data that is used to crerate the MySQL database schema.
It's necessary to have the JSON in a file to provide to the script.

## Getting the Schema JSON
Follow the following steps to get the schema JSON into a file
1. First log onto your AGOL account and navigate to your Content - it should be a tab at the top of the page
2. Click the **Title** to the left of the *Feature Layer* you want. There may be several entries with the same title, only one of them should be the *Feature Layer*
3. On the new page, scroll to find the **URL** label
4. Click on the *View* button that's near the **URL** label. If there isn't a *View* button, open the URL in another tab by copying and pasting
5. A page with the title of "ArcGIS REST Services Directory" will open. There will be a **JSON** link on the left side, near the title. Click the **JSON** link to view the JSON
6. Click once in the black box containing the JSON and select all the text. On Windows that will be <CMD>+A, on MacOS that will be <COMMAND>+A. Only the text in the black box should be highlighted. If all the text on the page is highlighted, click in the black box and try again
7. Copy the JSON from the web page and open your favorite text editor. Paste the JSON fromr the clipboard in the editor and save the JSON

## Prerequisites
The scripts in this repository use Python3.10 or later.
To check what Python version you have, open a console window and type the following command.
```bash
python3 --version
```
To ensure you have all the needed Python modules installed you can run the [pip3](https://pip.pypa.io/en/stable/) command.
The following command will attempt to install the required Python modules.
You can find the [requirements.txt](https://github.com/Chris-Schnaufer/agol2mysql/blob/main/requirements.txt) file in this repository.
```bash
pip3 install -r requirements.txt
```

## Creating the Database Schema
The [create_db.py](https://github.com/Chris-Schnaufer/agol2mysql/tree/main) script is used to create the database schema from the [Schema JSON](#getting-the-schema-json) file.

Open a command window and run the following command to see all the options available when running this script
```bash
./create_db.py -h
```

This example creates the schema in a new database that is local to the machine.
```bash
# Replace schema.json with the path and name of your JSON file
./create_db.py -u myusername -p schema.json
```
When running this script you will be prompted to enter your database password before the schema is updated.

If the database is on another machine, you will need to specify the address of the host.
In this example we specify both the host name and the database name to create the schema in.
```bash
# Replace remote-host, my_database, and schema.json with the correct values
./create_db.py -u myusername -p -o remote-host -d my_database schema.json
```
As before, you will be prompted to enter your password.

Notes on the **--force** flag.

Always back up your database before using this flag!

Specifying the '--force' flag will delete tables, indexes, foreign keys, and associated data which match the schema to be created.
Database objects that reference the new schema are also impacted; for example, a foreign key using a table to be deleted will also be deleted.
Database objects that have no connection to the new schema will be left alone.

In this final example we force the destructive recreation of the database schema by specifying the `--force` flag.

```bash
# Dangerous command that will remove database data and objects that match the schema being created
# Replace remote-host, my_database, and schema.json with the correct values
./create_db.py -u myusername -p -o remote-host -d my_database --force schema.json
```

## Populating the Database
The [data_xfer_excel.py](https://github.com/Chris-Schnaufer/agol2mysql/tree/main) script is used to populate the database using data downloaded fom AGOL as an Excel spreadheet.

By default only new data is added to the database.
If a primary key is specified on the command line it is used to determine if the data is already in the database.
Otherwise all the columns are checked for matching data and added if the data doesn't match an existing row.

To see all the options available with this script along with any default command line values, open a command window and run the following command.
```bash
./data_xfer_excel.py -h
```

The following command adds new data into the database (which is on the local machine).
Data that already exists in the database is left alone.
```bash
# Replace data.xlxs with the name of your file
./data_xfer_excel.py -u myusername -p data.xlxs
```

This next example adds new data and forces existing data to be updated.
Rows to be updated are determined when the specified primary key in the spreadsheet matches one or more rows in the database.
```bash
# Replace primary_key and data.xlxs with your primary key column name and file
./data_xfer_excel.py -u myusername -p --force --key_name primary_key data.xlxs
```

Notes on the **--force** flag.

Always back up your database before using this flag!
The use of this flag when populating the database will cause existing data to be updated to new values; the old values are replaced.
