# ASM_web

Flask Web demo with [ASM_core](https://github.com/Shuai-Xie/ASM_core).

## Features

ASM steps with Dataturks.

**1. auto_label()**

- update `d_hits.status` by ASM detection results.

```py
# update image status in Dataturks d_hits table
status = 'sl' if len(sl_boxes) > 0 else 'al'

# store all the sl anns, to compute AL ratio in start_train() 
global sl_anns = []
```

**2. Human annotation in Dataturks Hits Done, filter by SL/AL status.**

**3. start_train()**

- read `gt SL/AL anns` from mysql
- compute AL ratio by `sl_anns` and `gt_sl_anns`
- choose topK and build `asm_train_anns`
- train on the new dataset

```py
# 从数据库查询 3 种不同 status 标注
gt_sl_anns = get_gt_anns_from_sql(dataset, names2class, status='sl')
gt_al_anns = get_gt_anns_from_sql(dataset, names2class, status='al')
label_anns = get_gt_anns_from_sql(dataset, names2class, status='done') 
```

## Architecture

<img src="https://edrawcloudpubliccn.oss-cn-shenzhen.aliyuncs.com/viewer/self/1573941/share/2020-2-20/1582194045/main.svg"></img>
