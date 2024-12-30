"""WiP state.
Module responsible for fetching the data from ipstack api into SQLite database."""
import os
import requests
import sqlite3

from random import randint

# TODO: os.getenv to get the docker variable stroing databse connection string
_PATH_DATABASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resources", "db", "dev.db")

# TODO: change this into env variable
_API_KEY = "<insert_your_api_key>"
_API_BASE_URL = "http://api.ipstack.com/"

IP_PLACEHOLDER = "<country>.112.105.<detail>"

FILE_RAW_DATA = "/Users/machofv/Projects/api_geolocation/resources/api/raw_data.txt"

def __get_geolocation(ip_or_url: str, access_key: str = os.getenv("NOT_YET_EXISTING")):
    url = f"{_API_BASE_URL}{ip_or_url}?access_key={access_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

def __write_to_file(data: str) -> None:
    if data:
        # TODO: add exception raise
        with open(FILE_RAW_DATA, "a+") as file:
            # TODO: add append to a new line
            file.write(data)

def __fetch_to_db(connection, cursor, data) -> None:
    query_insert = """
    INSERT INTO geolocation (ip_address, country, region, city, zip, latitude, longitude)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    cursor.execute(query_insert, ("192.000.000.000", "Poland", "Silesia", "Katowice", 40514, 34.04, -118.02))

    cursor.execute(
        query_insert,
        (
            data["ip"],
            data.get("country_name"),
            data.get("region_name"),
            data.get("city"),
            int(data.get("zip")),
            float(data.get("latitude")),
            float(data.get("longitude"))
        )
    )
    connection.commit()
    
try:
    #  Connect to a database (create if does not exists)
    connection = sqlite3.connect(_PATH_DATABASE)
    cursor = connection.cursor()

    for i in range(1):
        ip = IP_PLACEHOLDER.replace("<country>", str(randint(1,99))).replace("<detail>", str(randint(1,99)))
        print(f"IP to fetch '{ip}'")

        # Get the geolocation data from API
        data = __get_geolocation(ip, _API_KEY)

        if not data:    
            print(f"Could not fetch data for '{ip}'")
            continue

        # Write to file as a backup
        __write_to_file(str(data))

        # Fetch into DB
        __fetch_to_db(connection, cursor, data)

        cursor.execute("SELECT * FROM geolocation")
        ans = cursor.fetchall()
        print(ans)

    
except sqlite3.Error as exc:
    print(f"DB Exception occured '{exc}'")
# ...

finally:
    if connection:
        connection.close()
        