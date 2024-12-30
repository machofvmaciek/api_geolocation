"""Module responsible for creating table with inserting a basic record."""
import sqlite3
import os

# TODO: os.getenv to get the docker variable stroing databse connection string
_PATH_DATABASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resources", "db", "dev.db")

QUERY_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS geolocation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT NOT NULL,
    country TEXT,
    region TEXT,
    city TEXT,
    zip INTEGER,
    latitude REAL,
    longitude REAL
);
"""
try:
    # Connect to a database (create if does not exists)
    connection = sqlite3.connect(_PATH_DATABASE)

    cursor = connection.cursor()

    # Clear the already existing table 
    cursor.execute("DROP TABLE IF EXISTS geolocation")

    # Create table
    cursor.execute(QUERY_CREATE_TABLE)

    query_insert = """
    INSERT INTO geolocation (ip_address, country, region, city, zip, latitude, longitude)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    cursor.execute(query_insert, ("192.000.000.000", "Poland", "Silesia", "Katowice", 40514, 34.04, -118.02))

    # Commit the changes and close the connection
    connection.commit()

    cursor.execute("SELECT * FROM geolocation")
    ans = cursor.fetchall()
    print(ans)

except sqlite3.Error as exc:
    print(f"Exception occured '{exc}'")

finally:
    if connection:
        connection.close()
