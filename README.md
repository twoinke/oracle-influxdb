
# Visualizing Oracle performance data with InfluxDB und Grafana

With Active Session History (ASH), Oracle provides an invaluable feature to historically analyze performance. Implemented as a ring buffer, data retention is limited.
But often, one needs to be able to analyze the database load retrospectively for a longer period of time.
Modern monitoring/visualization solutions like the ELK stack (Elasticsearch, Logstash, Kibana) or the TICK-Stack (Telegraf, InfluxDB, Chronograf, Kapacitor) come to mind. One solution using the ELK stack is described by Robin Moffat at https://www.elastic.co/de/blog/visualising-oracle-performance-data-with-the-elastic-stack.
This tutorial will show how to use the TICK stack, or more precisely its storage component InfluxDB and its data collector Telegraf in conjunction with Grafana, a combination which has recently become popular as the TIG-Stack.


## Prerequsites

 Covering all aspects of InfluxDB is way outside the scope of this article, we will cover just what we need as we go. If you are totally new to InfluxDB or want to dig deeper, please refer to the very good online documentation https://docs.influxdata.com/influxdb/v1.7/
You should however have a rough idea of the key concepts https://docs.influxdata.com/influxdb/v1.7/concepts/key_concepts/.
If you have an SQL database background, the crosswalk https://docs.influxdata.com/influxdb/v1.7/concepts/crosswalk/ might be helpful, too

Also, this tutorial will make use of Docker in order to setup the test/demo environment, so make sure you have Docker installed and you have sufficient permissions to create containers.

## Disclaimer

The Oracle Active Session History is licensed as part of the "Oracle Diagnostics Pack". Make sure your Oracle license allows usage of this feature.

## Setting up the test environment

Let us begin by going ahead and installing influxdb and grafana. To keep things simple, we just use the official docker images and use the following commands to spin up our test environment.
```bash
docker run -d -p 127.0.0.1:8086:8086 --name influxdb influxdb:1.7.9
docker run -d -p 127.0.0.1:3000:3000 --link influxdb --name grafana grafana/grafana:6.5.1
```


## Getting the ASH data into InfluxDB

We are ready now for the next step - gathering ASH data and feeding them into InfluxDB.  
As a so called "time series database", InfluxDB manages "points" (in time), identified by timestamp, measurement name (like "cpu_load") and "tags".

### Enter telegraf

Time to look at the "T" in "TICK" stack, Telegraf, which is the TICK stack's data collector. Telegraf supports a variety of output-plugins (one of them InfluxDB), and also lots and lots of input-plugins. Among them a couple of plugins to collect performance data from various databases - except Oracle. Even a simple query against Oracle is not possible. Looks like we need to roll our own.

Luckily, Telegraf has a plugin called "exec" which executes arbitrary commands and captures the output, which can then be fed into InfluxDB.
With that being said, we use a small python script to query the ASH and transform the data into a format suitable for InfluxDB.
While the ELK solution described by Robin Moffat just uses logstash to periodically execute "select * from v$active_session_history" and just stuff everything into Elasticsearch, we need to be a little more careful with InfluxDB at this point. We have to specify the columns we want to use as tags.

```python
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import cx_Oracle
import time

measurement_name = 'oracle_ash'
interval = 60

oracle_host     ='localhost'
oracle_port     =1521
oracle_service  ='orcl'
oracle_user     ='metrics'
oracle_passwd   ='metrics'

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
            tags['sql_id']     = row['SQL_ID']

        if (row['BLOCKING_SESSION']):
            tags['blocking_session'] = row['BLOCKING_SESSION']

        tags_str    = ",".join(["%s=%s" % (k, tags[k]) for k in tags])
        fields_str  = ",".join(["%s=\"%s\"" % (f.lower(), row[f]) for f in row if row[f] is not None])
        influx_time = "%d000000000" % int(time.mktime(row['SAMPLE_TIME'].timetuple()))
        print ("%s,%s %s %s" % ( measurement_name, tags_str, fields_str, influx_time ))
```

Next thing we need is an Oracle-User, which the script will use to access ASH:
```
sqlplus connect / as sysdba

SQL> create user metrics identified by metrics;

User created.

SQL> grant connect to metrics;

Grant succeeded.

SQL> grant select on v_$active_session_history to metrics;
```


When executed, the script's output should now look like this:

```
$ ./oracle_ash.py
oracle_ash,host=localhost,db=orcl,session_state=WAITING,wait_class=Other,event=os_thread_creation sample_id="272133",sample_time="2019-12-06 13:44:03.569000",session_id="4",session_serial#="27611",session_type="BACKGROUND",event="os thread creation",wait_class="Other",wait_time="0",session_state="WAITING",time_waited="5691",blocking_session_status="UNKNOWN" 1575636243000000000
oracle_ash,host=localhost,db=orcl,session_state=WAITING,wait_class=Other,event=oracle_thread_bootstrap sample_id="272133",sample_time="2019-12-06 13:44:03.569000",session_id="34",session_serial#="6929",session_type="BACKGROUND",event="oracle thread bootstrap",wait_class="Other",wait_time="0",session_state="WAITING",time_waited="19896",blocking_session_status="UNKNOWN" 1575636243000000000
oracle_ash,host=localhost,db=orcl,session_state=ON_CPU,wait_class=Other,event=oracle_thread_bootstrap sample_id="272133",sample_time="2019-12-06 13:44:03.569000",session_id="84",session_serial#="44923",session_type="BACKGROUND",wait_time="644",session_state="ON CPU",time_waited="0",blocking_session_status="NOT IN WAIT" 1575636243000000000
oracle_ash,host=localhost,db=orcl,session_state=WAITING,wait_class=Other,event=ADR_block_file_read sample_id="272109",sample_time="2019-12-06 13:43:39.567000",session_id="84",session_serial#="232",session_type="BACKGROUND",event="ADR block file read",wait_class="Other",wait_time="0",session_state="WAITING",time_waited="10042",blocking_session_status="UNKNOWN" 1575636219000000000
oracle_ash,host=localhost,db=orcl,session_state=ON_CPU,wait_class=Other,event=ADR_block_file_read sample_id="272078",sample_time="2019-12-06 13:43:08.566000",session_id="4",session_serial#="27611",session_type="BACKGROUND",wait_time="999821",session_state="ON CPU",time_waited="0",blocking_session_status="NOT IN WAIT" 1575636188000000000
```

Now we need to configure Telegraf, which will call our script periodically and feed the data into InfluxDB. This minimal example config will use a database called "telegraf", which Telegraf will create automatically if it does not exist.

```ini
# Configuration for telegraf agent
[agent]
  ## Default data collection interval for all inputs
  interval = "60s"

# Configuration for sending metrics to InfluxDB
[[outputs.influxdb]]
  urls = ["http://127.0.0.1:8086"]
  database = "telegraf"

# Read metrics from one or more commands that can output to stdout
[[inputs.exec]]
  ## Commands array
  commands = [ "./oracle_ash.py" ]
  data_format = "influx"
```

We are ready now to start Telegraf.
```bash
telegraf --config telegraf.conf --debug
```
The --debug switch enables more verbose logging, so we will see right away if anything is wrong.

If everything went ok, InfluxDB is now being fed with ASH data. Let's check!
There should be a database called "telegraf" containing a measurement with the name "oracle_ash" now.

```
$ docker exec -ti influxdb influx -database telegraf
Connected to http://localhost:8086 version 1.7.9
InfluxDB shell version: 1.7.9
> show measurements
name: measurements
name
----
oracle_ash
> select count(session_id) from oracle_ash
name: oracle_ash
time count
---- -----
0    3758
```

## Grafana
Now with the data part done, we will take care of the visualization part. Grafana is available at http://localhost:3000/ and after logging on using the default credentials admin/admin, we need to supply a new password. Now we are ready to go.

Next thing we need is to set up a data source in Grafana, like shown.

![setup grafana data source 1](img/grafana_add_data_source_1.png)
![setup grafana data source 2](img/grafana_add_data_source_2.png)

We are ready now to create our first Graph. Grafana already has a fresh dashboard with a new, unconfigured panel. Click on "add Query", and we can enter our query using the query editor, like shown in the screenshot.

![Grafana Query erstellen](img/grafana_graph_wait_events.PNG)



The demo dashboard shows wait events, session status(waiting/running), number of blocking sessions and sessions blocked by other sessions and by which wait event.

![Grafana Demo Dashboard](img/grafana_demo_dashboard.png)


## Conclusion
Collecting Oracle performance data in InfluxDB makes it easy to visualize what happens on your database, even for historical data. This is just a simple example, ASH contains much more useful information. But also feeding your application's performance data into InfluxDB is where the fun really begins as it enables you to correlate them to Oracle's and troubleshoot performance with only a few clicks.
