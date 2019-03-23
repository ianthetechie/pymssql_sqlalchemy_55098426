# SQLAlchemy + PyMSSQL Problem Demonstration

This is a minimal example illustrating the problem
documented in https://stackoverflow.com/questions/55098426/strings-used-in-query-always-sent-with-nvarchar-syntax-even-if-the-underlying-c.

The example relies on timing to demonstrate the effect
as simply as possible. Note that this can NOT be properly
debugged using the engine echo functionality, as this is
NOT the exact SQL that gets passed through to SQL Server.
The exact SQL passed to PyMSSQL is in fact parameterised,
and the parameters passed are Python `str`s, which result in
the final query being an `N'nvarchar'` style literal.

If you wish to debug the *exact* SQL that PyMSSQL sends,
you can use some variant of this query:

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
