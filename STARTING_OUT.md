This document contains information on what's needed to get started with the Red Squirrel MySQL database

## Connection Information

To acceess the database you will need the following information which will be provided using a secure method, such as [Stache](https://stache.arizona.edu/)

- An active [CALS](https://cales.arizona.edu/) VPN connection
- The address and port number of the MySQL server
- The username and password to use to access the data in the database
- The name of the database (redsq)

The server and user information will be provided via a secure method 

## Using MySQL Workbench

First, download [MySQL Workbench](https://www.mysql.com/products/workbench/) to your machine and install it using the MySQL provided instructions.
This can be skipped if you already have MySQL Workbench installed

### Specify a Connection

Open the [Setup New Connection](https://dev.mysql.com/doc/workbench/en/wb-getting-started-tutorial-create-connection.html) dialog by clicking the '+' sign next to "MySQL Connections"

- Set *Connection Name* to "Red Squirrel" (without the double quotes)
- Change *Hostname*, *Port*, and *Username* to what was provided to you
- You can save the password in the Keychain if desired, otherwise you will need to provide the password each time you log into the server
- Use "redsq" for *Default Schema* (without the double quotes)

Before dismissing the dialog, test the connection to confirm that the information was correctly entered

### Running a query

On the [Home Screen](https://dev.mysql.com/doc/workbench/en/wb-home.html) tab, click on the **Red Squirrel** tile to connect to the database

If necessary, open a [SQL Query tab](https://dev.mysql.com/doc/workbench/en/wb-sql-editor.html) 

Enter your query into the *SQL Query Panel*.
For example,
```sql
SELECT * FROM cvd_age;
```

Click the *Execute* button to run the query (represented by a plain lightning bolt)
