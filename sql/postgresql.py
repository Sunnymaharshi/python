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


"""
