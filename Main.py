#!/usr/bin/env python3
from create_monitor import create_monitor

# lista de checks a crear (ejemplo)
checks = [
    {"name":"fgm-ping-global","mtype":"ping","host":"home.cern","period":"10"},
    {"name":"fgm-web-us","mtype":"web","host":"home.cern","period":"15", "region":"United States"},
    {"name":"fgm-tcp-443","mtype":"tcp","host":"home.cern","port":"443","period":"10"}
]

for c in checks:
    res = create_monitor(name=c["name"], mtype=c["mtype"], host=c["host"],
                         period=c.get("period","10"),
                         port=c.get("port",""),
                         keyword=c.get("keyword",""))
    print(res)
