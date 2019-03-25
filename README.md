# SQLAlchemy + PyMSSQL Problem Demonstration


## Problem Description

This is a minimal example illustrating the problem
documented in https://stackoverflow.com/questions/55098426/strings-used-in-query-always-sent-with-nvarchar-syntax-even-if-the-underlying-c.

The example relies on timing to demonstrate the effect
as simply as possible. Note that this can NOT be properly
debugged using the engine echo functionality, as this is
NOT the exact SQL that gets passed through to SQL Server.
The exact SQL passed to PyMSSQL is in fact parameterised,
and the parameters passed are Python `str`s, which result in
the final query being an `N'nvarchar'` style literal.

## Verification of problem

If you wish to debug the *exact* SQL that PyMSSQL sends,
you can use some variant of this query, or use the profiler in SQL Server.

```sql
SELECT TOP 100 SUBSTRING(qt.TEXT, (qs.statement_start_offset / 2) + 1,
                         ((CASE qs.statement_end_offset
                             WHEN -1 THEN DATALENGTH(qt.TEXT)
                             ELSE qs.statement_end_offset
                             END - qs.statement_start_offset) / 2) + 1),
               qs.execution_count,
               qs.total_logical_reads,
               qs.last_logical_reads,
               qs.total_logical_writes,
               qs.last_logical_writes,
               qs.total_worker_time,
               qs.last_worker_time,
               qs.total_elapsed_time / 1000000 total_elapsed_time_in_S,
               qs.last_elapsed_time / 1000000  last_elapsed_time_in_S,
               qs.last_execution_time,
               qp.query_plan
FROM sys.dm_exec_query_stats qs
       CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) qt
       CROSS APPLY sys.dm_exec_query_plan(qs.plan_handle) qp
WHERE execution_count > 1
  AND qt.TEXT LIKE '%N''%'  -- You could also modify this to include a table name
ORDER BY qs.total_worker_time DESC -- CPU time
```

## Approaches to fixing this

I have attempted to fix this at the dialect level by adding the following type, and adding
`sqltypes.String: _String_pymssql` to the dialect's `colspecs` dictionary (file: `dialects/mssql/pymssql.py`).

```python
class _String_pymssql(sqltypes.String):
    def bind_processor(self, dialect):
        encoder = codecs.getencoder(dialect.encoding)

        def process(value):
            super_process = super(_String_pymssql, self).bind_processor(dialect)

            result = super_process(value) if super_process else value

            if isinstance(result, util.text_type):
                return encoder(value, self.unicode_error)[0]
            else:
                return result

        return process

    @property
    def python_type(self):
        return bytes
```

This correctly fixes string columns, but breaks when an enum is also used. See the traceback below.

```
Traceback (most recent call last):
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/sql/type_api.py", line 446, in dialect_impl
    return dialect._type_memos[self]["impl"]
  File "/Library/Frameworks/Python.framework/Versions/3.6/lib/python3.6/weakref.py", line 394, in __getitem__
    return self.data[ref(key)]
KeyError: <weakref at 0x106bb03b8; to 'Enum' at 0x10661c390>

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "main.py", line 69, in <module>
    main()
  File "main.py", line 51, in main
    perform_query(session, lookup_value.encode("utf-8"))
  File "main.py", line 29, in perform_query
    session.query(TestTable).filter(TestTable.indexed_varchar_column == value).all()
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/orm/query.py", line 3161, in all
    return list(self)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/orm/query.py", line 3317, in __iter__
    return self._execute_and_instances(context)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/orm/query.py", line 3342, in _execute_and_instances
    result = conn.execute(querycontext.statement, self._params)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/engine/base.py", line 988, in execute
    return meth(self, multiparams, params)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/sql/elements.py", line 287, in _execute_on_connection
    return connection._execute_clauseelement(self, multiparams, params)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/engine/base.py", line 1098, in _execute_clauseelement
    else None,
  File "<string>", line 1, in <lambda>
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/sql/elements.py", line 462, in compile
    return self._compiler(dialect, bind=bind, **kw)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/sql/elements.py", line 468, in _compiler
    return dialect.statement_compiler(dialect, self, **kw)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/dialects/mssql/base.py", line 1502, in __init__
    super(MSSQLCompiler, self).__init__(*args, **kwargs)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/sql/compiler.py", line 562, in __init__
    Compiled.__init__(self, dialect, statement, **kwargs)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/sql/compiler.py", line 319, in __init__
    self.string = self.process(self.statement, **compile_kwargs)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/sql/compiler.py", line 350, in process
    return obj._compiler_dispatch(self, **kwargs)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/sql/visitors.py", line 91, in _compiler_dispatch
    return meth(self, **kw)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/dialects/mssql/base.py", line 1630, in visit_select
    return compiler.SQLCompiler.visit_select(self, select, **kwargs)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/sql/compiler.py", line 2090, in visit_select
    for name, column in select._columns_plus_names
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/sql/compiler.py", line 2090, in <listcomp>
    for name, column in select._columns_plus_names
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/sql/compiler.py", line 1773, in _label_select_column
    impl = column.type.dialect_impl(self.dialect)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/sql/type_api.py", line 448, in dialect_impl
    return self._dialect_info(dialect)["impl"]
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/sql/type_api.py", line 513, in _dialect_info
    impl = self._gen_dialect_impl(dialect)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/sql/type_api.py", line 522, in _gen_dialect_impl
    return dialect.type_descriptor(self)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/engine/default.py", line 418, in type_descriptor
    return sqltypes.adapt_type(typeobj, self.colspecs)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/sql/type_api.py", line 1459, in adapt_type
    return typeobj.adapt(impltype)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/sql/sqltypes.py", line 1522, in adapt
    return super(Enum, self).adapt(impltype, **kw)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/sql/type_api.py", line 735, in adapt
    return super(Emulated, self).adapt(impltype, **kw)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/sql/type_api.py", line 532, in adapt
    return util.constructor_copy(self, cls, **kw)
  File "/Users/ianthetechie/PycharmProjects/pymssql_sqlalchemy_55098426/env/lib/python3.6/site-packages/sqlalchemy/util/langhelpers.py", line 1147, in constructor_copy
    return cls(*args, **kw)
TypeError: __init__() got an unexpected keyword argument '_enums'
```
