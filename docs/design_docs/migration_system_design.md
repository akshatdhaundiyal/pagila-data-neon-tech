# pagila-data-neon-tech Migration System Design

This document provides a detailed, verbose explanation of the design and logic implemented in the pagila-data-neon-tech migration system. The system is engineered to handle common pitfalls in PostgreSQL migrations, specifically when moving from a full local instance (PG 18 development dumps) to a managed cloud environment like Neon (Postgres 17).

## 1. System Architecture Overview

The system is refactored into a modular structure to separate concerns and ensure maintainability.

- **`sql/`**: Contains raw source SQL files (`pagila-schema.sql`, `pagila-insert-data.sql`).
- **`src/pagila/`**: The core logic package.
    - `cleaner.py`: Performs string-level and regex-level SQL transformations.
    - `database.py`: Handles connection pooling (via standard psycopg2) and execution blocks.
- **`main.py`**: The orchestration entry point.
- **`verify.py`**: Independent verification suite.

---

## 2. Migration Lifecycle

The migration is executed in a strictly defined sequence to satisfy dependency constraints and ensure a clean environment.

### Phase 0: Environment Reset
Before any objects are created, the script executes:
```sql
DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;
DROP SCHEMA IF EXISTS legacy CASCADE;
```
**Rationale**: `CASCADE` ensures that all tables, views, and functions are removed. Recreating `public` is necessary because dropping it removes the default schema.

### Phase 1: Structural Schema Initialization
The base schema is loaded *without* Foreign Key constraints.
**Internal Logic**: The script scans `pagila-schema.sql` and identifies lines containing `Type: FK CONSTRAINT`. It splits the file at this boundary.
- **Part A (Base)**: Tables, Views, Types, and Primary Keys.
- **Part B (Post-Constraints)**: Foreign Keys.

### Phase 2: Data Population
The script executes `pagila-insert-data.sql`.
**Transformation Logic**: Ownership commands (`OWNER TO postgres`) are stripped or replaced dynamically to prevent "permission denied" errors in Neon.

### Phase 3: Referential Integrity Enforcement
The Foreign Key constraints (Part B of Phase 1) are executed last.
**Rationale**: This solves the "Circular Dependency" problem (e.g., the `staff` table depends on `store`, and `store` depends on `staff` via its manager). By inserting all data first, the constraints can be applied to existing, valid rows.

---

## 3. Detailed Script Logic

### 3.1 `cleaner.py`: The SQL Transformation Engine

This module contains the `clean_sql` function, which is the "intelligence" of the migrator. It processes SQL strings before they reach the database.

#### A. Ownership Replacement
The script replaces `OWNER TO postgres` with `OWNER TO neondb_owner`.
- **Why?**: In managed databases, you do not have a `postgres` superuser. Creating objects owned by a non-existent user or trying to assign ownership to a superuser you don't control results in immediate failure.

#### B. The Generated Column Fix (Postgres 17 Compatibility)
PostgreSQL 17 requires the `STORED` keyword for all generated columns. Some versions of Pagila (or dumps from PG 18) omit this, assuming "virtual" generated columns. Neon (PG 17) does not support virtual columns.
**Logic Snippet**:
```python
if "GENERATED ALWAYS AS" in line and "STORED" not in line:
    if line.strip().endswith(","):
        line = re.sub(r"(\)\s*),$", r") STORED,", line)
    # ... more variations ...
```
This logic detects generated column definitions and injects the `STORED` keyword before the terminating comma or parenthesis.

#### C. Stripping PSQL Meta-commands
The script identifies lines starting with `\` (like `\restrict` or `\set`).
- **Why?**: These are specific to the `psql` command-line tool. The `psycopg2` driver does not understand them and would throw a syntax error.

### 3.2 `database.py`: execution and Reset

This module encapsulates the lower-level database interactions.

- **`execute_sql(conn, sql_content, description)`**:
    - Wraps execution in a transaction block.
    - If a command fails, it automatically issues a `conn.rollback()` to prevent the database from being left in an "idle in transaction" error state.
- **`reset_database(conn)`**:
    - Hard-coded schema reset logic to ensure the user starts with a 100% accurate representation of the Pagila dataset.

### 3.3 `main.py`: Orchestration

The orchestrator manages the high-level flow:
1. Opens the database connection.
2. Reads the SQL files from the `sql/` directory.
3. Passes the content through `clean_sql` to get the base structural components and the deferred constraints.
4. Executes segments in the order: **Reset -> Structural -> Data -> Constraints**.

---

## 4. Specific Workarounds for Neon Tech

1. **`session_replication_role` Bypassed**: Initially, we attempted to use `SET session_replication_role = 'replica'` to disable triggers during data load. However, Neon restricts this parameter to superusers.
2. **Circular Dependency Fix**: Since triggers couldn't be disabled globally, we implemented the "Deferred Constraint" pattern by manually splitting the dump into structural and relational parts.
3. **Trigger Cleanup**: Attempting to run `ALTER TABLE ... DISABLE TRIGGER ALL` on system triggers (like RI constraints) fails in Neon. The `cleaner.py` logic identifies and removes these commands, relying instead on the phased execution order to maintain data integrity.

---

## 5. Verification Logic (`verify.py`)

Verification is performed via a standalone script to maintain a "trust but verify" approach.
- **Table Discovery**: Queries `information_schema.tables` to ensure all 23 base tables are present.
- **Data Integrity**: Counts records in key tables (e.g., `actor`).
- **Schema Context**: Uses explicit schema prefixing (`public.actor`) because the migration script occasionally modifies the `search_path` within a session, and a separate verification run ensures the schema is globally accessible.
