# oracle-influxdb
Example configuration/script/dashboard to visualize Oracle Active Session History data with InfluxDB and Grafana

Oracle Performance Daten visualisieren mit InfluxDB und Grafana


Oracle's Active Session History (ASH) ist unerlässlich, um die Performance der Datenbank auch historisch auswerten zu können. Allerdings ist die ASH als Ringpuffer ausgeführt, und damit die Vorhaltezeit der historischen Performancedaten begrenzt. Oft ist es aber gerade wichtig, das Verhalten der Datenbank rückwirkend für einen längeren Zeitraum unter die Lupe zu nehmen.

Dementsprechend müssen die Daten also anderweitig persistiert werden. Einen Ansatz können moderne Monitoring- bzw. Visualisierungs-Lösungen wie der ELK-Stack (Elasticsearch, Logstash, Kibana) und der TICK-Stack (Telegraf, InfluxDB, Chronograf, Kapacitor) bieten.
Einen Weg, wie man den ELK-Stack hierzu nutzen kann, zeigt Robin Moffatt unter https://www.elastic.co/de/blog/visualising-oracle-performance-data-with-the-elastic-stack

In diesem Beitrag wollen wir den TICK-Stack nutzen, von dem uns zunächst nur dessen Storage-Kompenente InfluxDB interessiert.

Vorab noch die obligatorische Anmerkung, dass die Active Session History Teil des "Oracle Diagnostics Pack" ist und damit entsprechend lizenzpflichtig. Es gibt aber auch die Möglichkeit, ohne die ASH ans Ziel zu kommen, dazu später mehr.

InfluxDB und Elasticsearch verfolgen verschiedene Ziele. Während Elasticsearch insbesondere als Such-Engine einsetzbar ist, ist InfluxDB eine sogenannte "Time-Series-Database", und damit eher für das Verwalten von Metriken zu bestimmten Zeitpunkten interessant. Auch die Vorhaltezeit der Daten läßt sich durch Anlegen von Retention Policies einfach konfigurieren.
Anders als eine RDBMS "denkt" InfluxDB nicht in Tabellen, Keys und Indizes, sondern in "Points", die durch Tags identifiziert werden, Felder enthalten und in sogenannten Measurements abgelegt werden. InfluxDB ist zudem schemalos.

Zunächst müssen wir uns InfluxDB und Grafana installieren. Der Einfachheit halber verwenden wir Docker und die offiziellen Docker-Images:
```bash
docker run -d -p 127.0.0.1:8086:8086 -d --name influxdb influxdb:1.7.9
docker run -d -p 3000:3000 --link influxdb --name grafana grafana/grafana:6.4.4
```
Wie bekommen wir nun die Daten aus der ASH in die InfluxDB? Der Datensammler im TICK-Stack nennt sich Telegraf, und bietet von Haus aus eine Reihe von Plugins zum Sammeln der verschiedensten Metriken einschließlich Performancedaten einiger Datenbanken wie MySQL, Postgres oder SQL Server, jedoch nicht Oracle. Auch einfach nur Queries gegen Oracle absetzen ist nicht möglich. Es gibt aber das "exec"-Plugin, mit dem sich beliebige Programme oder Skripte ausführen lassen, deren Ausgabe dann InfluxDB zugeführt wird. Diesen Weg wollen wir gehen. Zum Aufbereiten der Daten verwenden wir ein kleines Python-Script.



```python
import script_here
```


Jetzt brauchen wir noch einen Oracle-User, mit dem das Script auf die Active Session History zugreifen kann.
Oracle User anlegen:
```
SQL> create user metrics identified by metrics;

User created.

SQL> grant connect to metrics;

Grant succeeded.

SQL> grant select on v_$active_session_history to metrics;
```

```bash
apt-get install telegraf
vi telegraf.conf
service telegraf start
```

Jetzt, da InfluxDB aus der Active Session History befüllt wird, können wir mit dem Visualisierungsteil weitermachen.
Grafana ist auf http://localhost:3000 erreichbar und möchte nach Login mit admin/admin zunächst ein neues Passwort gesetzt haben.

Als nächstes benötigen wir eine Datenquelle.

![Grafana Datenquelle erstellen](img/grafana_add_data_source_1.png)
![Grafana Datenquelle erstellen](img/grafana_add_data_source_2.png)

Und jetzt endlich erstellen wir unseren ersten Graphen. Grafana hält bereits ein frisches Dashboard und ein neues, unkonfiguriertes Panel für uns bereit.
Ein Klick auf "Add Query", und wir können mit dem Query Editor eine Abfrage erstellen, wie z. B. für die Wait Events, siehe Screenshot.

![Grafana Query erstellen](img/grafana_graph_wait_events.PNG)


Aus der Oracle Active Session History können auf diese Weise eine Reihe von Performancedaten visualisiert werden. Sammelt man nun noch weitere Metriken der laufenden Applikation und Systeme ebenfalls in InfluxDB, lassen sich diese mit den Daten aus der ASH korrelieren. Das Identifizieren von Performanceproblemen wird damit zum Klacks.

