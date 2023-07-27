# About
This project has the scripts that can help you move your AGOL data to a MySQL database

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

## Creating the Schema
