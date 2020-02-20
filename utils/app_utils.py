from datetime import datetime
from config import HOST_UPLOADS

# 参考模板
hit_dict_tmp = {
    'id': 3970500,  # int(11) unsigned
    'projectId': '2c9180826e63806a016e6382709f0002',  # varchar(36)
    'data': '/uploads/2c9180826e63806a016e6382709f0002/fddc7385-a43b-4ffe-bdb5-65768b6ff1a6___img2_2007_000175.jpg',
    # text
    'extras': None,  # text
    'status': 'notDone',  # varchar(50)
    'evaluation': 'NONE',  # varchar(50)
    'isGoldenHIT': 0,  # tinyint(1)
    'goldenHITResultId': 0,  # int(11) unsigned
    'notes': None,  # text
    'created_timestamp': datetime(2019, 11, 13, 13, 10, 36),  # timestamp, sql result 直接是 datetime
    'updated_timestamp': datetime(2019, 11, 13, 13, 10, 36),  # timestamp
    'isURL': 1  # tinyint(4)
}

hit_result_dict_tmp = {
    'id': 1091878,  # int(11) unsigned
    'hitId': 3970499,  # int(11) unsigned
    'projectId': '2c9180826e63806a016e6382709f0002',  # varchar(36)
    'result': [  # text
        # this is one box!
        {
            "label": ["person"],
            "shape": "rectangle",
            "points": [
                [0.026, 0.05333333333333334],
                [0.95, 0.05333333333333334],
                [0.95, 0.9813333333333333],
                [0.026, 0.9813333333333333]
            ],
            "notes": "",
            "imageWidth": 500,
            "imageHeight": 375
        }
    ],
    'userId': 'tThFQBQbx1Ah6qVeEZgFEvstJ2lf',  # varchar(36)
    'timeTakenToLabelInSec': 1,  # int(11) unsigned todo: a spotlight in frontend
    'notes': None,  # text
    'created_timestamp': datetime(2019, 11, 13, 13, 10, 36),  # timestamp, sql result 直接是 datetime
    'updated_timestamp': datetime(2019, 11, 13, 13, 10, 36),  # timestamp
}


def map_docker2host(img_path):
    return img_path.replace('/uploads', HOST_UPLOADS)
