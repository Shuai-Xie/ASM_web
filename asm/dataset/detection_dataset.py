import os
import torch
from torch.utils.data.dataset import Dataset
from pycocotools.coco import COCO
from PIL import Image
from utils.box_utils import cvt_xywh_2pts


class Detection_Dataset_coco(Dataset):
    """
    pass in coco json
    """

    def __init__(self, root, coco_json, transforms=None):
        self.coco = COCO(annotation_file=os.path.join(root, coco_json))
        self.transforms = transforms
        self.imgs, self.img_anns = [], []
        for img_id, anns in self.coco.imgToAnns.items():
            self.imgs.append(self.coco.imgs[img_id]['file_name'])
            self.img_anns.append(anns)

    def __getitem__(self, idx):
        img = Image.open(self.imgs[idx])
        img_anns = self.img_anns[idx]  # [dict,..]
        boxes, labels = [], []
        for ann in img_anns:
            boxes.append(cvt_xywh_2pts(ann['bbox']))
            labels.append(ann['category_id'] + 1)  # bg=0, infer will del, so cigar_A can't show

        # convert everything into a torch.Tensor
        boxes = torch.as_tensor(boxes, dtype=torch.float32)
        labels = torch.as_tensor(labels, dtype=torch.int64)
        area = (boxes[:, 3] - boxes[:, 1]) * (boxes[:, 2] - boxes[:, 0])  # cal area by box, return vector
        iscrowd = torch.zeros((len(img_anns),), dtype=torch.int64)  # set 0

        target = {
            'image_id': torch.as_tensor([idx]),
            "boxes": boxes,  # [x0, y0, x1, y1] ~ [0,W], [0,H]
            "labels": labels,  # class label
            "area": area,  # used in COCO metric, AP_small,medium,large
            "iscrowd": iscrowd,  # if True, ignored during eval
        }

        if self.transforms is not None:
            img, target = self.transforms(img, target)

        return img, target

    def __len__(self):
        return len(self.imgs)


class Detection_Dataset_anns(Dataset):
    """
    pass in anns list
    """

    def __init__(self, anns, transforms=None):
        self.anns = anns
        self.transforms = transforms

    def __getitem__(self, idx):
        ann = self.anns[idx]
        img = Image.open(ann['filepath'])  # F.to_tensor() 会转换 rgb
        boxes, labels = ann['boxes'], ann['labels'] + 1  # bg=0, so label idx+1

        # convert everything into a torch.Tensor
        boxes = torch.as_tensor(boxes, dtype=torch.float32)
        labels = torch.as_tensor(labels, dtype=torch.int64)  # 默认整数为 int64
        area = (boxes[:, 3] - boxes[:, 1]) * (boxes[:, 2] - boxes[:, 0])  # cal area by box, return vector
        iscrowd = torch.zeros((labels.size(0),), dtype=torch.int64)  # set 0

        target = {
            'image_id': torch.as_tensor([idx]),
            # 'filepath': ann['filepath'],  # for vis
            'boxes': boxes,  # [x1, y1, x2, y2] ~ [0,W], [0,H]
            'labels': labels,  # class label
            'area': area,  # used in COCO metric, AP_small,medium,large
            'iscrowd': iscrowd,  # if True, ignored during eval
        }

        if self.transforms is not None:
            img, target = self.transforms(img, target)

        return img, target

    def __len__(self):
        return len(self.anns)
