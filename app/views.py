from app import app, device
from app.db import *
from flask import render_template, jsonify, session, redirect, request

from utils.dataset_utils import cvt_echart_dict
from utils.app_utils import map_docker2host, hit_dict_tmp, hit_result_dict_tmp
from utils.box_utils import cvt_box_to_4floatpts, cvt_2pts_xywh
from utils.model_utils import load_model
from utils.plt_utils import plt_bbox

from PIL import Image
from datetime import datetime

import os
import numpy as np
import random

datasets_dir = os.path.join(os.path.dirname(__file__), '..', 'datasets')
model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')

# project is a dict with dataset info
project_list = None
choose_dataset_idx = None  # idx


@app.route('/')
def index():
    # do this when start the web
    return render_template('index.html')


@app.route('/datasets')  # all datasets
@app.route('/datasets/<int:idx>', methods=['GET', 'POST'])  # dataset detail
def datasets(idx=None):
    global project_list
    if idx is None:
        project_list = query_all_datasets()
        session['project_list'] = project_list
        return render_template(
            'datasets.html',
            project_list=session.get('project_list')
        )
    else:
        return jsonify(cvt_echart_dict(project_list[idx - 1]))


@app.route('/choose/<int:idx>', methods=['GET', 'POST'])
def choose_dataset(idx=None):
    global choose_dataset_idx
    if idx > 0:
        choose_dataset_idx = idx - 1
        session['choose_dataset'] = project_list[choose_dataset_idx]['name']
        return session['choose_dataset']


# todo: no tricks!
model_tricks = {
    "faster_rcnn_res50": ['augment', 'cosine'],
    "faster_rcnn_mobile": ['augment', 'cosine'],
}
model_list = list(model_tricks.keys())
eval_list = ['mAP', 'recall']


def get_asm_models_by_dataset(dataset_name):
    asm_model_list = sorted(list(os.listdir(os.path.join(model_dir, dataset_name))))
    return asm_model_list


@app.route('/ann_auto')
def ann_auto():
    if session.get('choose_dataset') is None:
        return redirect('/datasets')
    else:
        return render_template(
            'ann_auto.html',
            choose_dataset=session.get('choose_dataset'),
            asm_model_list=get_asm_models_by_dataset(session.get('choose_dataset'))
        )


@app.route('/train_test')
def train_test():
    return render_template(
        'train_test.html',
        choose_dataset=session.get('choose_dataset'),
        model_tricks=model_tricks,
        eval_list=eval_list,
    )


# ajax 异步请求的时候 session 是不能在后台函数没有执行完成的时候更新的
# 这就导致辅助函数不能访问到没执行完成主函数的session的
data = {
    'total_num': 0,
    'cur_idx': 0,
    'progress': 0,
    'sl_num': 0,
    'al_num': 0,
    'sl_img_src': '',
    'al_img_src': '',
}


@app.route('/progress', methods=['GET', 'POST'])
def progress():
    # data 作为全局变量，process 线程可以不断获取到
    return jsonify(data)


from asm.net.faster_rcnn import get_model
from asm.tools.asm_utils import detect_unlabel_img, compute_sl_ratio
from asm.tools.asm_train import train_model

# note: keep the useId!
hit_result_dict = hit_result_dict_tmp.copy()
sl_anns = []


# 存储当前批 SL 标注的图像
# 再通过 human label 获取其 gt_anns，再经过 update_sa_anns() 得到 sa_anns


# ASM auto label here
@app.route('/auto_label', methods=['GET', 'POST'])
def auto_label():
    """
    detect on notDone imgs, insert high conf anns to d_hits_result + update status in d_hits
    - global sl_anns 保存 SL 标注结果
    - sl/al status 直接存入数据库，得到划分开的样本
    todo: 解析得到 anns，再与 gt 比较，返回 al_ratio 筛选困难样本
    """
    model_name, dataset = request.values['model'], request.values['dataset']
    if dataset is not None:
        # get class2names of current project
        if choose_dataset_idx is not None:
            project = project_list[choose_dataset_idx]
        else:
            project = find_project_by_name(session.get('choose_dataset'), session.get('project_list'))

        num_class, class2names = project['classes'], project['cats']

        # load model and corresponding detector
        model = get_model(backbone=model_name.split('_')[-1],
                          input_size=(480, 640),  # 可存入 ckpt
                          num_classes=num_class + 1,  # +bg
                          self_pretrained=True)
        ckpt = os.path.join(model_dir, dataset, model_name, 'model_latest.pth')
        model = load_model(model, ckpt_path=ckpt)
        model = model.to(device)
        model.eval()
        print('load model done!')

        # 前端进度 图片结果 显示需要
        data['cur_idx'] = data['sl_num'] = data['al_num'] = data['progress'] = 0
        data['sl_img_src'] = data['al_img_src'] = ''

        # todo: can set a batch_num in query_d_hits() 如果 unlabel 数据量很大
        unlabeled_rows, data['total_num'] = query_d_hits(project_name=dataset, status='notDone')  # has no len
        print('total:', data['total_num'])

        # query one use, insert need
        userId = query_one_userId()
        global sl_anns
        sl_anns = []

        # ASM: detect here!
        for img_idx, row in enumerate(unlabeled_rows):
            # 从 row 解析得到 dict 标注
            hit_dict = parse_row_to_dict(row, dict_template=hit_dict_tmp)
            file_path = map_docker2host(hit_dict['data'])  # change to the real img_path on nfs
            img = Image.open(file_path)
            img_w, img_h = img.size  # cvt DT ann need

            # hit_result_dict id auto increment
            hit_result_dict['hitId'] = hit_dict['id']
            hit_result_dict['projectId'] = hit_dict['projectId']

            # ASM: generate auto label
            boxes, labels = detect_unlabel_img(model, img, device)  # x1y1x2y2, label_id
            boxes = [list(map(int, box)) for box in boxes]
            labels = [int(label) for label in labels]

            # insert row to d_hits_result
            if len(boxes) > 0:
                ## 保存 SL 结果到 Dataturks
                result = []
                for idx, (box, label) in enumerate(zip(boxes, labels)):
                    labels[idx] = label  # already -1 in infer()
                    box_info = {
                        "label": [class2names[labels[idx]]],
                        "shape": "rectangle",
                        "points": cvt_box_to_4floatpts(box, img_w, img_h),
                        "notes": "",
                        "imageWidth": img_w,
                        "imageHeight": img_h
                    }
                    result.append(box_info)

                # other columns
                hit_result_dict['result'] = str(result).replace("'", '\\"')  # 转义字符，插入 mysql 使用
                hit_result_dict['userId'] = userId
                hit_result_dict['notes'] = 'auto'  # sl 备注
                hit_result_dict['created_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                hit_result_dict['updated_timestamp'] = hit_result_dict['created_timestamp']

                # insert to DT database
                insert_sl_ann_to_db(hit_result_dict)

                # ASM: 保存模型标注结果到 sl_anns
                sl_anns.append({  # 解析的 unlabel gt_anns 也要有这种格式
                    'id': hit_dict['id'],
                    'filepath': file_path,
                    'boxes': boxes,  # x1y1x2y2
                    'labels': labels
                })
                update_status_in_db(hit_dict['id'], status='sl')
            else:
                update_status_in_db(hit_dict['id'], status='al')

            # plt bbox on img, visualize on the frontend
            web_img_src = plt_bbox(img, boxes, labels, class2names, send_web=True)

            if len(boxes) > 0:
                data['sl_img_src'] = web_img_src
                data['sl_num'] += 1
            else:
                data['al_img_src'] = web_img_src
                data['al_num'] += 1

            data['cur_idx'] = img_idx + 1
            data['progress'] = int(data['cur_idx'] / data['total_num'] * 100)

        return jsonify(data)
    else:
        return redirect('/datasets')


# clear ASM sl/al label
@app.route('/clear_auto', methods=['GET', 'POST'])
def clear_auto():
    dataset = request.values['dataset']
    if dataset is not None:
        if choose_dataset_idx is not None:
            project = project_list[choose_dataset_idx]
        else:
            project = find_project_by_name(session.get('choose_dataset'), session.get('project_list'))

        clear_auto_label(project_id=project['id'])
        print('clear all auto label data on', dataset)
        global sl_anns
        sl_anns = []

    # reset asm status
    data = {
        'total_num': 0,
        'cur_idx': 0,
        'progress': 0,
        'sl_num': 0,
        'al_num': 0,
        'sl_img_src': '',
        'al_img_src': '',
    }
    return jsonify(data)


# ASM train here
@app.route('/start_train', methods=['GET', 'POST'])
def start_train():
    model_name, dataset = request.values['model'], request.values['dataset']
    ticks, evals = request.values['tricks'].split(','), request.values['evals'].split(',')

    K = 100  # todo: judge by user

    if dataset is not None:
        # get class2names of current project
        if choose_dataset_idx is not None:
            project = project_list[choose_dataset_idx]
        else:
            project = find_project_by_name(session.get('choose_dataset'), session.get('project_list'))

        num_class, class2names = project['classes'], project['cats']
        names2class = {cat: idx for idx, cat in enumerate(class2names)}

        ## 1. prepare asm train/test anns

        # 从数据库查询 3 种不同 status 标注
        gt_sl_anns = get_gt_anns_from_sql(dataset, names2class, status='sl')
        gt_al_anns = get_gt_anns_from_sql(dataset, names2class, status='al')
        label_anns = get_gt_anns_from_sql(dataset, names2class, status='done')

        # compute al ratio with sl_anns and gt_sl_anns
        # 按图像 id 排序，保证对应
        global sl_anns
        sl_anns = list(sorted(sl_anns, key=lambda t: t['id']))
        gt_sl_anns = list(sorted(gt_sl_anns, key=lambda t: t['id']))
        # 如果 sl 人工没有标注，那么 gt_sl_anns = sl_anns，sl_ratio 全=1

        sl_ratios = [
            compute_sl_ratio(sl_ann, gt_ann) for sl_ann, gt_ann in zip(sl_anns, gt_sl_anns)
        ]
        # print(sl_ratios)

        # 判断要从 sl_anns 中选出的 sl_ratio 较低的样本数量
        topK = min(K - len(gt_al_anns), len(gt_sl_anns))
        top_idxs = np.argsort(sl_ratios)[:topK]  # sl 最少的样本
        weak_sl_anns = [sl_anns[i] for i in top_idxs]

        rndK_label_anns = random.sample(label_anns, min(K, len(label_anns)))

        # build train/test anns from hard anns
        hard_anns = gt_al_anns + weak_sl_anns
        random.shuffle(hard_anns)
        split = len(hard_anns) // 3
        hard_anns_eval = hard_anns[:split]
        hard_anns_train = hard_anns[split:]

        asm_train_anns = rndK_label_anns + hard_anns_train
        asm_eval_anns = hard_anns_eval

        ## 2. build model and train
        model = get_model(backbone=model_name.split('_')[-1],
                          input_size=(480, 640),  # 可存入 ckpt
                          num_classes=num_class + 1,  # +bg
                          self_pretrained=True)
        model_save_dir = os.path.join(model_dir, dataset, model_name)

        train_model(asm_train_anns, asm_eval_anns, model, device, model_save_dir, batch_size=1)

    return 'OK'
