import os
import torch
from torch.utils.tensorboard import SummaryWriter
from asm.dataset.detection_dataset import Detection_Dataset_anns
from asm.dataset.transforms import get_transform
from asm.tools.utils import collate_fn
from asm.tools.engine import train_one_epoch, evaluate
from utils.model_utils import load_model, save_model
from datetime import datetime
import numpy as np
import re


def get_curtime():
    current_time = datetime.now().strftime('%b%d_%H-%M-%S')
    return current_time


def lasso_shift(records):
    mean = np.mean(records)
    return np.mean([abs(x - mean) for x in records])


def save_clean_best_model(best_epoch, model_save_dir):
    for model in os.listdir(model_save_dir):
        epoch = int(re.search(r'model_(\d).pth', model).group(1))
        if epoch != best_epoch:
            # 删除其他 model
            os.remove(os.path.join(model_save_dir, model))
        else:
            # 更换 best model 为 latest.pth
            os.rename(os.path.join(model_save_dir, model),
                      os.path.join(model_save_dir, 'model_latest.pth'))


def train_model(train_anns, eval_anns,
                model, device, model_save_dir,
                ckpt='model_latest.pth',
                num_epoches=10,
                batch_size=4,
                ap='ap_50', ap_thre=0.5,
                ap_range=3, ap_shift_thre=0.001):
    # optimizer
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.SGD(params, lr=0.005, momentum=0.9, weight_decay=0.0005)
    # load pretrain best model
    ckpt_path = os.path.join(model_save_dir, ckpt)
    model, optimizer, start_epoch = load_model(model, ckpt_path, optimizer)
    lr_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epoches)

    # train/eval dataset
    dataset = Detection_Dataset_anns(train_anns, get_transform(True))
    dataloader = torch.utils.data.DataLoader(dataset,
                                             batch_size=batch_size,
                                             shuffle=True,
                                             pin_memory=True,
                                             num_workers=4,
                                             collate_fn=collate_fn)
    dataset_eval = Detection_Dataset_anns(eval_anns, get_transform(False))
    dataloader_eval = torch.utils.data.DataLoader(dataset_eval,
                                                  batch_size=1,
                                                  shuffle=False,
                                                  pin_memory=True,
                                                  num_workers=4,
                                                  collate_fn=collate_fn)
    # 检测参数
    writer = SummaryWriter(log_dir='runs/{}'.format(get_curtime()))
    ap_records = {'ap_50': [], 'ap_75': [], 'ap_shift': []}

    for epoch in range(start_epoch, num_epoches):  # epoch 要从0开始，内部有 warm_up
        # train
        train_one_epoch(model, optimizer, dataloader, device, epoch, print_freq=10,
                        writer=writer, begin_step=epoch * len(dataloader))
        # store & update lr
        writer.add_scalar('Train/lr', optimizer.param_groups[0]["lr"], global_step=epoch)
        lr_scheduler.step()

        # eval after each train
        evals = evaluate(model, dataloader_eval, device, writer, epoch)

        # states
        ap_records['ap_50'].append(evals['ap_50'])
        ap_records['ap_75'].append(evals['ap_75'])
        if len(ap_records[ap]) >= ap_range:
            ap_shift = lasso_shift(ap_records[ap][-ap_range:])
        else:
            ap_shift = 0
        ap_records['ap_shift'].append(ap_shift)

        writer.add_scalar('Accuracy/AP_shift', ap_shift, global_step=epoch)

        if evals[ap] > ap_thre:
            ckpt_path = os.path.join(model_save_dir, 'model_{}.pth'.format(epoch))
            save_model(ckpt_path, model, epoch, optimizer)

            if 0 < ap_shift < ap_shift_thre:  # break and save ap records
                best_idx_in_range = ap_records[ap].index(max(ap_records[ap][-ap_range:]))
                best_epoch = epoch - ap_range + 1 + best_idx_in_range

                print('best epoch:', best_epoch)
                save_clean_best_model(best_epoch, model_save_dir)
