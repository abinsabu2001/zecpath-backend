# ZecPath Database Migration Plan

## Current Database
- SQLite is currently used for development.
- Database backup is created using the custom Django backup command.

## Production Database
- PostgreSQL will be used for production.
- Psycopg 3 is installed for PostgreSQL connectivity.
- Connection settings will be configured through environment variables.

## Migration Steps

1. Create a PostgreSQL production database.
2. Configure PostgreSQL credentials using environment variables.
3. Update Django `DATABASES` settings for PostgreSQL.
4. Run Django migrations:
   `python manage.py migrate`
5. Create a database backup before migration.
6. Restore/import required data into PostgreSQL.
7. Verify users, jobs, and other application data.
8. Test application functionality after migration.
9. Keep the SQLite backup available for rollback if required.

## Backup and Rollback

- Create a backup before database changes.
- Verify the backup by restoring it into a test database.
- Keep recent backups available for recovery.
- If migration fails, restore from the verified backup.

## Verification

- Run `python manage.py check`
- Verify database connectivity.
- Verify job records and active jobs.
- Verify database indexes and query performance.
- Test the application after migration. 