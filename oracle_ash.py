#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import cx_Oracle
import time
measurement_name = 'oracle_ash'
interval = 60
oracle_host='localhost'
oracle_port=12521
oracle_service='orcl'
oracle_user='metrics'
oracle_passwd='metrics'

def dictionary_factory(cursor):
    names = [d[0] for d in cursor.description]
    def create_row(*args):
        return dict(zip(names, args))
    return create_row

if __name__ == "__main__":

    oracle_conn = cx_Oracle.connect( oracle_user , oracle_passwd , "%s:%s/%s" % (oracle_host, oracle_port, oracle_service) )

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
    """ % interval)

    tags = {
        'host': oracle_host,
        'db': oracle_service
    }

    cursor.rowfactory = dictionary_factory(cursor)
    for row in cursor:

        # InfluxDB does not like spaces in tag names, so we replace them with _
        tags['session_state'] = row['SESSION_STATE'].replace(' ', '_')

        # set wait_class and wait_event only if session is really waiting
        if (row['WAIT_CLASS']):
            tags['wait_class'] = row['WAIT_CLASS'].replace(' ', '_')
            tags['event']      = row['EVENT'].replace(' ', '_')

        # set sql operation name only if session is a sql operation
        if (row['SQL_OPNAME']):
            tags['sql_opname'] = row['SQL_OPNAME'].replace(' ', '_')

        # set sql id if present
        if (row['SQL_ID']):
            tags['sql_id'] = row['SQL_ID']

        if (row['BLOCKING_SESSION']):
            tags['blocking_session'] = row['BLOCKING_SESSION']

        tags_str    = ",".join(["%s=%s" % (k, tags[k]) for k in tags])
        fields_str  = ",".join(["%s=\"%s\"" % (f.lower(), row[f]) for f in row if row[f] is not None])
        influx_time = "%d000000000" % int(time.mktime(row['SAMPLE_TIME'].timetuple()))
        print ("%s,%s %s %s" % ( measurement_name, tags_str, fields_str, influx_time ))
