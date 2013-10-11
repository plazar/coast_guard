import warnings
import string

import sqlalchemy as sa

import config
import errors

import schema
import utils

null = lambda x: x
    
def fancy_getitem(self, key):
    filterfunc = null
    if (type(key) in (type('str'), type(u'str'))) and key.endswith("_L"):
        filterfunc = string.lower
        key = key[:-2]
    elif (type(key) in (type('str'), type(u'str'))) and key.endswith("_U"):
        filterfunc = string.upper
        key = key[:-2]
    if self.has_key(key):
        return filterfunc(super(self.__class__, self).__getitem__(key))
    else:
        matches = [k for k in self.keys() if k.startswith(key)]
        if len(matches) == 1:
            return filterfunc(super(self.__class__, self).__getitem__(matches[0]))
        elif len(matches) > 1:
            raise errors.BadColumnNameError("The column abbreviation " \
                                "'%s' is ambiguous. ('%s' all match)" % \
                                (key, "', '".join(matches)))
        else:
            raise errors.BadColumnNameError("The column '%s' doesn't exist! " \
                                "(Valid column names: '%s')" % \
                                (key, "', '".join(sorted(self.keys()))))

sa.engine.RowProxy.__getitem__ = fancy_getitem
    

def before_cursor_execute(conn, cursor, statement, parameters, \
                            context, executemany):
    """An event to be executed before execution of SQL queries.

        See SQLAlchemy for details about event triggers.
    """
    # Step back 7 levels through the call stack to find
    # the function that called 'execute'
    msg = str(statement)
    if executemany and len(parameters) > 1:
        msg += "\n    Executing %d statements" % len(parameters)
    elif parameters:
        msg += "\n    Params: %s" % str(parameters)
    utils.print_debug(msg, "queries", stepsback=7)


def on_commit(conn):
    """An event to be executed when a transaction is committed.

        See SQLAlchemy for details about event triggers.
    """
    utils.print_debug("Committing database transaction.", 'database', \
                        stepsback=7)


def on_rollback(conn):
    """An event to be executed when a transaction is rolled back.
        
        See SQLAlchemy for details about event triggers.
    """
    utils.print_debug("Rolling back database transaction.", 'database', \
                        stepsback=7)
        

def on_begin(conn):
    """An event to be executed when a transaction is opened.
        
        See SQLAlchemy for details about event triggers.
    """
    utils.print_debug("Opening database transaction.", 'database', \
                        stepsback=7)


def on_sqlite_connect(dbapi_conn, conn_rec):
    """An even to be execute when sqlite connections
        are established. This turns on foreign key support.

        See SQLAlchemy for details about activating SQLite's
        foreign key support:
        http://docs.sqlalchemy.org/en/rel_0_7/dialects/sqlite.html#foreign-key-support
    
        Inputs:
            dbapi_conn: A newly connected raw DB-API connection 
                (not a SQLAlchemy 'Connection' wrapper).
            conn_rec: The '_ConnectionRecord' that persistently 
                manages the connection.

        Outputs:
            None
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Cache of database engines
__engines = {}

def get_engine(url=None):
    """Given a DB URL string return the corresponding DB engine.
        Create the Engine object if necessary. If the engine 
        already exists return it rather than creating a new one.

        Input:
            url: A DB URL string.

        Output:
            engine: The corresponding DB engine.
    """
    global __engines
    if url is None:
        url = config.dburl
    if url not in __engines:
        # Create the database engine
        engine = sa.create_engine(url)
        if engine.name == 'sqlite':
            sa.event.listen(engine, "connect", on_sqlite_connect)
        sa.event.listen(engine, "before_cursor_execute", \
                            before_cursor_execute)
        if config.debug.is_on('database'):
            sa.event.listen(engine, "commit", on_commit)
            sa.event.listen(engine, "rollback", on_rollback)
            sa.event.listen(engine, "begin", on_begin)
        __engines[url] = engine
    return __engines[url]


class Database(object):
    def __init__(self):
        """Set up a Database object using SQLAlchemy.
        """
        self.engine = get_engine()
        if not self.is_created():
            raise errors.DatabaseError("The database (%s) does not appear " \
                                    "to have any tables. Be sure to run " \
                                    "'create_tables.py' before attempting " \
                                    "to connect to the database." % \
                                            self.engine.url.database)

        # The database description (metadata)
        self.metadata = schema.metadata
        self.tables = self.metadata.tables

    def get_table(self, tablename):
        return self.tables[tablename]

    def __getitem__(self, key):
        return self.get_table(key)

    def __getattr__(self, key):
        return self.get_table(key)

    def is_created(self):
        """Return True if the database appears to be setup
            (i.e. it has tables).

            Inputs:
                None

            Output:
                is_setup: True if the database is set up, False otherwise.
        """
        with self.transaction() as conn:
            table_names = self.engine.table_names(connection=conn)
        return bool(table_names)

    def transaction(self, *args, **kwargs):
        """Return a context manager delivering a 'Connection'
            with a 'Transaction' established. This is done by
            calling the 'begin' method of 'self.engine'.

            See http://docs.sqlalchemy.org/en/rel_0_7/core/connections.html
                        #sqlalchemy.engine.base.Engine.begin

            Inputs:
                Arguments are passed directly to 'self.engine.begin(...)'

            Output:
                context: The context manager returned by 
                    'self.engine.begin(...)'
        """
        return self.engine.begin(*args, **kwargs)

    @staticmethod
    def select(*args, **kwargs):
        """A staticmethod for returning a select object.

            Inputs:
                ** All arguments are directly passed to 
                    'sqlalchemy.sql.select'.

            Outputs:
                select: The select object returned by \
                    'sqlalchemy.sql.select'.
        """      
        return sa.sql.select(*args, **kwargs)

