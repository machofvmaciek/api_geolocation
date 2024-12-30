"""Module implementing API for ip addresses geolocation data."""

import os
import logging
import sqlite3

from typing import Generator, Annotated

from fastapi import FastAPI, HTTPException, Path, Query, Depends
from pydantic import BaseModel, Field, field_validator

# TODO: Add more robust logging

# TODO: os.getenv to get the docker variable stroing databse connection string
_PATH_DATABASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resources", "db", "dev.db")


app = FastAPI(
    title="machofv's geolocation data API.",
    description="This API serves purpose of inspecting, adding and modifing the IP-related data.",
    version="1.0.0",
)


class Record(BaseModel):
    """Representation of a record in the system."""

    ip_address: str = Field(description="ipv4 or ipv6 address.")
    country: str = Field(description="Country where the ip is located.")
    region: str = Field(description="Region of the country where the ip is located.")
    city: str = Field(description="Name of the city where the ip is located.")
    zip_code: int = Field(description="ZIP postal code of a city.")
    latitude: float = Field(description="North-south position coordinate.")
    longitude: float = Field(description="West-east position coordinate.")


class RecordInput(BaseModel):
    """Representation of the input record taken from client, involves sanitization."""

    ip: str = Field(title="Unique ipv4/ipv6 address.", min_length=7, max_length=45)
    country: str = Field(title="Country where address is located.", min_length=1, max_length=100)
    region: str = Field(title="Region where address is located.", min_length=1, max_length=100)
    city: str = Field(title="City where address is located.", min_length=1, max_length=100)
    zip_code: int = Field(title="ZIP postal code of the address", ge=1)
    latitude: float = Field(title="North-south position coordinate of the address")
    longitude: float = Field(title="West-east position coordinate of the address")

    @classmethod
    @field_validator("ip", "country", "region", "city", mode="before")
    def sanitize_strings(cls, value: str) -> str:
        """Strip leading/trailing spaces and title-case the string."""
        if isinstance(value, str):  # Ensure the value is a string
            return value.strip().title()

        raise ValueError("Invalid value; expected a string.")


def get_db_session() -> Generator[sqlite3.Connection, None, None]:
    """Responsible for handling the SQLite DB connection."""
    connection = sqlite3.connect(_PATH_DATABASE)
    # Treat row like a dictionary
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    except sqlite3.Error as exc:
        print(f"DB Exception occured '{exc}'")
    finally:
        connection.close()


@app.get("/")
def index() -> dict[str, str]:
    """Basic greeting call."""
    return {"message": "Greetings from machofv's geolocation API!"}


def __transform_rows_to_records(rows: list[list]) -> list[Record]:
    """Transforms given list of rows from database into list of Record objects."""
    return [
        Record(
            ip_address=row["ip_address"],
            country=row["country"],
            region=row["region"],
            city=row["city"],
            zip_code=row["zip"],
            latitude=row["latitude"],
            longitude=row["longitude"],
        )
        for row in rows
    ]


@app.get(
    "/ips/{ip}",
    response_model=dict[str, list[Record]],
    responses={
        404: {"description": "Address not found."},
    },
)
def get_ip_info(
    ip: Annotated[str, Path(title="IP address to get info about.", min_length=7, max_length=45)],
    db: sqlite3.Connection = Depends(get_db_session),
) -> dict[str, list[Record]]:
    """Get info about specific ip address.

    Args:
        ip (str): ipv4 | ipv6 address. Must be a string between 7 and 45 characters, to match
                shortest ipv4 address, ipv6 and ipv4 converted into ipv6.
        db (sqlite3.Connection): opened SQLite session.

    Returns:
        Information regarding selected ip address.
    """
    cursor = db.cursor()
    rows = cursor.execute("SELECT * FROM geolocation WHERE ip_address = ?", (ip,)).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No data found for ip={ip}!")

    return {"result": __transform_rows_to_records(rows)}


@app.get(
    "/ips/",
    response_model=dict[str, list[Record]],
    responses={
        400: {"description": "No arguments specified."},
        404: {"description": "No matching data."},
    },
)
def get_ip_info_by_parameters(
    ip: Annotated[str | None, Query(title="IP address to get info about.", min_length=7, max_length=45)] = None,
    country: Annotated[str | None, Query(title="Country to filter addresses by.", min_length=1)] = None,
    region: Annotated[str | None, Query(title="Region to filter addresses by.", min_length=1)] = None,
    city: Annotated[str | None, Query(title="City to filter addresses by.", min_length=1)] = None,
    zip_code: Annotated[int | None, Query(title="ZIP postal code to filter addresses by.", ge=0)] = None,
    latitude: Annotated[float | None, Query(title="North-south position coordinate to filter addresses by.")] = None,
    longitude: Annotated[float | None, Query(title="West-east position coordinate to filter addresses by.")] = None,
    limit: Annotated[int | None, Query(title="Number of maximum records to return.", ge=1)] = 10,
    db: sqlite3.Connection = Depends(get_db_session),
) -> dict[str, list[Record]]:
    """Filter IP records based on the provided parameters.

    Args:
        ip (str | None): Filter by IP address.
        country (str | None): Filter by country.
        region (str | None): Filter by region.
        city (str | None): Filter by city.
        zip_code (int | None): Filter by ZIP postal code.
        latitude (float | None): Filter by latitude.
        longitude (float | None): Filter by longitude.
        limit (int | None): Number of maximum rows to return.
        db (sqlite3.Connection): SQLite database connection.

    Returns:
        dict[str, list[Record]]: Filtered results.

    Raises:
        HTTPException: When no parameters were privded or no records were matched.
    """
    _RECORD_TO_SQL_MAPPER = {
        "ip_address": ip,
        "country": country,
        "region": region,
        "city": city,
        "zip": zip_code,
        "latitude": latitude,
        "longitude": longitude,
    }

    # Check if any parameter was provided
    if not any(param is not None for param in [ip, country, region, city, zip_code, latitude, longitude]):
        raise HTTPException(status_code=400, detail="At least one filtering parameter must be provided.")

    # Select conditions to be check against database
    conditions = []
    params = []

    for field, value in _RECORD_TO_SQL_MAPPER.items():
        if value is not None:
            conditions.append(f"{field} = ?")
            params.append(value)

    # Construct the query
    query = "SELECT * FROM geolocation"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    if limit:
        query += f" LIMIT {limit}"

    # Execute the query
    cursor = db.cursor()
    rows = cursor.execute(query, params).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No data found for provided parameters!")

    return {"result": __transform_rows_to_records(rows)}


@app.post(
    "/",
    response_model=dict[str, RecordInput],
    responses={400: {"description": "Address already exists."}, 500: {"description": "Internal Server Error."}},
)
def add_ip(
    record: RecordInput,
    db: sqlite3.Connection = Depends(get_db_session),
) -> dict[str, RecordInput]:
    """Add a new IP address record to the database.

    Args:
        record (RecordInput): Data to add for a new IP address.
        db (sqlite3.Connection): SQLite database connection.

    Returns:
        dict[str, RecordInput]: The added IP record.

    Raises:
        HTTPException: If the address already exists or a database error occurs.
    """
    try:
        cursor = db.cursor()

        # Check for existence of data to be added
        rows = cursor.execute("SELECT * FROM geolocation WHERE ip_address = ?", (record.ip,)).fetchall()
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="")

    if rows:
        raise HTTPException(status_code=400, detail=f"Address with ip={record.ip} already exists!")

    # Add a record
    try:
        query = """
        INSERT INTO geolocation (ip_address, country, region, city, zip, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(
            query,
            (
                record.ip,
                record.country,
                record.region,
                record.city,
                record.zip_code,
                record.latitude,
                record.longitude,
            ),
        )
        db.commit()
        return {"added": record.model_dump()}

    except sqlite3.Error as exc:
        logging.error("Database error: %s", exc)
        raise HTTPException(status_code=500, detail="")


@app.put(
    "/ips/{ip}",
    response_model=dict[str, Record],
    responses={
        400: {"description": "No arguments specified."},
        404: {"description": "No data for specified ip address."},
        500: {"description": "Internal Server Error."},
    },
)
def update_data(
    ip: Annotated[str, Path(title="IP address to get info about.", min_length=7, max_length=45)],
    country: Annotated[str | None, Query(title="Country to filter addresses by.", min_length=1)] = None,
    region: Annotated[str | None, Query(title="Region to filter addresses by.", min_length=1)] = None,
    city: Annotated[str | None, Query(title="City to filter addresses by.", min_length=1)] = None,
    zip_code: Annotated[int | None, Query(title="ZIP postal code to filter addresses by.", ge=0)] = None,
    latitude: Annotated[float | None, Query(title="North-south position coordinate to filter addresses by.")] = None,
    longitude: Annotated[float | None, Query(title="West-east position coordinate to filter addresses by.")] = None,
    db: sqlite3.Connection = Depends(get_db_session),
) -> dict[str, Record]:
    """Update IP record data based on the provided parameters.

    Args:
        ip (str): The IP address to update.
        country (str | None): Country to update.
        region (str | None): Region to update.
        city (str | None): City to update.
        zip_code (int | None): ZIP postal code to update.
        latitude (float | None): Latitude coordinate to update.
        longitude (float | None): Longitude coordinate to update.
        db (sqlite3.Connection): SQLite database connection.

    Returns:
        dict[str, Record]: The updated IP record.

    Raises:
        HTTPException: If no parameters were provided for update, no record found, or a database error occurs.
    """

    _RECORD_TO_SQL_MAPPER = {
        "country": country,
        "region": region,
        "city": city,
        "zip": zip_code,
        "latitude": latitude,
        "longitude": longitude,
    }

    # Check whether any parameters to update were passed
    if all(param is None for param in (country, region, city, zip_code, latitude, longitude)):
        raise HTTPException(status_code=400, detail="No parameters passed!")

    try:
        cursor = db.cursor()

        # Check for existence of ip to be updated
        rows = cursor.execute("SELECT * FROM geolocation WHERE ip_address = ?", (ip,)).fetchall()

    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="")

    if not rows:
        raise HTTPException(status_code=404, detail=f"No data found for ip={ip}!")

    # Dynamically construct query
    updates = []
    params = []
    for field, value in _RECORD_TO_SQL_MAPPER.items():
        if value is not None:
            updates.append(f"{field} = ?")
            params.append(value)

    query = f"UPDATE geolocation SET {', '.join(updates)} WHERE ip_address = ?"

    # Add the IP address for the WHERE clause
    params.append(ip)

    try:
        cursor.execute(query, tuple(params))
        db.commit()

        # Get updated record for the user response
        rows = cursor.execute("SELECT * FROM geolocation WHERE ip_address = ?", (ip,)).fetchall()

    except sqlite3.Error as exc:
        logging.error("Database error: %s", exc)
        raise HTTPException(status_code=500, detail="")

    return {"updated": __transform_rows_to_records(rows)[0]}
