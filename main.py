import os
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import TestTable

# Boring setup junk
TSQL_USER = os.getenv("TSQL_USER")
TSQL_PASSWORD = os.getenv("TSQL_PASSWORD")
TSQL_HOST = os.getenv("TSQL_HOST", "127.0.0.1")
TSQL_DB = os.getenv("TSQL_DB")

CONNECT_STRING = (
    "mssql+pymssql://"
    f"{TSQL_USER}:{TSQL_PASSWORD}@{TSQL_HOST}:1433/{TSQL_DB}"
    "?charset=utf8&tds_version=7.3"
)

engine = create_engine(CONNECT_STRING)
Session = sessionmaker(bind=engine)


def perform_query(session, value):
    start = time.perf_counter()

    items = (
        session.query(TestTable).filter(TestTable.indexed_varchar_column == value).all()
    )

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    print(f"Found {len(items)} items in {elapsed_ms:.1f}ms")


def main():
    session = Session()

    lookup_value = "Some String"

    # This example performs the query with a bytestring
    # passed instead of a str. pymssql will, in this case, send
    # the value as 'Some String' to SQL Server and assume that we
    # have properly encoded the string / know what we are doing.
    #
    # If the table is sizeable (several million rows, for instance),
    # there will be a massive difference in running times between
    # these two methods, as SQL Server ends up casting all values
    # in the VARCHAR column to NVARCHARs to perform the string
    # equality checks, and it is thus unable to use the index.
    perform_query(session, lookup_value.encode("utf-8"))

    # Second, we run the same query using a Python3 str. This
    # is technically always a unicode value, so pymssql assumes
    # we know what we're doing and dutifully sends this to SQL Server
    # as N'Some String'. I intentionally put this query second to minimize
    # the impact of any session startup, caching, etc.
    #
    # If you run this on a table with a large number of records (1.7 mil in our case),
    # it will be an order of magnitude slower than the previous query.
    # I include a timing example here because that's actually a lot easier than verifying
    # the exact SQL received by SQL server (doable, but tricky).
    perform_query(session, lookup_value)

    session.close()


if __name__ == "__main__":
    main()
