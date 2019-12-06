#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import cx_Oracle
import time

oracle_host='localhost'
oracle_port=12521
oracle_service='orcl'
oracle_user='metrics'
oracle_passwd='metrics'


def make_dict_factory(cursor):
    column_names = [d[0] for d in cursor.description]
    def create_row(*args):
        return dict(zip(column_names, args))
    return create_row

if __name__ == "__main__":

    dsn = cx_Oracle.makedsn(
        host = oracle_host,
        port = oracle_port,
        service_name = oracle_service
    )

    oracle_conn = cx_Oracle.connect( oracle_user , oracle_passwd , dsn )

    cursor = oracle_conn.cursor()
    cursor.execute("""
    select
    sample_id,
    sample_time,
    session_id,
    session_serial#,
    session_type,
    sql_opname,
    sql_id,
    event,
    wait_class,
    wait_time,
    session_state,
    time_waited,
    blocking_session_status,
    blocking_session,
    blocking_session_serial#
    from v$active_session_history
    where sample_time > current_timestamp - interval '%d' second
    """ % 60)

    tags = {}
    tags['host'] = oracle_host
    tags['db']   = oracle_service

    cursor.rowfactory = make_dict_factory(cursor)
    for row in cursor:

        tags['session_state'] = row['SESSION_STATE'].replace(' ', '_')
        if (row['WAIT_CLASS']):
            tags['wait_class'] = row['WAIT_CLASS'].replace(' ', '_')
            tags['event']      = row['EVENT'].replace(' ', '_')

        if (row['SQL_OPNAME']):
            tags['sql_opname'] = row['SQL_OPNAME'].replace(' ', '_')

        if (row['SQL_ID']):
            tags['sql_id'] = row['SQL_ID']

    if (row['BLOCKING_SESSION'] > 0):
        tags['blocking_session'] = row['BLOCKING_SESSION']


        print ("oracle_ash_waits,%s %s %d000000000" %
            (
                ",".join(["%s=%s" % (k, tags[k]) for k in tags]),
                ",".join(["%s=\"%s\"" % (f.lower(), row[f]) for f in row if row[f] is not None]),

                int(time.mktime(row['SAMPLE_TIME'].timetuple()))
            ))
