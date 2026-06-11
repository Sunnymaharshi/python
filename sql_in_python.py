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
"""
