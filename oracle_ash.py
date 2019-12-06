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
    """ % 10)

    cursor.rowfactory = make_dict_factory(cursor)
    for row in cursor:

        if (row['WAIT_CLASS']):
            print ("""oracle_ash_waits,host=%s,db=%s,session_id=%d,sql_opname=%s,
            session_state=%s,
            wait_class=%s,
            event=%s,
            sql_id=%s

            session_id=%s,
            session_serial=%s,
            session_type=\"%s\",
            event=\"%s\",
            wait_class=\"%s\",
            wait_time=%d,
            session_state=\"%s\",
            time_waited=%d,
            blocking_session_status=\"%s\",
            blocking_session=%d,
            blocking_session_serial=%s
            %d000000000
            """ %
            (
                oracle_host,

                oracle_service,
                row['SESSION_ID'],
                row['SQL_OPNAME'],
                row['SESSION_STATE'],
                # InfluxDB does not like spaces in tag names, so lets replace them with _
                row['WAIT_CLASS'].replace(' ', '_'),
                row['EVENT'].replace(' ', '_'),
                row['SQL_ID'],

                row['SESSION_ID'],
                row['SESSION_SERIAL#'],
                row['SESSION_TYPE'],
                row['EVENT'],
                row['WAIT_CLASS'],
                row['WAIT_TIME'],
                row['SESSION_STATE'],
                row['TIME_WAITED'],
                row['BLOCKING_SESSION_STATUS'],
                0,
                #row['BLOCKING_SESSION'],
                row['BLOCKING_SESSION_SERIAL#'],
                int(time.mktime(row['SAMPLE_TIME'].timetuple()))
            ))
        continue
        print ("oracle_ash,host=%s,db=%s,session_id=%d,sql_opname=%s,session_state=%s,wait_class=%s,event=%s,sql_id=%s session_id=%s,session_serial=%s," %
        (
            oracle_host,
            oracle_service,
            row['SESSION_ID'],
            row['SQL_OPNAME'],
            row['SESSION_STATE'],
            row['WAIT_CLASS'].replace(' ', '_'),
            row['EVENT'],
            row['SQL_ID'],

            #session_id=%s,session_serial=%s,session_type=\"%s\",event=\"%s\",wait_class=\"%s\",wait_time=%s,session_state=\"%s\",time_waited=%s,
            #blocking_session_status=\"%s\",blocking_session=%d,blocking_session_serial=%s, %s000000000
            row['SESSION_ID'],
            row['SESSION_SERIAL#'],
            #row['SESSION_TYPE'],
            #row['EVENT'],
            #row['WAIT_CLASS'],
            #row['WAIT_TIME'],
            #row['SESSION_STATE'],
            #row['TIME_WAITED'],
            #row['BLOCKING_SESSION_STATUS'],
            #row['BLOCKING_SESSION'],
        #    row['BLOCKING_SESSION_SERIAL#'],
            #int(time.mktime(row['SAMPLE_TIME'].timetuple()))
        ))
