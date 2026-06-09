"""
PostgreSQL
    technically an Object-Relational Database Management System (ORDBMS)
    support for NoSQL-like behavior such as JSONB documents
    key-value pairs via hstore
    Write-Ahead Logging for point-in-time recovery and streaming replication
    the ability to store documents using multiple paradigms within a single system.
    Why PostgreSQL wins
        Full ACID
        MVCC
        JSONB + SQL
        Extensible
        Open source / free
        PostGIS for geo
        pgvector for AI
        WAL + point in recovery
        Runs on any OS
    Postgres vs Other
        vs MySQL
            ✓ Superior MVCC concurrency
            ✓ Richer data types (arrays, JSONB, range)
            ✓ Better standards compliance
            ✓ Advanced indexing (partial, expression)
            ~ MySQL faster on simple reads (~20-30%)
        vs SQLite
            ✓ Multi-user concurrent access
            ✓ Client-server architecture
            ✓ Scales to terabytes
            ✓ Full replication support
            ~ SQLite for embedded/local only
        vs MongoDB
            ✓ Full ACID across multiple docs
            ✓ JSONB = document-style in SQL
            ✓ Complex joins & aggregations
            ✓ Stronger consistency guarantees
            ~ Mongo for pure document at scale
    psql (CLI)
        built-in postgres terminal client
        psql -h host -U user -d dbname
        \l          -> list databases
        \dt         -> list tables
        \d orders   -> describe table
        \i file.sql -> run a SQL file
        \timing     -> show query execution time
        \x          -> expanded output
        \e          -> open query in editor
        psql -U admin -d dbname -c "SELECT * FROM orders;"
    Data Types
        Arrays
            let you store multiple values of the same type in one column.
            Every Postgres type can be an array — integer[], text[], uuid[].
            You query them with array operators: @> for containment, && for overlap, ANY() for membership tests.
            ex: CREATE TABLE posts (
                    id        bigint PRIMARY KEY,
                    title     text,
                    tags      text[])
        Hstore
            key-value store inside a column
            a flat map of text keys to text values.
            ex: CREATE TABLE products (id bigint, attrs hstore);
        Composite type
            let you define a structured type and use it as a column type
            ex: CREATE TYPE address AS (
                    street  text,
                    city    text,
                    country text,
                    postcode text
                );
        JSONB
            Structured document in a column
            Binary JSON stored inline.
            Right when your data has variable or evolving shape that cannot be normalised.
            Use jsonb_path_ops GIN for containment queries.

    UUID vs serial vs identity
        Choosing your primary key generation strategy is one of the most consequential schema design decisions.
        SERIAL / BIGSERIAL
            old Postgres way
            syntactic sugar that creates a sequence and wires it to a DEFAULT
            sequence is a separate object not tightly bound to the table
            can cause issues when dumping/restoring or renaming tables
            because the sequence name is independent of the table.
            GENERATED ALWAYS
                prevents manual inserts into id
        GENERATED AS IDENTITY
            SQL standard way, added in Postgres 10.
            semantically equivalent to serial but properly bound to the column.
            Prefer this over serial for all new tables.
        UUIDs
            128-bit globally unique identifiers
            ideal for distributed systems, multi-tenant architectures
            and systems that generate IDs before writing to the database.
            UUID v7 is time-ordered
                first bytes encode a millisecond timestamp
                so new rows always append to the end of the B-tree, just like a sequential integer.

    PostgreSQL Internals
        MVCC — Multi-Version Concurrency Control
            Readers never block writers — writers never block readers
            Every row has two hidden system columns
                xmin (the transaction ID that created this version)
                xmax (the transaction ID that deleted/updated it, 0 if alive).
            UPDATE never overwrites in place
                Postgres does not overwrite it
                it marks the old row dead (sets xmax) and writes a brand-new row version with a new xmin.
            DELETE just sets xmax.
            Each transaction sees a snapshot of the DB at its start time.
            A row is "visible" to a txn if xmin ≤ txn_id < xmax (simplified).
            This is what makes consistent reads free.
            The cost
                dead row versions ("dead tuples") pile up.
                That's what VACUUM cleans.
                High UPDATE/DELETE workloads create "bloat" if VACUUM falls behind.
        Heap
            main data file for each table.
        ACID guarantees
            Atomicity
                All or nothing. A crash mid-transaction rolls back everything.
                Powered by WAL.
            Consistency
                Constraints, triggers, and rules always hold before and after a txn.
            Isolation
                Concurrent txns don't see each other's in-progress work.
                Degree controlled by isolation level.
                READ COMMITTED(default):
                    sees committed rows at the start of each statement.
                    Most apps use this.
                    Danger: non-repeatable reads within a long txn.
                REPEATABLE READ:
                    snapshot taken at first statement.
                    Same row returns same value throughout the txn.
                    Prevents non-repeatable reads.
                SERIALIZABLE
                    transactions appear to run one-at-a-time.
                    Postgres uses SSI (Serializable Snapshot Isolation)
                        detects conflicts and may abort one party.
                    Use for financial correctness.
                Postgres has no READ UNCOMMITTED
                    it's silently upgraded to READ COMMITTED.
                    Dirty reads simply don't happen here.
            Durability
                Once COMMIT returns, the data is safe — even if the server crashes 1ms later.
                WAL ensures this.
        WAL — Write-Ahead Log
            Before Postgres touches any data page on disk,
            it writes what it's about to do to the WAL first — hence "write-ahead."
            flushed on COMMIT
            The WAL lives in pg_wal/ as sequential 16MB segment files.
            crash recovery
                on restart, Postgres replays WAL from the last checkpoint to restore consistency
            replication
                standbys receive and replay the same WAL records in real time
                standbys do exactly what the primary did.
        Shared buffers & buffer pool
            Postgres doesn't read from disk on every query.
            It caches 8KB data pages in a shared memory region called shared_buffers.
            A cache hit is ~100x faster than a disk read.
            frequently accessed pages accumulate a "usage count" that protects them from eviction
            Monitor buffer hit rate via pg_stat_database.
            If blks_read is high relative to blks_hit, your buffer pool is too small.
        VACUUM & autovacuum
            MVCC leaves dead tuples behind.
            VACUUM reclaims that space and makes it available for new rows.
            visibility map
                updates which pages are safe for index-only scans
                it prevents transaction ID(versions) wraparound
                a hard limit at ~2 billion transactions.
            If you neglect VACUUM long enough, Postgres will literally shut down to protect data integrity.
            Autovacuum
                background daemon that runs this automatically,
                but it needs tuning on high-traffic tables
        TOAST storage (The Oversized-Attribute Storage Technique)
            Data pages are 8KB. A 500KB text value won't fit.
            automatically compresses and/or moves large values to a hidden companion "TOAST table."
            Your queries are completely unaffected — Postgres fetches it transparently.
        Visibility map & FSM (Free Space Map)
            Two compact companion files live alongside every table
            Free Space Map (FSM)
                tracks free bytes available in each heap page
                On INSERT, Postgres consults it to find a page with room rather than scanning from page 0
                VACUUM updates it as dead tuples are reclaimed.
            Visibility Map (VM)
                has one bit per heap page.
                If set, all tuples on that page are visible to all transactions.
                Autovacuum sets these bits.
                Index-only scans use the VM — if a page is all-visible,
                the index alone answers the query without touching the heap at all.
                This is a massive performance win for read-heavy workloads.
        Checkpoint & BGWriter
            Postgres doesn't flush every dirty page immediately.
            Dirty pages accumulate in shared buffers.
            A checkpoint is the moment all dirty pages are flushed to disk, creating a clean recovery point.
            After a checkpoint, crash recovery only needs to replay WAL from that point forward.
            Checkpoints
                happen every checkpoint_timeout (default 5 min) or when WAL reaches max_wal_size
            BGWriter (Background Writer)
                pre-emptively flushes dirty pages between checkpoints to spread disk I/O
                prevent checkpoint spikes.
        Process model — postmaster & backends
            Postgres uses a multi-process model (not multithreaded).
            Postmaster
                parent process that listens for TCP connections and forks a new backend OS process per client.
                All backends share shared_buffers via shared memory but have separate stacks.
            Key background daemons
                autovacuum launcher
                bgwriter
                checkpointer
                walwriter
                stats collector
            Each backend uses ~5–10MB of RAM for process overhead alone.
            At 500 connections that's 2.5–5GB before any query work
            pgBouncer(connection pooler)
                essential in production
                Most deployments keep actual Postgres connections at 50–100
                let pgBouncer multiplex thousands of app connections onto them.
        OID(Object Identifier) & system catalogs
            Every object in Postgres — every table, index, function, type — has an Object Identifier (OID).
            These are the primary keys of the system catalogs
            system catalogs
                a set of internal tables in pg_catalog that describe the entire database.
                pg_class
                    all tables/indexes/views
                pg_attribute
                    all columns
                pg_index
                    index definitions
                pg_proc
                    functions
                pg_stat_activity
                    live backend state
                pg_locks
                    current lock state
                pg_stat_user_tables
                    seq scans
                    dead tuples per table
                pg_stat_user_indexes
                    which indexes are actually being used

    Query planning
        EXPLAIN
            shows the plan Postgres intends to run
            estimated costs, row counts, join strategies.
        EXPLAIN ANALYZE
            actually executes the query and shows real timings.
        EXPLAIN ANALYZE BUFFERS
            additionally shows how many shared buffer pages were read (hits vs misses).
            ex: EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
                SELECT ...
        Seq scan vs index scan vs bitmap scan
            three ways Postgres can access rows from a table
            planner picks based on cost estimates.
            sequential scan
                reads every page of the heap from start to
                for small tables or queries that need most rows,
                it's actually faster than an index because it does sequential I/O (which is fast)
                avoids the overhead of index lookups.
            index scan
                traverses the B-tree index to find matching entries
                for each entry fetches the actual row from the heap at a random location.
            bitmap index scan
                middle ground
                First, Postgres scans the index entirely and builds an in-memory bitmap
                of which heap pages contain matching rows.
                it reads those pages in physical order (sequential-ish), visiting each page at most once
        Hash join vs merge join vs nested loop
            nested loop join
                takes each row from the outer table and probes the inner table for matches.
                If the inner table has an index on the join column, each probe is O(log n)
            hash join
                reads the smaller of the two tables
                hashes its join key into a hash table in memory (work_mem)
                then streams the larger table through that hash table.
                default for joining two large unsorted tables when no usable index exists.
            merge join
                requires both inputs to already be sorted on the join key
                It advances a pointer through each sorted set simultaneously
                like merging two sorted lists. O(n log n)
                for the sort phase, then O(n + m) for the merge.
        JIT (Just-In-Time) compilation
            For query-intensive analytics, Postgres can JIT-compile parts of the execution plan using LLVM.
            Instead of interpreting expression evaluation row-by-row
            it compiles the expression to native machine code.
            This is most beneficial for long-running queries that evaluate complex expressions
    Indexing Strategies
        B-tree (default)
            balanced tree structure where every leaf node is at the same depth,
            leaf nodes are linked in a doubly-linked list ordered by the indexed value.
            once you find the start of a range, you just walk right along the leaf level
            B-trees handle
                equality (=), range queries (<, >, BETWEEN)
                IS NULL, prefix matching (LIKE 'foo%')
                ORDER BY / GROUP BY
            B-tree can't handle
                LIKE '%foo' (suffix)
                case-insensitive search without a functional index
                full-text search
                array containment
        Hash index
            Hash indexes store a hash of each value and map it to the heap location.
            Lookup is O(1) for equality — faster than B-tree's O(log n) in theory.
            But they only support =.
            No ranges, no ordering, no NULL checks, no multicolumn.
        GIN — Generalized Inverted Index
            GIN is designed for types where a single value contains multiple searchable "keys"
            arrays, JSONB, and tsvector (full-text search).
            For arrays
                WHERE tags @> ARRAY['postgres', 'indexing'] (containment).
            For JSONB
                WHERE data @> '{"status": "active"}'.
            For FTS
                WHERE to_tsvector(body) @@ to_tsquery('postgres').
        GiST — Generalized Search Tree
            framework for indexing types with complex overlap/proximity relationships
            PostGIS extension uses GiST for spatial indexes.
            Postgres's built-in range types (daterange, tsrange, int4range) use GiST.
            The pg_trgm extension uses GiST for fuzzy text search.
            GiST supports
                equality, range overlap, containment
                nearest-neighbor (ORDER BY location <-> point)
        BRIN — Block Range Index
            designed for very large tables where the data has a natural physical
            correlation with the indexed column
            time-series data where rows are inserted in timestamp order, or auto-increment IDs.
            BRIN stores only the min and max value for each range of heap pages (default: 128 pages per range)
        SP-GiST — Space-Partitioned GiST
            data that partitions naturally into non-overlapping regions: quad-trees,
            k-d trees, radix trees (tries), and space-partitioning trees.
            Built-in Postgres types that use SP-GiST: point (2D spatial),
            text (prefix/trie matching), inet (IP addresses and subnets), range types.
            works well for
                IP routing (WHERE net >>= '192.168.1.100')
                phone number prefix matching
                2D point proximity
        Partial indexes
            only indexes rows that satisfy a WHERE clause.
            A partial index on just pending orders is tiny, fast to update
            the planner picks it up for the exact queries you care about.
        Expression / functional indexes
            Postgres can index the result of any deterministic function or expression on a column.
            for case-insensitive search, computed values, and JSON field extraction.
        Covering indexes - INCLUDE
            stores additional columns alongside the index key using the INCLUDE clause.
            These extra columns are not part of the B-tree structure (not searchable)
            they're just stored in the leaf pages.
            This enables index-only scans
                the query executor finds matching rows via the index
                reads their data without ever touching the heap.
        Multicolumn indexes
            multicolumn index on (a, b, c) is usable for queries filtering on a, a + b, or a + b + c
            but not on b alone or c alone. This is the left-prefix rule for B-trees.
            Column order matters enormously.
        Index-only scans
            index-only scan happens when the query only needs columns that are
            all present in the index (as key columns or INCLUDE columns)
            visibility map says the heap page is all-visible (meaning VACUUM has run).
            the executor never touches the heap at all.
        Bloom filters
            The bloom extension provides a bloom filter index
            probabilistic structure that can test "does this row possibly match this
            combination of equality conditions?"
            Many-column arbitrary equality combos
        Building indexes on production
            CONCURRENTLY takes two table scans but never blocks reads or writes.
            Essential for zero-downtime deployments.




    SERIALIZABLE isolation level
        Other databases
            Most databases implement SERIALIZABLE using locking
            every read locks the row, creating massive contention.
        PostgreSQL
            PostgreSQL SERIALIZABLE is optimistic, it assumes transactions won't conflict,
            lets them all run freely, and only intervenes when it proves they actually did conflict.
            uses SSI (Serializable Snapshot Isolation)
            a lock-free algorithm that detects dangerous patterns and aborts one transaction
            rather than blocking both.
            1. Every transaction runs with a snapshot
                Reads don't block writes. Writers don't block readers.
                No read locks acquired.
            2. PostgreSQL silently tracks dependencies between transactions
                specifically which transactions read data that
                another transaction later wrote (called "rw-anti-dependencies").
            3. If a dangerous cycle is detected
                concurrent execution could not have happened in any serial order
                PostgreSQL aborts one transaction with error code 40001 (serialization_failure)
            4. Your code catches the error and retries.
    Advisory locks
        application-defined locks that have no connection to any actual database object.
        they're just named integers you can lock and unlock at will.
        They're perfect for things like distributed cron jobs (only one server should run the nightly batch)
        application-level mutexes, or ensuring only one worker processes a particular job type.

    Generated columns
        columns whose value is automatically computed from other columns in the same row
        ex: CREATE TABLE users (
            id PRIMARY KEY,
            first_name text NOT NULL,
            last_name  text NOT NULL,
            full_name  text GENERATED ALWAYS AS (first_name || ' ' || last_name) STORED
        )
    Soft deletes and audit trails
        patterns for preserving the history of your data rather than destroying it.
        A soft delete means marking a row as deleted rather than actually removing it with DELETE
        The row stays in the table, invisible to normal queries
        but available for recovery, audit, and foreign key integrity.

    LATERAL joins
        subquery on the right side that can reference columns from tables to its left
        Without LATERAL, a subquery in a FROM clause is completely independent.
        ex: SELECT c.name, recent.*
            FROM customers c
            CROSS JOIN LATERAL (subquery...)
    DISTINCT ON
        PostgreSQL extension to standard SQL that keeps only the first row for each unique value of expr
    FILTER in aggregates
        lets you apply a WHERE clause to a specific aggregate function
        without affecting other aggregates in the same query.
        ex: SELECT
                COUNT(*) FILTER (WHERE status = 'completed')      AS completed,
                SUM(amount) FILTER (WHERE status = 'completed')   AS completed_revenue,
            FROM orders;
    GROUPING SETS, CUBE, ROLLUP
        multi-level aggregation without writing multiple queries and UNION ALLing them together.
        ROLLUP
            produces subtotals along a hierarchy
            the classic "grand total at the bottom"
        CUBE
            produces all possible combinations of subtotals
        GROUPING SETS
            lets you specify exactly which combinations you want
            ex: GROUP BY GROUPING SETS (
                    (region, channel),
                    (region, product_category),
                    (region),
                    ()
                );
    RETURNING clause
        lets INSERT, UPDATE, and DELETE return column values from the affected rows — in a single round trip.
        This eliminates the common pattern of "insert a row, then SELECT it back to get the generated ID.
        RETURNING * returns all columns
        ex: INSERT INTO users (email, name)
            VALUES ('alice@example.com', 'Alice')
            RETURNING id, created_at;
    Upsert — INSERT ON CONFLICT
        It atomically handles the "insert if not exists, update if exists" pattern

    PostgreSQL FTS (Full text search)
        1. Raw text
        2. to_tsvector() normalises
            Lowercases, strips stop-words, stems each word to its root (lexeme)
        3. tsvector stored/indexed
        4. to_tsquery() parses query
            "fox & jump" → both lexemes must appear
        5. @@ operator matches
            GIN index lookup — O(1) per lexeme, no full table scan
        6. ts_rank() scores results
            Ranks by lexeme frequency, position, and coverage
        pg_trgm extension — trigram fuzzy search
            Splits words into 3-character chunks ("trigrams")
            Two strings are similar if they share many trigrams.

    JSON vs JSONB
        Both types store valid JSON
        JSON (TEXT)
            Stored as-is, exact text copy
            Preserves whitespace, key order and duplicate keys
        JSONB (BINARY)
            Stored decomposed as binary tree
            Keys sorted, whitespace removed, last duplicate key wins
    GIN indexes on JSONB
        Without an index, any @>, ?, or ->> query does a full sequential scan.
        GIN index on a JSONB column creates an inverted index over every key and value in every document.

    Replication
        PostgreSQL has two fundamentally different replication models.
        PHYSICAL (STREAMING)
            Copies raw WAL bytes
            Exact byte-for-byte replica
            Same PG version required
            Used for: HA, read replicas
            Lag: milliseconds
        LOGICAL REPLICATION
            Copies decoded SQL changes
            Row-level, selective
            Cross-version, cross-OS
            Used for: CDC, migrations, partial replication
        Zero-downtime production topology
            A typical highly-available cluster has a primary, at least one sync standby for durability,
            async replicas for read scaling, and an orchestrator that monitors and fails over automatically.
        Synchronous vs asynchronous replication
            With async replication, a committed transaction exists only on the primary until the
            standby catches up — a crash can lose those transactions.
            Sync replication waits for acknowledgment, eliminating that window.
        Patroni
            automated failover orchestration
            most widely-used PostgreSQL HA solution
            It uses a distributed consensus store (etcd, Consul, or ZooKeeper) to elect a leader,
            manage promotion, and ensure only one primary ever exists — preventing split-brain.
            it does
                Health monitoring
                Leader TTL expires
                    If the primary's heartbeat stops, its leader lock in etcd expires (default 30s TTL).
                    This is the failover trigger
                Election
                    Standbys race to acquire the leader lock.
                    The most up-to-date standby (highest WAL LSN) wins via a compare-and-swap atomic operation
                Promotion
                    standby becomes writable primary
                Old primary fenced
                    If old primary comes back, Patroni demotes it to standby
    Performance tuning
        shared_buffers — the buffer cache
            PostgreSQL's internal cache of data pages.
            The "25% of RAM" rule is a starting point
        effective_cache_size — planner hint only
            tells the query planner how much total memory is available for caching
            (shared_buffers + OS page cache combined).
        max_connections
            the hidden memory trap
            Every connection spawns a backend process consuming ~5–10 MB of RAM at idle
            At 500 connections with work_mem=64MB doing sorts, you can easily OOM a 32 GB server.
            The answer is not a lower limit; it's connection pooling.
        PgBouncer — connection pooling
            sits between your app and PostgreSQL
            multiplexing thousands of app connections onto a small pool of real backend processes
            This is the right solution to connection pressure — not raising max_connections.
        wal_buffers — the WAL write buffer
            In-memory buffer for WAL records before they're flushed to disk
            The default auto-tunes to 1/32 of shared_buffers, capped at 16 MB.
            On high-write workloads with many concurrent committing transactions,
            pushing this to 64 MB can reduce WAL write contention.
        Checkpoint tuning
            checkpoint flushes all dirty pages from shared_buffers to disk.
            The goal is to spread checkpoint I/O over a long window so it's invisible to application queries.
        pg_stat_statements
            find slow queries
            single most important extension for production performance work
            It tracks execution statistics for every distinct query, aggregated across all runs.
        auto_explain — automatic slow query logging
            Automatically logs the EXPLAIN ANALYZE plan for any query exceeding a time threshold
            without having to reproduce the query manually.
        pg_prewarm — warm the buffer cache
            After a server restart, shared_buffers is cold — the first queries after startup are slow
            with autoprewarm it can restore the cache state from before the restart automatically.
    Security
        Role-based access control (RBAC)
            A role can be a login user, a group, or both.
            GRANT/REVOKE system controls what each role can do
                on databases, schemas, tables, columns, sequences, functions, and more.
        Row-level Security (RLS)
            lets you restrict which rows a role can see or modify
            Each user only sees their own data even if they share the same table
            Critical for multi-tenant applications.
        pgcrypto
            encryption inside Postgres
            adds cryptographic functions directly in SQL
            symmetric encryption, hashing, password hashing with bcrypt, and PGP.

    PostgreSQL Extensions Ecosystem
        installed via CREATE EXTENSION <name>;
        Spatial & Vector
            PostGIS
                add geographic/geometric types & functions
                queries like find all points within 10KM of this coordinate
            pgvector
                stores & indexes high-dimensional vectors (embeddings)
        Monitoring & Stats
            pg_stat_statements
                tracks execution statistics (call,mean time,rows)
                for query performance analysis
        Scheduling & Automation
            pg_cron
                runs SQL jobs on a cron schedule
                directly inside postgres
        Time series
            TimescaleDB
                wraps regular tables as hypertables automatically partitioned by time
                adds time series functions and compression
        Auditing
            pgaudit
                logs detailed session/object-level audit trails
                required for SOC2/HIPAA compliance
        UUID
            gen_random_uuid()
                built in
        Partitioning management
            pg_partman
                automates creation and maintenance of time-or-serial based partitions
        Fuzzy Text Search
            pg_trgm
                enables Fuzzy string matching
                fast LIKE/ILIKE queries via GIN/GIST indexes
            unaccent
                text search dictionary that strips accents from words
        Semi structured data
            hstore
                key value pairs stored in single column
            ltree
                stores & queries tree-structured labels

    Monitoring & observability
        system catalog views
            pg_stat_activity
                live snapshot of all connections and what theyre doing
            pg_stat_user_tables
                per table statistics
            pg_stat_user_indexes
                index usage stats
            pg_stat_bg_writter
                single row view showing background writer & checkpoint activity
        Prometheus Stack
            postgres_exporter + Prometheus + grafana
                scrapes postgres metrics, exposes them as Prometheus metrics
                grafana dashboards visualize them
        Log Analysis
            pgBadger
                parses Postgres log files, generates HTML report

    PostgreSQL Cloud & Modern Tooling
        AWS
            Amazon RDS for PostgreSQL
                limited superuser access
                Multi-AZ
                Read replicas
                can only install listed extensions
            Amazon Aurora PostgreSQL
                AWS-reimagined Postgres engine
                Serverless
                upto 5x faster than RDS
        Google
            Cloud SQL for PostgreSQL
                similar to RDS
            AlloyDB for PostgreSQL
                similar to Aurora
        Serveless
            Neon, Supabase, Citus
        Containerization
            Docker
                run postgresql in docker locally
        Schema migrations
            Flyway
                migrations as versioned SQL files
            Liquibase
                more flexible, migrations as XML, YAML, JSON or SQL

"""
