"""
PostgreSQL


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
