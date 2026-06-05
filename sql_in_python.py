"""
Cursor
    ex: cursor.execute("SELECT * FROM table_name")

 ex:
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM table_name")
  psycopg2
    a popular PostgreSQL adapter for Python

?: used for parameterized queries to prevent SQL injection
    ex: cursor.execute("SELECT * FROM table_name WHERE column1 = ?", (value1,))
    context manager for database connections
        allows you to automatically manage the connection and ensure it is properly closed after use
        automatically commits transactions if no exceptions occur, or rolls back if an exception is raised
"""
