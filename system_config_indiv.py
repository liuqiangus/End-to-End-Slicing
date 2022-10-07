CONF_TRAF = {"traffic": 1.0}


CONF_CN = [{
    "IMSI":"222010000000001",
    "ADDR":"192.168.17.11"
}]

CONF_TN = {
    'slice0':{
                '192.168.17.11':{
                    'bandwidth':100,
                    'static_path':0
                }
            },
}


# details see https://mosaic5g.io/apidocs/flexran/#api-SliceConfiguration-ApplySliceConfiguration
# XXX attention, static RB allocation is inclusive!!! XXX
# allowable DL scheduler: "round_robin_dl", "proportional_fair_wbcqi_dl", "maximum_throughput_wbcqi_dl"
# allowable UL scheduler: "round_robin_dl" XXX ONLY XXX
DL_SCHER = ["round_robin_dl", "proportional_fair_wbcqi_dl", "maximum_throughput_wbcqi_dl"]
UL_SCHER = ["round_robin_ul"]  # _ul !!!! XXX
CONF_AN = {
    "dl": {
        "algorithm": "Static",
        "slices": [
            {
                "id": 0, # 
                "maxmcs":0,
                'scheduler':"round_robin_dl",
                "static": {
                    "posLow": 0,
                    "posHigh": 18
                }
            },
        ]
    },
    "ul": {
        "algorithm": "Static",
        "slices": [
            {
                "id": 0,
                "maxmcs":0,
                'scheduler':"round_robin_ul",
                "static": {
                    "posLow": 7,
                    "posHigh": 48
                }
            },
        ]
    }
}

CONF_UES = {
  "0": 
    {
      "imsi": "222010000000001",
      "sliceid": "0",
      "addr": "12.1.1.2",
      "server": "192.168.17.11", # edge server
      'rnti': -1,
      'retx_dl':0,
      'retx_ul':0,
      'reliability_ul':[1],
      'reliability_dl':[1],
      'total_dl':0,
      'total_ul':0,
      'load_dl':[0],
      'load_ul':[0],
      'mcs_dl':[0],
      'mcs_ul':[0],
      'workload':[0], # server workload
      'last_time':0   # last update time   
    },
}

