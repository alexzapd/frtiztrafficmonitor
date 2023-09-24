import time
import threading

from fritzconnection.core.exceptions import *
from influxdb import InfluxDBClient
from fritzconnection import FritzConnection
from datetime import datetime, timedelta
def connFritz():
    retry=True
    while retry:
        try:
            fc = FritzConnection(address="", user="", password="", use_cache=True)
            retry=False
        except Exception:
            retry=True
            print("unable to connect to Fritz,retrying in 10s")
            time.sleep(10)
    return fc

def connDB():
    retry=True
    global client
    while retry:
        try:
            client = InfluxDBClient('IP', 8086, 'DB name', 'password', 'measurement')
            client.ping()
            retry=False
        except Exception:
            retry=True
            print("unable to connect to DB,retrying in 10s")
            time.sleep(10)
    return client

def trafficMonitor(fc ,client):
    while True:
        service = "WANCommonInterfaceConfig1"
        action = "GetCommonLinkProperties"
        result=""
        try:
            result = fc.call_action(service, action)
        except Exception:
            print("Connection to FritzBox lost, retrying in 5s")
            time.sleep(5)
            fc=connFritz()
            print("Reconnected to Fritz")
            result = fc.call_action(service, action)
        keys = ['NewX_AVM-DE_DownstreamCurrentUtilization', 'NewX_AVM-DE_UpstreamCurrentUtilization']
        downstream = [int(x) for x in result[keys[0]].split(",")]
        upstream = [int(x) for x in result[keys[1]].split(",")]
        i = 0
        now=datetime.utcnow()
        for d, u in zip(downstream, upstream):
            d *= 8
            u *= 8
            result = now - timedelta(seconds=i * 5)
            timeq = result.strftime("%Y-%m-%dT%H:%M:%SZ")
            data_points = [
                {
                    "measurement": "bandwidthUsage",
                    "tags": {
                        "type": "bits_per_sec",
                    },
                    "time": timeq,
                    "fields": {
                        "downstream": d,
                        "upstream": u,
                    }
                }
            ]
            i += 1
            try:
                client.write_points(data_points)
            except Exception:
                print("Connection to DB lost, retrying in 5s")
                time.sleep(5)
                client=connDB()
                print("Reconnected to DB")
                client.write_points(data_points)
        time.sleep(95)


if __name__ == '__main__':
    fc=connFritz()
    client=connDB()
    trafficMonitor(fc,client)
