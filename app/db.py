from app import db_session
from utils.dataset_utils import create_dataset_from_sql_res, split_and_save_coco_dataset
from utils.io_utils import dump_json, load_json
import os
import json
from pprint import pprint


def parse_row_to_dict(row, dict_template):
    """
    :param row: query result: d_hits, d_hits_result
    :param dict_template: hit_dict, hit_result_dict
    :return:
    """
    dict_row = dict_template.copy()
    for idx, (key, _) in enumerate(dict_row.items()):  # items 结果相对字典还是有序的
        dict_row[key] = row[idx]
    return dict_row


def query_d_hits(project_name, status=None):
    """
    :param project_name: voc, Retail Project Dataset
    :param status: 'done', 'notDone'
    :return:
    """
    sql = "select * from d_hits " \
          "where projectId in (select id from d_projects where name='{}')".format(project_name)
    if status:
        sql += "and status='{}'".format(status)
    res = db_session.execute(sql)
    # 总数
    sql = sql.replace('*', 'count(*)')
    total_num = db_session.execute(sql)
    # 以循环的方式解析结果, yield, 一输出就没了，数据库用 generator 很合理
    # for row in res:
    #     print(row)
    #     pprint(parse_row_to_dict(row, dict_template=hit_dict_tmp))
    return res, total_num.next()[0]


def query_d_hits_result(project_name):
    sql = "select * from d_hits_result " \
          "where projectId in (select id from d_projects where name='{}')".format(project_name)
    res = db_session.execute(sql)
    return res


def query_one_userId():
    sql = "select id from d_users limit 0,1"
    res = db_session.execute(sql)
    return res.next()[0]


def clear_auto_label(project_id):
    # find auto-label rows
    # sql = "select hitId from d_hits_result where projectId='{}' and notes='auto'".format(project_id)

    # find sl/al lines
    sql = "select id from d_hits where projectId='{}' and status in ('sl', 'al')".format(project_id)
    hitIds = db_session.execute(sql)

    for hid in hitIds:
        hid = hid[0]
        # update d_hits status
        sql = "update d_hits set status='notDone' where id={}".format(hid)
        db_session.execute(sql)
        # clear d_hit_results
        sql = "delete from d_hits_result where hitId={}".format(hid)
        db_session.execute(sql)
        db_session.commit()


def parse_projects(row):
    taskRules = json.loads(row[3])  # str->dict, 中文
    cats = taskRules['tags'].replace(' ', '').split(',')
    return {
        'id': row[0],
        'name': row[1],
        'taskType': row[2],
        'classes': len(cats),
        'cats': cats,
    }


def find_project_by_name(name, project_list):
    for project in project_list:
        if project['name'] == name:
            return project


data_root = os.path.join(os.path.abspath(os.path.dirname(__file__)), '../datasets')


# todo: update dataset each night, 定时器
def query_one_dataset(project_name, top_k=None):
    dataset_dir = os.path.join(data_root, project_name)
    os.makedirs(dataset_dir, exist_ok=True)
    prefix = '{}_'.format(top_k) if top_k else ''
    project_cfg_path = os.path.join(dataset_dir, '{}{}_cfg.json'.format(prefix, project_name))

    if os.path.exists(project_cfg_path):  # has dataset_file
        print('read {} from json!'.format(project_name))
        project = load_json(project_cfg_path)
    else:
        print('read {} from mysql!'.format(project_name))
        project = create_dataset_from_sql(project_name, top_k)
        dump_json(project, out_path=os.path.join(dataset_dir, '{}{}_cfg.json'.format(prefix, project_name)))

    return project


def create_dataset_from_sql(project_name, top_k=None):
    dataset_dir = os.path.join(data_root, project_name)

    # read project cfgs
    sql = f"select `id`, `name`, `taskType`, `taskRules` from d_projects where `name`='{project_name}'"
    res = db_session.execute(sql)
    project = res.next()  # get name
    project = parse_projects(project)

    # read data from mysql
    sql = f"select d_hits.id as img_id, d_hits.data as path, d_hits_result.result as anns from d_hits, d_hits_result " \
          "where d_hits.projectId='{}' and d_hits.id=d_hits_result.hitId and d_hits.status='done'".format(
        project['id'])
    res = db_session.execute(sql)

    # create dataset from sql query results
    dataset = create_dataset_from_sql_res(res, project['cats'])

    # split and save dataset to json
    filter_cats, filter_cats_num, train_num, val_num, test_num = split_and_save_coco_dataset(dataset, dataset_dir,
                                                                                             top_k)
    # update project
    project['cats_num'] = filter_cats_num
    # project['cats'] = filted_cats  # 保持创建项目时所有类
    # project['classes'] = len(filted_cats)
    project['train'] = train_num
    project['valid'] = val_num
    project['test'] = test_num

    return project


def query_all_datasets(orgID='2c9180836e6f27e2016e6f327ede0001'):
    sql = f"select `name` from d_projects where orgId='{orgID}'"  # Shuai datasets
    project_names = db_session.execute(sql)
    project_list = []
    for idx, p_name in enumerate(project_names):
        project = query_one_dataset(p_name[0])
        project['idx'] = idx + 1  # add idx
        project_list.append(project)
    return project_list


def query_d_hits_result_by_id(hit_id):
    sql = "select result from d_hits_result where hitId={}".format(hit_id)
    res = db_session.execute(sql)
    res = res.next()
    if len(res) > 0:
        return res[0]
    else:
        return None


def query_projectId_by_name(project_name):
    sql = "select id from d_projects where name='{}'".format(project_name)
    res = db_session.execute(sql)
    res = res.next()  # 返回 <class 'sqlalchemy.engine.result.RowProxy'>
    if len(res) > 0:
        return res[0]
    else:
        return None


def query_results_by_status(project_name, status):
    projectId = query_projectId_by_name(project_name)
    sql = "select d_hits.id as hitId, d_hits.data as filepath, d_hits_result.result as result " \
          "from d_hits, d_hits_result " \
          "where d_hits_result.hitId=d_hits.id " \
          "and d_hits.id in (select id from d_hits where projectId='{}' and status='{}')".format(projectId, status)
    hit_results = db_session.execute(sql)
    return hit_results


from utils.box_utils import cvt_4floatpts2box
from utils.app_utils import map_docker2host


def parse_result_box_labels(result, names2class):
    """
    @param result: Dataturks ann result
    @param names2class: label -> label idx
    """
    result = json.loads(result)  # str -> [dict,..]
    boxes, labels = [], []
    for ann in result:
        boxes.append(cvt_4floatpts2box(ann['points'], ann['imageWidth'], ann['imageHeight']))
        labels.append(names2class[ann['label'][0]])
    return boxes, labels


def get_gt_anns_from_sql(project_name, names2class, status):
    # parse hit_results to gt_anns
    gt_anns = []
    hit_results = query_results_by_status(project_name, status)

    for row in hit_results:
        hitId, filepath, result = row[0], row[1], row[2]
        if len(result) > 0:
            boxes, labels = parse_result_box_labels(result, names2class)
            ann = {
                'id': hitId,
                'filepath': map_docker2host(filepath),
                'boxes': boxes,
                'labels': labels
            }
            gt_anns.append(ann)
    return gt_anns


def insert_sl_ann_to_db(hit_result_dict):
    # 1.insert row to d_hits_result
    # value 单行, values 多行，但是速度 values 更快
    # id auto increment
    sql = "insert into d_hits_result " \
          "(`hitId`, `projectId`, `result`, `userId`, `timeTakenToLabelInSec`, `notes`, `created_timestamp`, `updated_timestamp`) " \
          "values ({},'{}','{}','{}',{},'{}','{}','{}')".format(hit_result_dict['hitId'],  # int
                                                                hit_result_dict['projectId'],  # str
                                                                hit_result_dict['result'],  # str
                                                                hit_result_dict['userId'],  # str
                                                                hit_result_dict['timeTakenToLabelInSec'],
                                                                # int
                                                                hit_result_dict['notes'],  # str
                                                                hit_result_dict['created_timestamp'],  # str
                                                                hit_result_dict['updated_timestamp'])
    db_session.execute(sql)
    db_session.commit()


def update_status_in_db(hit_id, status):
    sql = "update d_hits set status='{}' where id={}".format(status, hit_id)
    db_session.execute(sql)
    db_session.commit()


if __name__ == '__main__':
    # projects = query_all_datasets()
    # pprint(projects)
    # project = query_one_dataset('VOC')
    # pprint(project)

    # query_d_hits_result_by_id(hit_id=1)
    # print(query_projectId_by_name('VOC'))

    # query_results_by_status('VOC', status='done')

    class2names = [  # 0-19
        'aeroplane', 'bicycle', 'bird', 'boat', 'bottle',
        'bus', 'car', 'cat', 'chair', 'cow',
        'diningtable', 'dog', 'horse', 'motorbike', 'person',
        'pottedplant', 'sheep', 'sofa', 'train', 'tvmonitor'
    ]
    names2class = {
        name: idx for idx, name in enumerate(class2names)
    }
    get_gt_anns_from_sql('VOC', names2class, status='done')
