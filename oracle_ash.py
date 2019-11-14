#!/usr/bin/python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import os
import sys
import cx_Oracle
import argparse
import re
import time
from datetime import datetime
from influxdb import InfluxDBClient
import dateutil.parser

oracle_host='localhost'
oracle_port=1521
oracle_service='xepdb1'
oracle_user='metrics'
oracle_passwd='metrics'

#influx_host='localhost'
#influx_port=8086
#influx_dbname='metrics'

def make_dict_factory(cursor):
        column_names = [d[0] for d in cursor.description]
        def create_row(*args):
                return dict(zip(column_names, args))
        return create_row

def ashstats(oracle_conn, influx_conn):
    #lastrunfile = "/tmp/oracle_metrics_%s_lastrun.tmp" % ("ashstats")
    #lastrun = self.read_lastrun(lastrunfile)
    lastrun = datetime.fromtimestamp(0)

    try:
            result = influx_conn.query("select last(\"session_id\"), \"time\" from \"oracle_ash\" where \"host\"='%s' and \"db\"='%s'" % (self.host, self.sid))
            for r in result:
                    lastrun = dateutil.parser.parse(r[0]['time'])

    except:
            lastrun = datetime.fromtimestamp(0)

    cursor = self.connection.cursor()
    cursor.rowfactory = make_dict_factory(cursor)
    cursor.execute("""
    select
    sample_id,
    sample_time,
    session_id,
    session_serial#,
    session_type,
    sql_id,
    sql_child_number,
    sql_opcode,
    sql_opname,
    sql_plan_hash_value,
    sql_plan_line_id,
    sql_plan_operation,
    sql_plan_options,
    event,
    wait_class,
    wait_time,
    session_state,
    time_waited,
    blocking_session_status,
    blocking_session,
    blocking_session_serial#,
    current_obj#,
    current_file#,
    current_block#,
    current_row#,
    program,
    module,
    machine,
    pga_allocated,
    temp_space_allocated
    from v$active_session_history
    where sample_time > :lastrun
    """, {'lastrun': lastrun})


    for row in cursor:
            tags = {}
            #fields = []

            if row['PGA_ALLOCATED'] is None:
                    row['PGA_ALLOCATED']=0

            if row['TEMP_SPACE_ALLOCATED'] is None:
                    row['TEMP_SPACE_ALLOCATED']=0

            if row['BLOCKING_SESSION'] is None:
                    row['BLOCKING_SESSION'] =0

            if row['BLOCKING_SESSION_SERIAL#'] is None:
                    row['BLOCKING_SESSION_SERIAL#']=0

            if row['SQL_OPNAME'] is None:
                    row['SQL_OPNAME']='UNKNOWN'
            else:
               row['SQL_OPNAME'] = row['SQL_OPNAME'].replace(' ', '_')

            if row['SESSION_STATE'] is None:
                    row['SESSION_STATE']='UNKNOWN'
            else:
               row['SESSION_STATE'] = row['SESSION_STATE'].replace(' ', '_')

            if row['EVENT'] is None:
                    row['EVENT']='NONE'
            else:
               row['EVENT'] = row['EVENT'].replace(' ', '_')

            if row['WAIT_CLASS'] is None:
                    row['WAIT_CLASS']='NONE'
            else:
               row['WAIT_CLASS'] = row['WAIT_CLASS'].replace(' ', '_')

            print ("oracle_ash,host=%s,db=%s,session_id=%d,machine=%s,sql_opname=%s,session_state=%s,wait_class=%s,event=%s,sql_id=%s session_id=%s,session_serial=%s,session_type=\"%s\",sql_id=\"%s\",sql_child_number=%s,sql_opname=\"%s\",sql_plan_hash_value=%s,sql_plan_line_id=\"%s\",sql_plan_operation=\"%s\",sql_plan_options=\"%s\",event=\"%s\",wait_class=\"%s\",wait_time=%s,session_state=\"%s\",time_waited=%s,blocking_session_status=\"%s\",blocking_session=%d,blocking_session_serial=%s,current_obj=%s,current_file=%s,current_block=%s,current_row=%s,program=\"%s\",module=\"%s\",machine=\"%s\",pga_allocated=%d,temp_space_allocated=%d %d000000000" % (
                    self.host,
                    self.sid,
                    row['SESSION_ID'],
                    row['MACHINE'],
                    row['SQL_OPNAME'],
                    row['SESSION_STATE'],
                    row['WAIT_CLASS'],
                    row['EVENT'],
                    row['SQL_ID'],

                    row['SESSION_ID'],
                    row['SESSION_SERIAL#'],
                    row['SESSION_TYPE'],
                    row['SQL_ID'],
                    row['SQL_CHILD_NUMBER'],
                    row['SQL_OPNAME'],
                    row['SQL_PLAN_HASH_VALUE'],
                    row['SQL_PLAN_LINE_ID'],
                    row['SQL_PLAN_OPERATION'],
                    row['SQL_PLAN_OPTIONS'],
                    row['EVENT'],
                    row['WAIT_CLASS'],
                    row['WAIT_TIME'],
                    row['SESSION_STATE'],
                    row['TIME_WAITED'],
                    row['BLOCKING_SESSION_STATUS'],
                    row['BLOCKING_SESSION'],
                    row['BLOCKING_SESSION_SERIAL#'],
                    row['CURRENT_OBJ#'],
                    row['CURRENT_FILE#'],
                    row['CURRENT_BLOCK#'],
                    row['CURRENT_ROW#'],
                    row['PROGRAM'],
                    row['MODULE'],
                    row['MACHINE'],
                    row['PGA_ALLOCATED'],
                    row['TEMP_SPACE_ALLOCATED'],
                    time.mktime( row['SAMPLE_TIME'].timetuple())
            ))


if __name__ == "__main__":

    dsn = cx_Oracle.makedsn(
            host = oracle_host,
            port = oracle_port,
            service_name = oracle_service
    )

    oracle_conn = cx_Oracle.connect( oracle_user , oracle_passwd , dsn )
#    influx_conn = InfluxDBClient(influx_host, influx_port, '', '', influx_dbname)

    print(oracle_conn)

    cursor = oracle_conn.cursor()
    cursor.execute("""
    select
    --sample_id,
    --sample_time,
    --session_id,
    --session_serial#,
    --session_type,
    sql_id,
    sql_child_number,
    --sql_opcode,
    --sql_opname,
    --sql_plan_hash_value,
    --sql_plan_line_id,
    --sql_plan_operation,
    --sql_plan_options,
    event,
    wait_class,
    wait_time,
    --session_state,
    --time_waited,
    --blocking_session_status,
    --blocking_session,
    --blocking_session_serial#,
    --current_obj#,
    --current_file#,
    --current_block#,
    --current_row#,
    program,
    module,
    machine
    --pga_allocated,
    --temp_space_allocated
    --from v$active_session_history
    from v$session
    --where sample_time > current_timestamp - interval '5' minute
    """, {})

    cursor.rowfactory = make_dict_factory(cursor)
    for row in cursor:
        print ("oracle_ash,host=%s,db=%s,session_id=%d,machine=%s,sql_opname=%s,session_state=%s,wait_class=%s,event=%s,sql_id=%s session_id=%s,session_serial=%s,session_type=\"%s\",sql_id=\"%s\",sql_child_number=%s,sql_opname=\"%s\",sql_plan_hash_value=%s,sql_plan_line_id=\"%s\",sql_plan_operation=\"%s\",sql_plan_options=\"%s\",event=\"%s\",wait_class=\"%s\",wait_time=%s,session_state=\"%s\",time_waited=%s,blocking_session_status=\"%s\",blocking_session=%d,blocking_session_serial=%s,current_obj=%s,current_file=%s,current_block=%s,current_row=%s,program=\"%s\",module=\"%s\",machine=\"%s\",pga_allocated=%d,temp_space_allocated=%d %d000000000" % (

