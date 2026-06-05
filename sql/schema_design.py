"""
Database Schema Design
    normalization is about eliminating redundancy
    Redundancy causes
        update anomalies
            the same fact stored in N places
            change a fact in one place, forget another
        insert anomalies
            can't record a fact without unrelated data
            ex: table cols: customer_id 🔑	customer_name	customer_city	city_tax_rate
            A city's tax rate is stored on customer rows.
            You want to add a new city before any customer from that city signs up.
            You can't — there's no row to attach it to.
        delete anomalies
            lose a fact accidentally when deleting something else
            ex: for above table
            All customers from Hyderabad are deleted.
            Along with them, you lose the only record that Hyderabad's tax rate is 0.15.
            The tax rate information is gone
    normalization ladder
        each form builds on the last
        You can't be in 2NF without satisfying 1NF
        You can't be in 3NF without satisfying 2NF
    1NF
        Atomic values, unique rows
        Every cell holds exactly one value.
        No repeating column groups like phone1, phone2, phone3
        Each value needs its own row.
        Every row is uniquely identifiable.
    2NF
        No partial dependencies
        Every non-key column depends on the whole primary key, not just part of it.
        Only relevant when the PK is composite.
        for 1 column primary key, 2NF is automatically satisfied.
    3NF
        No transitive dependencies
        Every non-key column depends directly on the primary key
        not on another non-key column.
        No "A → B → C" chains.

    Super Key
        any set of columns that can uniquely identify a row
        can have extra unneccessary columns
        they just need to uniquely identify rows
    Candidate key
        is a super key with no extra columns, minimum needed to be unique
        any minimal set of columns that uniquely identifies a row.
        A table can have multiple candidate keys.
    Primary Key
        one candidate key you pick to be official identifier
        you can have multiple candidate keys but only one primary key
    Alternate Key
        candidate keys that are not choosen as primary key

    Functional Dependency
        if i know your student id, i can always figure out your name.
        Student ID -> Name, Student ID determines Name

    BCNF (Boyce-Codd Normal Form)
        3NF has a small loophole
            X -> Y is allowed for
            1. X is a super key (includes candidate keys)
            2. Y is part of some candidate key
        BCNF removes 2nd points
        BCNF closes that loophole with a stricter rule.
        Every dependency must come from a candidate key
        if non-candidate key determining another column, that's BCNF violation
        ex: student 🔑	course 🔑	teacher
            Ravi	    SQL	        Dr. Sharma
            Priya	    SQL	        Dr. Sharma
            Ravi	    Python	    Dr. Nair
            Priya	    Python	    Dr. Nair
            Teacher teaches only one subject, Teacher -> Subject
            Candidate key (Student,Teacher) together uniquely identify a row
            Teacher is not a candidate key but it's determining Subject, BCNF violation
            Update anomoly
                if Sharma switches from SQL to Java, you will have to update every row with Sharma
                if missed one, now data says he teaches both SQL & Java - corupted data
        Check for BCNF
            1. find all functional dependencies in the table
            2. for each dependency X -> Y, is X a candidate key?
            3. if yes for all -> Table is in BCNF
            4. if no for any, split the table
    Denormalization
        when to intentionally break the rules
        You're building a read-heavy reporting or analytics system.
        The same JOINs run millions of times per day.
        You've measured the JOIN cost and it's the bottleneck.
        Star Schema & Snowflake Schema comes in Data Warehousing
        designed for analytics & reporting (OLAP)
    Decomposition
        splitting one table into two or more smaller tables
        each containing a subset of the original columns
        such that you can perfectly reconstruct the original table by joining them back together.
        being able to reconstruct it — is what makes a decomposition valid.

Full-text search in SQL databases
    Naive LIKE '%search term%' scans every row character-by-character — it's slow and dumb.
    Full-text search instead pre-processes text into an index of normalized tokens,
    so searches hit an index rather than raw strings.
    PostgreSQL
        tsvector
            preprocessed, sorted list of lexemes (stemmed words) with their positions.
            PostgreSQL strips stop words ("the", "are")
            stems the rest ("cats" → "cat", "running" → "run"), and stores the result.
            You never store the original prose — you store this compact structure.
        tsquery
            parsed form of a search query
        GIN on a tsvector column
    MySQL
        FULLTEXT index declared on columns
    DB FTS vs. Elasticsearch
        DB full text search
            when your data already lives in the database,
            your search needs are modest, and you don't want to maintain another service.
            PostgreSQL
                handles ranking, phrase proximity, highlighting,
                and multilingual stemming without leaving SQL.
        Elasticsearch
            when you need fuzzy/typo-tolerant matching, faceted search,
            massive scale with sub-10ms latency, or complex relevance tuning.
            PostgreSQL's FTS has no built-in fuzzy matching
            a typo in a query returns nothing unless you pair it with pg_trgm (trigram similarity).

Partitioning
    Data split across multiple storage files — but still on one database server.
    The DB engine manages it transparently. Applications see one table.
    ex: CREATE TABLE orders (
            id          BIGINT,
            customer_id INT,
            order_date  DATE        NOT NULL,
            total       DECIMAL(12,2),
            status      VARCHAR(20)
        ) PARTITION BY RANGE (order_date);
    partitioning solves
        Query speed
            query planner skips entire partitions that
            can't contain matching rows, called partition pruning.
        Fast archiving and deletion
            Dropping an old partition (DROP TABLE orders_2021) is instant
            it's one file operation
        Storage tiering
            Recent partitions on fast NVMe SSDs, old partitions on slow cheap HDDs or cold object storage
            all behind one logical table name.
            Massive cost savings for time-series or audit data.
    Partition Types
        Range partitioning
            Ordered, contiguous value ranges.
            Adjacent data stays together physically.
            ex: Time-series, logs, orders, events
        List partitioning
            Explicit set of values per partition.
            Best for categorical data
            Common in multi-region or multi-tenant systems
            ex: Multi-tenant, geo-partitioned data
        Hash partitioning
            Key is hashed → uniform distribution across N partitions.
            Use when you need uniform write distribution
            ex: Evenly distributing write load
        Composite partitioning
            Range outer, Hash inner — best of both.
            ex: Large time-series with many customers

Sharding
    Data split across multiple database servers.
    Each shard is a fully independent DB.
    The app or a routing layer must know which shard to query.
    Massively more complex.

Partitioning vs Sharding
    Partitioning is a database feature.
    Sharding is a system architecture decision.
    sharding is operationally very expensive.

Replication
    Every replicated database has one node that accepts writes — the primary (also called master)
    one or more replicas (also called secondaries or read replicas) that mirror it.
    The primary is the source of truth. Replicas are copies.
    Replication lag
        time delta between when a write commits on the primary and when that change appears on a replica.
    transaction consistency
        A replicated system with async replication is eventually consistent
        replicas will catch up, but not instantly.
    Replica promotion
        if the primary goes down, a replica can be promoted to primary.
    Read replicas aren't sharding
        replicas hold the full dataset.
    Cascading replicas
        replicas can themselves have replicas (replica of a replica)
        used to distribute load geographically.

"""
