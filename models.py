from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TestTable(Base):
    __tablename__ = "test"

    id = Column("id", Integer, primary_key=True)

    # This column should be an indexed VARCHAR column in your
    # database. SQL Server is annoying and has special column
    # types and literal syntax to support unicode strings.
    # Even though this column is a String and not Unicode,
    # Python 3 strs (unicode) are passed through to pymssql
    # unchanged.
    #
    # My proposal is to change the pymssql dialect behavior
    # (and other affected drivers in the MSSQL tree, if necessary) to send
    # bytestrings for String columns encoded using the connection
    # charset. This way they will be sent as 'non-unicode literals'
    # instead of N'unicode literals'.
    indexed_varchar_column = Column("key", String(50), index=True)
