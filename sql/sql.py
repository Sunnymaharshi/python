"""
SQL (Structured Query Language)
    standard language for working with relational databases
    The 4 Core Operations (CRUD)
        1. SELECT — Read data
            ex: SELECT name, age FROM users;          -- specific columns
                SELECT * FROM users;                  -- all columns
        2. INSERT — Add data
            ex: INSERT INTO users (name, age, city)
                VALUES ('Arjun', 28, 'Hyderabad');
        3. UPDATE — Modify data
            ex: UPDATE users
                SET city = 'Bangalore'
                WHERE name = 'Arjun';
        4. DELETE — Remove data
            ex: DELETE FROM users
                WHERE id = 3;
    Filtering with WHERE
        used to specify conditions for filtering data
        filters rows → before grouping
        ex: SELECT * FROM users WHERE age > 25;
            SELECT * FROM users WHERE age > 20 AND city = 'Mumbai';
            SELECT * FROM users WHERE age > 20 OR city = 'Mumbai';
    Sorting & Limiting
        ex: SELECT * FROM users ORDER BY age ASC;     -- ascending
            SELECT * FROM users ORDER BY age DESC;    -- descending
            SELECT * FROM users LIMIT 5;
    Creating a Table
        ex: CREATE TABLE users (
                id   INT PRIMARY KEY,
                name VARCHAR(100),
                age  INT,
                city VARCHAR(100)
            );
    Aggregate Functions
        used to perform calculations on a set of values and return a single value
        ex: SELECT COUNT(*) FROM users;               -- counts total rows
            SELECT SUM(amount) FROM orders;           -- total revenue
            SELECT AVG(age) FROM users;               -- average age
            SELECT MAX(age) FROM users;               -- maximum age
            SELECT MIN(age) FROM users;               -- minimum age
    GROUP BY
        splits rows into groups and applies aggregate functions per group.
        ex: SELECT city, SUM(amount) AS total_sales
            FROM orders
            GROUP BY city;                      -- total sales per city
        ex: SELECT city, COUNT(*) AS num_customers
            FROM orders
            GROUP BY city;                      -- number of customers per city
    HAVING
        Filter rows after grouping
        ex: SELECT city, SUM(amount) AS total_sales
            FROM orders
            GROUP BY city
            HAVING SUM(amount) > 500;           -- cities with total sales > 500
    JOIN
        combine data from multiple tables.
        1. INNER JOIN
            Returns only rows that have matching values in both tables.
            ex: SELECT c.name, o.product, o.amount
                FROM customers c
                INNER JOIN orders o ON c.customer_id = o.customer_id;
        2. LEFT JOIN or LEFT OUTER JOIN
            Returns all rows from the left table, and matched rows from the right.
            ex: SELECT c.name, o.product, o.amount
                FROM customers c
                LEFT JOIN orders o ON c.customer_id = o.customer_id;
        3. RIGHT JOIN or RIGHT OUTER JOIN
            Returns all rows from the right table, and matched rows from the left.
            ex: SELECT c.name, o.product, o.amount
                FROM customers c
                RIGHT JOIN orders o ON c.customer_id = o.customer_id;
            In practice, RIGHT JOIN is rare — most people flip the tables and use LEFT JOIN instead
        4. FULL OUTER JOIN
            Returns all rows from both tables. NULLs fill in where there's no match on either side.
            ex: SELECT c.name, o.product, o.amount
                FROM customers c
                FULL OUTER JOIN orders o ON c.customer_id = o.customer_id;
            Not supported in MySQL - LEFT JOIN UNION RIGHT JOIN can be used as a workaround
        5. CROSS JOIN
            Returns the cartesian product
            every row from table A combined with every row from table B.
            ex: SELECT c.name, o.product
                FROM customers c
                CROSS JOIN orders o;
            4 customers x 4 orders = 16 rows
            No ON condition needed
            Useful for generating combinations (e.g. all possible size-color pairs for products)
        6. SELF JOIN
            A table joined with itself.
            Useful for hierarchical data.
            ex: -- employees table: id, name, manager_id
                SELECT e.name AS employee, m.name AS manager
                FROM employees e
                LEFT JOIN employees m ON e.manager_id = m.id;
            Common for org charts, category trees, friend relationships

    Complete SQL Execution Order
        1.  FROM                    - loads tables into memory
        2.  ON                      - defines matching condition for join
        3.  JOIN                    - combines rows from two or more tables
        4.  WHERE                   - filters rows before grouping
        5.  GROUP BY                - rows are grouped based on specified columns
        6.  AGGREGATE FUNCTIONS     - calculations performed on groups
        7.  HAVING                  - filters groups, can't use column aliases up to this point
                                      because select is not executed yet
        8.  WINDOW FUNCTIONS        - calculations across related rows
                                      runs after grouping but before select
        9.  SELECT                  - database decides which columns to show
                                      Aliases are created here
        10. DISTINCT                - removes duplicate rows from the result set
        11. ORDER BY                - sorts the result, this is only clause that can use column aliases
        12. LIMIT / OFFSET          - trims the result to a specific number of rows
        ex: SELECT DISTINCT c.city, COUNT(o.order_id) AS total_orders, SUM(o.amount) AS revenue
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            WHERE o.status = 'delivered'
            GROUP BY c.city
            HAVING SUM(o.amount) > 10000
            ORDER BY revenue DESC
            LIMIT 5 OFFSET 0;

    SELECT 1 FROM table_name
        returns 1 for every every row of table
        used for existence checks, when you don't want data
    LIKE
        used in WHERE clause for pattern matching
        wild cards
            % matches any no of characters (including zero)
                ex: HI%
            _ matches exactly one character
                ex: H_TH_RE
        ESCAPE or '\'
            defines which character acts as escape prefix.
            default escape character is '\'
            LIKE '%50!%' ESCAPE '!'
            or LIKE '%50\%'
    PostgresSQL
        SIMILAR TO (regex-like)
            ex: WHERE name SIMILAR TO '(John|Jane)%'
        full regex (~, ~*)
            ex: WHERE name ~ '^John' -- case sensitive regex
            ex: WHERE name ~* '^john' -- case-insensitive regex

    NULL handling
        NULL means "unknown" — not zero, not empty string
        SQL uses three-valued logic: TRUE, FALSE, and UNKNOWN
        Any comparison with NULL produces UNKNOWN — not TRUE or FALSE.
        ex: 5 = 5        → TRUE
            5 = 6        → FALSE
            NULL = NULL  → UNKNOWN
            NULL = 5     → UNKNOWN
            NULL != 5    → UNKNOWN
            NULL > 0     → UNKNOWN
            NULL + 1     → NULL
            NOT UNKNOWN  → UNKNOWN
        WHERE filters only keep rows where the condition is TRUE.
        UNKNOWN rows are silently dropped
        ex: WHERE discount = NULL  -- NEVER works, always returns UNKNOWN
            WHERE discount IS NULL -- correct
        IS NULL / IS NOT NULL
            only operators that correctly tests for NULL.
            It returns TRUE or FALSE, never UNKNOWN.
        COALESCE
            return first non-NULL value
            ex: COALESCE(NULL, NULL, 42)      → 42
                COALESCE(NULL, NULL, NULL)    → NULL
        NULLIF
            return NULL when two values are equal, otherwise returns val1
            ex: NULLIF(10, 10)   → NULL
                NULLIF(10, 5)    → 10
        The NULL traps
            NOT IN (... NULL)
                silently returns zero rows and looks like it's working fine.
            NULLs in JOINs
            NULLs in aggregates
                AVG divides by the count of non-NULL rows, not total rows.
                With 2 NULLs out of 5 rows, your denominator is silently wrong.


    Subqueries
        query nested inside another query
        Instead of combining tables with a JOIN
        you use the result of an inner query as the input to an outer query.
        can appear in the SELECT, FROM, or WHERE clause
        Where clause
            Filter rows using a subquery
            ex: SELECT name, salary
                FROM employees
                WHERE salary > (
                    SELECT AVG(salary)
                    FROM employees
                );
        From clause
            Use a subquery as a derived table
            ex: SELECT dept, avg_sal
                FROM (
                    SELECT department AS dept,
                            AVG(salary) AS avg_sal
                    FROM employees
                    GROUP BY department
                ) AS dept_stats
                WHERE avg_sal > 60000;
        Select clause
            Add a computed column from another table
            ex: SELECT
                product_name,
                price,
                (
                    SELECT COUNT(*)
                    FROM orders o
                    WHERE o.product_id = p.product_id
                ) AS total_orders
                FROM products p;
        Correlated subquery
            Sub query references the outer query
            uses a column from the outer query
            re-runs for every single outer row
            ex: SELECT name, department, salary
                FROM employees e1
                WHERE salary = (
                    SELECT MAX(salary)
                    FROM employees e2
                    WHERE e2.department = e1.department ← links to outer row
                );

    EXISTS
        returns TRUE if subquery returns atleast one row
        ex: SELECT name from customers c
            WHERE EXISTS (
                SELECT 1 FROM orders o
                WHERE o.cus_id=c.id
            )
    NOT EXISTS
        returns TRUE if subquery returns 0 rows
    IN
        ex: SELECT name FROM customers
            WHERE price> ALL(SELECT price FROM products WHERE cat_id=5)
    NOT IN
    ANY/SOME
        true if condition holds for at least one value
    ALL
        true if condition holds for every value

    CASE in SQL
        ex: CASE status
                WHEN 'active'   THEN 'Live'
                WHEN 'inactive' THEN 'Paused'
                WHEN 'banned'   THEN 'Blocked'
                ELSE                 'Unknown'
            END
        ex: CASE
                WHEN salary > 100000 THEN 'Senior'
                WHEN salary > 60000  THEN 'Mid'
                WHEN salary IS NULL  THEN 'Unknown'
                ELSE                      'Junior'
            END

    Pivoting rows into columns
        transform row values into col headers
        turning tall table to wide table
        ex: SELECT
                COUNT(CASE WHEN status='pending' THEN 1 END) as pending_count,
                COUNT(CASE WHEN status='delivered' THEN 1 END) as delivered_count,
            FROM orders;
        COUNT(CASE WHEN ... THEN 1 END) omits ELSE, so non-matching rows return NULL
        COUNT ignores NULLs. Cleaner than ELSE 0 for counting.

    String functions
        CONCAT
            ex: CONCAT('Hello', ' ', 'World') 'Hello World'
        SUBSTRING
            ex: SUBSTRING('Hello World', 1, 5) 'Hello'
        TRIM
            ex: TRIM(' hello ') 'hello'
        REGEXP_REPLACE
            ex: REGEXP_REPLACE('abc 123', '[0-9]', '') 'abc '

    Date functions
        DATE_TRUNC
            truncate to boundary
            ex: DATE_TRUNC('month', '2024-03-15 14:32:00') 2024-03-01 00:00:00
                DATE_TRUNC('hour', '2024-03-15 14:32:59')  2024-03-15 14:00:00
        DATEADD
            shift by interval
            ex: DATEADD(day, 30, '2024-01-15')  2024-02-14
        DATEDIFF
            count intervals between dates
            ex: DATEDIFF(day, '2024-01-01', '2024-03-01')  60
        EXTRACT
            field extraction
            EXTRACT(week FROM '2024-01-01')   1

    Common Table Expressions (CTEs)
        With subqueries you write inside-out — inner query first, outer query wraps it.
        With CTEs you write top-to-bottom - subquery defined first, then main query.
        CTE starts with WITH, gives the result a name
        then the main query uses that name like a table.
        SQL runs everything inside the WITH block and stores the result under the name high_earners.
        Then the main SELECT queries that result as if it were a real table.
        Chainable — each CTE can build on the last
        ex: WITH high_earners AS (
                SELECT name, department, salary
                FROM employees
                WHERE salary > 70000
            )
            SELECT name, department, salary
            FROM high_earners
            ORDER BY salary DESC;
        chain multiple CTEs
            ex: WITH dept_avg AS (
                    SELECT department, AVG(salary) AS avg_sal
                    FROM employees
                    GROUP BY department
                    ),
                -- Step 2: tag each employee vs their dept average
                tagged AS (
                    SELECT e.name, e.department, e.salary,
                    CASE WHEN e.salary > d.avg_sal
                        THEN 'above avg'
                        ELSE 'below avg'
                    END AS vs_avg
                    FROM employees e
                    JOIN dept_avg d ON e.department = d.department
                )
                SELECT * FROM tagged ORDER BY department;
        Recursive CTEs
            querying hierarchies, letting you walk tree-like data
            recursive CTE references itself
            ex: -- Org chart: find all reports under a given manager
                WITH RECURSIVE org_tree AS (
                    -- Anchor: start at the root manager
                    SELECT id, name, manager_id, 1 AS depth
                    FROM employees
                    WHERE name = 'Anita Das'
                    UNION ALL
                    -- Recursive part: find direct reports of current level
                    SELECT e.id, e.name, e.manager_id, t.depth + 1
                    FROM employees e
                    JOIN org_tree t ON e.manager_id = t.id
                )
                SELECT name, depth FROM org_tree
                ORDER BY depth;
            Anchor query (runs once)
                Selects the starting row — Anita Das, depth = 1. This is the seed.
            Recursive part (runs repeatedly)
                JOINs the org_tree result back to employees to find direct reports.
                Each pass adds another level of depth.
            Stops automatically
                When the recursive part finds no new rows (no more direct reports), the loop ends.
    CTEs vs subqueries:
        A Common Table Expression (WITH dept_stats AS (...) SELECT ...) does exactly what a FROM subquery does
        A subquery is anonymous and nested inside the main query.
        A CTE is a named, reusable block defined before the main query using WITH.
        you can define multiple CTEs in sequence, where later ones can reference earlier ones
        something nested subqueries simply can't do cleanly.
        If you reference the same CTE twice in a query, a materializing engine computes it once and caches it.
        A subquery written twice runs twice.

    Views
        saved SQL query with a name.
        Querying the view runs the underlying query fresh every time.
        No data is stored
        ex: CREATE VIEW public_employees AS
            SELECT id, name, dept
            FROM employees;
        views are good for
            Security
                Expose only the columns a role needs.
            Reusability
                Define complex join logic once.
            Abstraction
                When you rename a table or column, update the view
                all queries using the view continue unchanged.
        Updatable views
            Simple views (no aggregates, no JOINs, no DISTINCT) can be INSERTed/UPDATEd through.
            DB passes the write through to the base table.
    Materialized views
        pre-computed snapshots
        runs the query once and physically stores the result on disk.
        Reads are instant. Data is stale until refreshed.
        how to solve staleness problem
            Scheduled refresh
            On-demand refresh
            Trigger based
            incremental
        REFRESH MATERIALIZED VIEW CONCURRENTLY
            Refreshes without locking reads. Requires a unique index on the mat view.
    Functions
        Scalar function
            Takes inputs, returns one value.
        Table-valued function
            Returns a result set (a table). Can be JOINed, filtered, and aggregated like a table.
    Stored procedures
        precompiled SQL + procedural logic (loops, conditionals, variables) stored in the database.
        ex: CREATE OR REPLACE PROCEDURE transfer_funds(
                from_account INT,
                to_account   INT,
                amount       DECIMAL
            )...;
            CALL transfer_funds(101, 202, 5000.00);
        Pros
            Precompiled — query plan cached
            Reduces network round-trips (one CALL vs many queries)
            Centralised business logic in DB
            Security — grant EXECUTE, not table access
            Atomic multi-step operations with ROLLBACK
        Cons
            Hard to version-control and code-review
            DB-vendor specific syntax (no portability)
            Difficult to unit-test
            Logic split across app + DB = harder to debug
            Can become a maintenance burden at scale
        When to use these over application code
            For atomic multi-step operations that must not be interrupted
            bank transfers, inventory deductions, audit-log writes that must happen together
            it keeps all steps in one transaction with automatic rollback on error
            reducing network round-trips and race conditions.


    Window functions
        perform calculations across a set of rows related to the current row
        Every aggregate you've learned (SUM, COUNT, AVG) collapses rows into groups — you lose the individual rows.
        Window functions do the same calculations but keep every row intact,
        adding the result as a new column alongside the original data.
        OVER() Clause
            function() OVER(...). The OVER clause defines the "window" — which rows to include and in what order.
            ex: SELECT name, department, salary,
                -- Window 1: whole table, no partition
                AVG(salary) OVER() AS company_avg,
                -- Window 2: partitioned by dept
                AVG(salary) OVER(PARTITION BY department) AS dept_avg,
                -- Window 3: rank within dept by salary
                ROW_NUMBER() OVER(PARTITION BY department ORDER BY salary DESC) AS dept_rank
                FROM employees;
        Execution order
            they always run after WHERE, JOIN, and GROUP BY — but before the final SELECT output.
            This is why you can't filter on a window function result in the same query's WHERE clause.
            You always need a CTE or subquery wrapper first to filter on window function results.
        PARTITION BY vs GROUP BY
            Think of it this way — GROUP BY collapses rows into one per group.
            PARTITION BY draws invisible dividing lines between groups but keeps every row.
            Same grouping logic, completely different output shape.
        ORDER BY inside OVER()
            Ordering
                SQL physically sorts the rows within the window before processing them
            Implicit frame activation
                SQL implicitly uses a running frame
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                for each row, look at all rows from the very start of the window up to and including this row.
            gives you a running/cumulative aggregate
            ex: SELECT
                    sale_date,
                    amount,
                    SUM(amount) OVER (ORDER BY sale_date) AS running_total
                FROM sales;
            ex: -- 3-row moving average
                SELECT
                    sale_date,
                    amount,
                    AVG(amount) OVER (
                        ORDER BY sale_date
                        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                    ) AS moving_avg_3
                FROM sales;
            ex: SELECT
                    category,
                    SUM(amt) AS cat_total,
                    SUM(SUM(amt)) OVER() AS grand_total
                FROM sales
                GROUP BY category;
                -- SUM(amt) is aggregate function, groups & sums per category
                -- SUM(...) OVER() is window function, sums those grouped results across all rows

        ROW_NUMBER()
            Assign a unique sequential number to each row
            ex: ROW_NUMBER() OVER(
                    PARTITION BY department
                    ORDER BY salary DESC
                ) AS rank
        RANK() vs DENSE_RANK()
            RANK leaves gaps in the ranking sequence if there are ties.
                ex: if 2 people tie for 2nd rank, they both get 2nd rank & 3rd rank is skipped → 1, 2, 2, 4
            DENSE_RANK does not leave gaps; The next rank is always consecutive
                ex: if 2 people tie for 2nd rank, they both get 2nd rank & the next rank is 3rd → 1, 2, 2, 3
            ex: SELECT name, salary,
                    RANK() OVER(ORDER BY salary DESC) AS rnk,
                    DENSE_RANK() OVER(ORDER BY salary DESC) AS dense_rnk,
                    ROW_NUMBER() OVER(ORDER BY salary DESC) AS row_num
                FROM employees;
        LAG() vs LEAD()
            Look at the previous or next row's value
            LAG(col, n) reaches back n rows. LEAD(col, n) reaches forward n rows.
            The default n is 1. Both return NULL at the boundary where there's no prior/next row.
            ex: SELECT
                    month, revenue,
                    LAG(revenue) OVER(ORDER BY month) AS prev_month,
                    revenue - LAG(revenue) OVER(ORDER BY month) AS change,
                    LEAD(revenue) OVER(ORDER BY month) AS next_month
                FROM monthly_revenue;

    Indexes
        An index is a sorted, separate data structure that tells the database exactly where to look.
        Without an index, SQL searches your entire table row by row
        Primary keys and unique constraints
            automatically create indexes on those columns.
        B-tree (Balanced tree) Index (default)
            B-trees are optimized for range queries and sorting
            Great for =, <, >, BETWEEN, ORDER BY.
            Keeps data sorted. Works for most use cases.
            ex: CREATE INDEX idx_name ON employees(name);
        Hash Index
            Only for exact = matches.
            Faster than B-tree for equality, but useless for range queries or sorting.
            ex: CREATE INDEX idx ON t(col) USING HASH;
        Composite Index
            Index on multiple columns.
            Useful when your queries filter on multiple columns together.
            Column order matters — leftmost column must be in your WHERE clause
            ex: CREATE INDEX idx ON t(dept, salary);
        Unique index
            Enforces uniqueness + speeds up lookups.
            PRIMARY KEY creates one automatically. Use for emails, usernames.
            ex: CREATE UNIQUE INDEX idx ON t(email);

    JSON & Semi-Structured Data in SQL
        JSON columns
            ex: CREATE TABLE products (
                id primary key,
                metadata JSON       -- stores raw JSON text
            )
        PostgreSQL
            offers JSON & JSONB
            JSON
                raw text
                write speed is fast
                read speed is slow (re-parses every time)
                Indexing is not supported
                Key order is preserved
            JSONB
                binary decomposed format
                write speed is slow (parses on insert)
                read speed is faster
                Indexing is supported
                Key order is not preserved
            JSONB specific operators
                Existence operators (?, ?!(any in array), ?&(all in array))
                    ex: SELECT '{"a":1}'::jsonb ?& ARRAY['a','z'];  -- false
                Containment operator (@>,<@)
                    @> does left side contain the right side
                    does JSON have at least these key-value pairs
                Path/Value Operators(->,->>,#>,#>>)

            Indexing
                1. GIN index on whole column
                    best for ? key exists and @> contains searches
                    ex: CREATE INDEX idx_payload ON events USING GIN(payload);
                2. Expression index on a specific path
                    best when you query one field often
                    ex: CREATE INDEX idx_payload ON events USING ((payload ->> 'status'));
                3. GIN with jsonb_path_ops
                    smaller index, only supports @> contains
                    ex: CREATE INDEX idx_payload ON events USING GIN(payload jsonb_path_ops);

    Query Optimization
        Every sql database has a query optimizer (query planner) that takes your SQL and
        decides most efficient way to execute it
        you can see this plan using EXPLAIN or EXPLAIN ANALYZE
        EXPLAIN
            shows the query execution plan
            how SQL plans to execute your query, which indexes it will use, join order, etc
            ex: EXPLAIN SELECT * FROM orders WHERE customer_id = 123;
        ANALYZE
            runs the query and shows actual execution stats
            ex: EXPLAIN ANALYZE SELECT * FROM orders WHERE customer_id = 123
        Anti Patterns that kill performance
            1. SELECT *
                fetches all columns including large TEXT/BLOB fields you don't need
            2. Function on Column
                Wrapping a column in a function (YEAR, UPPER, DATE, etc.) makes the index invisible.
                The DB must compute YEAR() for every row.
            3. LIKE with leading %
                A leading % means the DB has no idea where to start in the sorted index.
                It scans every row. Even with an index.
            4. N+1 queries
                1 query for orders, then 1 query per order
                N+1 is one of the most common bugs in ORMs. If you have 10,000 orders, you fire 10,001 queries.
                One JOIN replaces thousands of round trips.
                In ORMs, use eager loading (.include(), joinedload()) to avoid N+1 automatically.
            5. OR on Indexes
                OR on an indexed column can defeat the index
                UNION ALL lets the optimizer run two separate index seeks and merge results
                IN() is equivalent to OR but the optimizer handles it better.

    Transactions
        group of SQL statements that succeed or fail as single unit
        ACID
            Atomic
                All or nothing
                every statement in transaction succeeds or whole thing is rolled back
            Consistency
                Rules always holds
                transaction brings the DB from one valid state to another
                constraints, foreign keys & rules are never violated
            Isolated
                Transactions don't interfere
                Concurrent transactions behave as if they ran one at a time
            Durable
                Commits survice the crash
        BEGIN, COMMIT, ROLLBACK, SAVEPOINT
            SAVEPOINT
                create named checkpoints inside a transaction
                roll back to a specific point without undoing everything
                ex: SAVEPOINT before_risky_step;
                    ... do risky work ...
                    ROLLBACK TO SAVEPOINT before_risky_step; -- undo only from here
            ex: BEGIN;
                UPDATE accounts SET balance = balance - 5000
                WHERE account_id = 'A' AND balance >= 5000;
                -- Check if the row was actually updated
                DO $$
                BEGIN
                    IF NOT FOUND THEN
                        ROLLBACK; -- insufficient funds
                    END IF;
                END;
                $$ LANGUAGE plpgsql;
                UPDATE accounts SET balance = balance + 5000
                WHERE account_id = 'B';
                COMMIT;
        Isolation levels
            trading safety for speed
            more protection from concurrency bugs, but more locking and lower throughput.
            ex: SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
                BEGIN;
                -- ... your statements ...
                COMMIT;
            READ UNCOMMITTED
                almost never use this
                sees uncommitted data from other transactions
            READ COMMITTED
                default
                only sees committed data
            REPEATABLE READ
                for consistent multi-step reads
                Guarantees the same row returns the same value throughout your transaction.
            SERIALIZABLE
                maximum safety
                Transactions behave as if they ran one at a time.
                Use for financial operations, inventory checks, anything where correctness is non-negotiable.
            Level	            Dirty read	Non-repeatable	Phantom read
            READ UNCOMMITTED	possible	possible	    possible
            READ COMMITTED	    prevented	possible	    possible
            REPEATABLE READ	    prevented	prevented	    possible
            SERIALIZABLE	    prevented	prevented	    prevented
        Deadlocks
            two transactions waiting on each other forever
            Transaction A holds a lock that B needs, and B holds a lock that A needs
            database detects this and kills one transaction automatically
            database picks a "victim"
                usually the transaction that has done less work and rolls it back.
            Your application code must catch this error and retry the transaction.
            If you don't handle it, the user sees an error.
            Prevent deadlocks
                Always acquire locks in the same order.
                Keep transactions short
                Lock everything upfront with SELECT FOR UPDATE.
        SELECT FOR UPDATE
            explicit row locking
            It locks selected rows so no other transaction can modify them until you commit
            preventing the classic "two users buy the last item" race condition.
            ex: -- Classic race condition: two users buy the last ticket
                BEGIN;
                -- Lock this row — no one else can UPDATE it until we COMMIT
                SELECT quantity FROM inventory
                WHERE product_id = 42
                FOR UPDATE; ← this is the key
                -- Now we're the only one who can modify this row
                UPDATE inventory
                SET quantity = quantity - 1
                WHERE product_id = 42 AND quantity > 0;
                COMMIT;
        Isolation levels vs SELECT FOR UPDATE
            Isolation level
                control what your transaction can see (read behaviour)
                applies to entire transaction
                db shows you consistent point-in-time view of data
                Effects None
                    other transactions are unaware.
                    Readers don't block writers.
                protects against
                    dirty reads, non-repeatable reads, phantom reads
            SELECT FOR UPDATE
                controls who can modify a row while you hold it (write behaviour).
                applies to rows returned by that statement
                row locks - physically prevents other transactions from touching those rows
                Blocking
                    other transactions that try to update those rows must wait
                protects against
                    Lost updates, race conditions — two writers colliding on the same rows
        SERIALIZABLE vs SELECT FOR UPDATE
            SERIALIZABLE can logically replace SELECT FOR UPDATE in many cases but requires your
            app to retry on serialization failures.
            we get aborts with SERIALIZABLE instead of blocking with SELECT FOR UPDATE
            SERIALIZABLE
                db detects conflicting concurrent transactions & aborts one of them than blocking.
                uses optimistic concurrency in PostgreSQL via Serializable Snapshot Isolation(SSI)
                protects against broader range of anomalies like write skew
                that SELECT FOR UPDATE don't cover
                Scope
                    entire transactions read/write set
                Retry logic needed
                Performance
                    can cause more aborts under high contention
                When
                    you want correctness without managing explicit locks
                    app already handles transaction retries
                    you need protection againts write skew
                    write skew
                        two transactions both read overlapping data
                        each makes a decision on others not-yet-committed write
            SELECT FOR UPDATE
                locks specific rows at query time, preventing other transactions from modifying them
                explicit, fine-grained locking
                other transactions block(wait) when they try to update the same rows
                Scope
                    only locked rows
                Retry logic not needed
                Performance
                    can cause lock contention
                When
                    need to guarantee a specific row is locked immediately and make writers wait
                    don't want retry transactions
        READ COMMITTED + FOR UPDATE
            the right default for 90% of web applications. Simple, predictable, precise.
            Only reach for SERIALIZABLE when FOR UPDATE can't express the invariant you're trying to protect.

    Triggers
        lifecycle
            DML statement fires
                INSERT/UPDATE/DELETE
            Before Trigger
                can modify NEW row values
                Validate or transform data
                Abort with SIGNAL/RAISE
                Set NEW.col := computed_val
            Row written to storage
                transaction not yet commited
            After trigger
                sees commited row state
                Audit logging
                Cascade to other tables
                Notify/queue messages
            COMMIT or ROLLBACK
                trigger runs in same transaction
        ex: CREATE TRIGGER trg_audit_salary
            AFTER UPDATE ON employees
            FOR EACH ROW
            WHEN (OLD.salary <> NEW.salary)           -- optional guard condition
            BEGIN
                INSERT INTO audit_log(emp_id, old_sal, new_sal, changed_at)
                VALUES (NEW.id, OLD.salary, NEW.salary, NOW());
            END;
        Used for
            Audit logging
            Enforcing business rules
            Maintaining derived data
            Soft deletes / row versioning
        Where triggers will punish you
            Hidden side effects
                trigger is invisible to anyone reading application code.
            Cascading triggers
                Trigger A modifies table B, which fires trigger B, which modifies table C
                some databases let this recurse indefinitely.
                PostgreSQL has no depth limit by default
            Performance on bulk loads
                FOR EACH ROW fires N times for an N-row INSERT
            Transaction coupling
                trigger runs in the same transaction as the DML
                An exception inside a trigger rolls back the triggering statement
                sometimes desirable, often catastrophic if the trigger is doing "optional" logging.
            Debugging is painful
                Triggers don't appear in EXPLAIN output.
                They don't show up in ORMs' query logs.
                The only way to know a trigger fired is to inspect information_schema.triggers



PostgreSQL vs MySQL — Syntax Cheat Sheet
==========================================

DATE & TIME
-----------
Purpose                   PostgreSQL                                  MySQL
------------------------  ------------------------------------------  ------------------------------------------
Format date               TO_CHAR(col, 'YYYY-MM')                     DATE_FORMAT(col, '%Y-%m')
Current date              CURRENT_DATE                                CURDATE()
Current datetime          NOW() or CURRENT_TIMESTAMP                  NOW()
Extract part              EXTRACT(YEAR FROM col)                      YEAR(col) or MONTH(col)
Add interval              col + INTERVAL '1 day'                      DATE_ADD(col, INTERVAL 1 DAY)
Difference in days        d1 - d2 returns integer directly            DATEDIFF(d1, d2)
Truncate to period        DATE_TRUNC('month', col)                    DATE_FORMAT(col,'%Y-%m-01') no native TRUNC
Age / elapsed             AGE(now(), col) returns interval            TIMESTAMPDIFF(YEAR, col, NOW())

STRING FUNCTIONS
----------------
Purpose                   PostgreSQL                                  MySQL
------------------------  ------------------------------------------  ------------------------------------------
Concatenate               CONCAT(a, b) or a || b                      CONCAT(a, b)
Substring                 SUBSTRING(col, 1, 5) or col[1:5]            SUBSTRING(col, 1, 5)
String length             LENGTH(col) or CHAR_LENGTH(col)             LENGTH(col)
Uppercase                 UPPER(col)                                  UPPER(col)
Trim whitespace           TRIM(col)                                   TRIM(col)
Find position             POSITION('x' IN col)                        LOCATE('x', col)
Regex match               col ~ 'pattern'                             col REGEXP 'pattern'
Case-insensitive LIKE     ILIKE dedicated operator                    LIKE case-insensitive by default
Split string              STRING_TO_ARRAY(col, ',')                   SUBSTRING_INDEX(col, ',', n)
Repeat string             REPEAT(col, 3)                              REPEAT(col, 3)
Pad left                  LPAD(col, 5, '0')                           LPAD(col, 5, '0')

TABLE & COLUMN DEFINITIONS
--------------------------
Purpose                   PostgreSQL                                  MySQL
------------------------  ------------------------------------------  ------------------------------------------
Auto-increment            SERIAL or GENERATED ALWAYS AS IDENTITY      INT AUTO_INCREMENT
Boolean type              BOOLEAN                                     TINYINT(1)
Variable string           VARCHAR(n) or TEXT                          VARCHAR(n)
JSON type                 JSON or JSONB JSONB is indexed & faster     JSON
Unsigned int              Not supported use CHECK (col >= 0)          INT UNSIGNED
Array column              INT[] / TEXT[] native array type            Not supported
UUID type                 UUID                                        CHAR(36) no native UUID type
Enum type                 CREATE TYPE mood AS ENUM (...)              ENUM('a','b') inline

QUERY SYNTAX
------------
Purpose                   PostgreSQL                                  MySQL
------------------------  ------------------------------------------  ------------------------------------------
Limit rows                LIMIT 10                                    LIMIT 10
Offset rows               LIMIT 10 OFFSET 5                           LIMIT 10 OFFSET 5
If/else inline            CASE WHEN cond THEN a ELSE b END            IF(cond, a, b)
Null coalesce             COALESCE(col, 0)                            IFNULL(col, 0)
Full outer join           FULL OUTER JOIN                             Not supported use LEFT + UNION + RIGHT
String cast               col::TEXT or CAST(col AS TEXT)              CAST(col AS CHAR)
Integer cast              col::INT or CAST(col AS INT)                CAST(col AS UNSIGNED)
Upsert                    INSERT ... ON CONFLICT DO UPDATE            INSERT ... ON DUPLICATE KEY UPDATE
Return inserted row       INSERT ... RETURNING id                     Not supported use LAST_INSERT_ID()
CTE                       WITH cte AS (...) SELECT ...                WITH cte AS (...) SELECT ... MySQL 8+ only
Window functions          ROW_NUMBER() OVER (...)                     ROW_NUMBER() OVER (...) MySQL 8+ only
Lateral join              LATERAL                                     LATERAL MySQL 8.0.14+

UTILITY & ADMIN
---------------
Purpose                   PostgreSQL                                  MySQL
------------------------  ------------------------------------------  ------------------------------------------
Show tables               \dt or SELECT * FROM pg_tables;             SHOW TABLES;
Describe table            \d table or query information_schema        DESCRIBE table;
Comment syntax            -- comment only                             -- comment or # comment
Quote identifiers         "column_name" double quotes only            `column_name` backticks
Show running queries      SELECT * FROM pg_stat_activity;             SHOW PROCESSLIST;
Explain query plan        EXPLAIN ANALYZE SELECT ...                  EXPLAIN SELECT ...
List databases            \l or SELECT datname FROM pg_database;      SHOW DATABASES;

TRANSACTIONS & LOCKING
----------------------
Purpose                   PostgreSQL                                  MySQL
------------------------  ------------------------------------------  ------------------------------------------
Isolation level           SET TRANSACTION ISOLATION LEVEL ...         SET TRANSACTION ISOLATION LEVEL ...
Advisory lock             pg_advisory_lock(id)                        GET_LOCK('name', timeout)
DDL in transaction        Supported can rollback CREATE TABLE         Not supported DDL auto-commits
Savepoint                 SAVEPOINT sp1                               SAVEPOINT sp1



Real-World SQL Query Patterns:
-- customers table
    customer_id|name   |city     |joined_date|
-----------+-------+---------+-----------+
        101|Arjun  |Hyderabad| 2022-01-15|
        102|Priya  |Mumbai   | 2022-03-20|
        103|Karthik|Chennai  | 2023-06-10|
        104|Sneha  |Delhi    | 2023-08-05|
        105|Ravi   |Hyderabad| 2024-01-01|

-- orders table
order_id|customer_id|product |category   |amount|order_date|status   |
--------+-----------+--------+-----------+------+----------+---------+
       1|        101|Laptop  |Electronics| 50000|2024-01-10|delivered|
       2|        102|Phone   |Electronics| 20000|2024-01-15|delivered|
       3|        101|Tablet  |Electronics| 15000|2024-02-01|delivered|
       4|        103|Shoes   |Fashion    |  3000|2024-02-10|cancelled|
       5|        102|Earbuds |Electronics|  2000|2024-03-05|delivered|
       6|        101|Shirt   |Fashion    |  1500|2024-03-20|delivered|
       7|        104|Laptop  |Electronics| 50000|2024-04-01|pending  |
       8|        105|Notebook|Stationery |   500|2024-04-15|delivered|

1. Top N Per Group
    Find the top 2 spending customers per city
    ex: SELECT city, name, total_spent
        FROM (
            SELECT c.city,
                c.name,
                SUM(o.amount) AS total_spent,
                RANK() OVER (PARTITION BY c.city ORDER BY SUM(o.amount) DESC) AS rnk
            FROM customers c
            JOIN orders o ON c.customer_id = o.customer_id
            WHERE o.status = 'delivered'
            GROUP BY c.city, c.name
        ) ranked
        WHERE rnk <= 2;

        city     |name |total_spent|
        ---------+-----+-----------+
        Hyderabad|Arjun|      66500|
        Hyderabad|Ravi |        500|
        Mumbai   |Priya|      22000|

2. Customers who have never placed an order
    ex: SELECT c.name, c.city
        FROM customers c
        LEFT JOIN orders o ON c.customer_id = o.customer_id
        WHERE o.order_id IS NULL;
    ex: SELECT name, city
        FROM customers c
        WHERE NOT EXISTS (
            SELECT 1 FROM orders o
            WHERE o.customer_id = c.customer_id
        );
3. Running Total (Cumulative Sum)
    Show each order and the running total spent by that customer
    ex: SELECT  c.name,
                o.product,
                o.amount,
                SUM(o.amount) OVER (
                    PARTITION BY o.customer_id
                    ORDER BY o.order_date
                ) AS running_total
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE o.status = 'delivered'
        ORDER BY o.customer_id, o.order_date;

        name |product |amount|running_total|
        -----+--------+------+-------------+
        Arjun|Laptop  | 50000|        50000|
        Arjun|Tablet  | 15000|        65000|
        Arjun|Shirt   |  1500|        66500|
        Priya|Phone   | 20000|        20000|
        Priya|Earbuds |  2000|        22000|
        Ravi |Notebook|   500|          500|
4. Month-over-Month Comparison
    Compare each month's revenue to the previous month
    ex: SELECT
            TO_CHAR(order_date, 'YYYY-MM') AS month,
            SUM(amount)                       AS revenue,
            LAG(SUM(amount)) OVER (
                ORDER BY TO_CHAR(order_date, 'YYYY-MM')
            )                                 AS prev_month_revenue,
            SUM(amount) - LAG(SUM(amount)) OVER (
                ORDER BY TO_CHAR(order_date, 'YYYY-MM')
            )                                 AS change
        FROM orders
        WHERE status = 'delivered'
        GROUP BY TO_CHAR(order_date, 'YYYY-MM');

        month  |revenue|prev_month_revenue|change|
        -------+-------+------------------+------+
        2024-01|  70000|                  |      |
        2024-02|  15000|             70000|-55000|
        2024-03|   3500|             15000|-11500|
        2024-04|    500|              3500| -3000|

5. Percentage of Total
    What % of total revenue does each category contribute?
    ex: SELECT
            category,
            SUM(amount) AS category_revenue,
            ROUND(
                SUM(amount) * 100.0 / SUM(SUM(amount)) OVER(),
                2
            ) AS pct_of_total
        FROM orders
        WHERE status = 'delivered'
        GROUP BY category
        ORDER BY category_revenue DESC;

        category   |category_revenue|pct_of_total|
        -----------+----------------+------------+
        Electronics|           87000|       97.75|
        Fashion    |            1500|        1.69|
        Stationery |             500|        0.56|

6. Deduplication (keep latest record per user)
    keep only the most recent order for each customer
    ex: SELECT *
        FROM (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY customer_id
                    ORDER BY order_date DESC
                ) AS rn
            FROM orders
        ) ranked
        WHERE rn = 1;

        order_id|customer_id|product |category   |amount|order_date|status   |rn|
        --------+-----------+--------+-----------+------+----------+---------+--+
               6|        101|Shirt   |Fashion    |  1500|2024-03-20|delivered| 1|
               5|        102|Earbuds |Electronics|  2000|2024-03-05|delivered| 1|
               4|        103|Shoes   |Fashion    |  3000|2024-02-10|cancelled| 1|
               7|        104|Laptop  |Electronics| 50000|2024-04-01|pending  | 1|
               8|        105|Notebook|Stationery |   500|2024-04-15|delivered| 1|

7. Pivot (Rows to Columns)
    row values into column headers
    Show total revenue per category as columns
    ex: SELECT
            TO_CHAR(order_date, 'YYYY-MM') AS month,
            SUM(CASE WHEN category = 'Electronics' THEN amount ELSE 0 END) AS electronics,
            SUM(CASE WHEN category = 'Fashion'     THEN amount ELSE 0 END) AS fashion,
            SUM(CASE WHEN category = 'Stationery'  THEN amount ELSE 0 END) AS stationery
        FROM orders
        WHERE status = 'delivered'
        GROUP BY TO_CHAR(order_date, 'YYYY-MM');

        month  |electronics|fashion|stationery|
        -------+-----------+-------+----------+
        2024-01|      70000|      0|         0|
        2024-02|      15000|      0|         0|
        2024-03|       2000|   1500|         0|
        2024-04|          0|      0|       500|

8. Cohort Analysis
    How much did customers spend in their first month vs later
    ex: SELECT
            c.customer_id,
            c.name,
            SUM(CASE
                WHEN TO_CHAR(o.order_date, 'YYYY-MM') = TO_CHAR(c.joined_date, 'YYYY-MM')
                THEN o.amount ELSE 0
            END) AS first_month_spend,
            SUM(CASE
                WHEN TO_CHAR(o.order_date, 'YYYY-MM') > TO_CHAR(c.joined_date, 'YYYY-MM')
                THEN o.amount ELSE 0
            END) AS later_spend
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        WHERE o.status = 'delivered'
        GROUP BY c.customer_id, c.name;

        customer_id|name |first_month_spend|later_spend|
        -----------+-----+-----------------+-----------+
                101|Arjun|                0|      66500|
                102|Priya|                0|      22000|
                105|Ravi |                0|        500|

9. Find Duplicates
    Find customers who placed orders for the same product more than once
    ex: SELECT customer_id, product, COUNT(*) AS times_ordered
        FROM orders
        GROUP BY customer_id, product
        HAVING COUNT(*) > 1;
10. Search & Filter Flexibly
    Search orders by keyword, date range, and status
    ex: SELECT o.order_id, c.name, o.product, o.amount, o.order_date
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE o.product LIKE '%laptop%'            -- keyword search
        AND o.order_date BETWEEN '2024-01-01'
                            AND '2024-12-31'    -- date range
        AND o.status IN ('delivered', 'pending') -- multiple statuses
        ORDER BY o.order_date DESC
        LIMIT 20;

"""
