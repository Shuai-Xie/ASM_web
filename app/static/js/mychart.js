function choose_dataset(url) {
    $.ajax({
        type: "post",
        url: url,
        async: true,
        success: function (dt_name) {
            $('#dt').text(dt_name);
            $('#choose').css('display', 'block');
            show_dataset_detail(url.replace('choose', 'datasets'))
        }
    });
}

function show_dataset_detail(url) {
    $.ajax({
        type: "post",
        url: url,
        async: true,
        success: function (data) {
            load_chart(data)
        }
    });
}

let myChart = null;

function load_chart(data) {
    $('#chart').css('height', data['classes'] * 28 + 'px');

    // init myChart div
    myChart = echarts.init(document.getElementById('chart'));
    myChart.showLoading();
    myChart.resize(); // if div or window change

    let cigar_array = data['children'];
    // sort the array, large -> small
    cigar_array.sort(function (first, second) {
        return first['value'] - second['value'];
    });

    let cigar_data_ordered = {};
    cigar_data_ordered['cats'] = cigar_array.map(function (item) {
        return item['name'];
    });
    cigar_data_ordered['nums'] = cigar_array.map(function (item) {
        return item['value'];
    });

    // vis cigar bar max_length
    let max_num = cigar_data_ordered['nums'][cigar_data_ordered['nums'].length - 1]; // last one
    cigar_array.reverse(); // small -> large, vis for tree order
    data['children'] = cigar_array;

    myChart.hideLoading();
    myChart.setOption(option = {
        title: {
            top: 5,
            left: 'center',
            text: data['name'] + ' Dataset',
            subtext: 'classes: ' + data['classes'] + ', instances: ' + data['instances'],
        },
        tooltip: {
            trigger: 'item',
            triggerOn: 'mousemove'
        },
        legend: {
            top: 55,
            left: 'center',  // 'center' 居中, 'x' 左对齐
            // orient: 'vertical',
            data: [
                '类别层次树',
                '数量统计图',
            ],
            icon: 'circle',
        },
        grid: [ // stats 子图位置
            { // cigar
                top: 120,
                // bottom: '1%',
                left: '60%',
                right: '10%',
                // containLabel: true
            },
        ],

        xAxis: [
            {
                type: 'value',
                name: 'amount',
                max: max_num,
            },
        ],

        yAxis: [
            {
                type: 'category',
                name: '',
                data: cigar_data_ordered['cats'],
            },
        ],

        series: [
            {
                name: '类别层次树',
                type: 'tree',
                itemStyle: {
                    color: ['#d9534f'],
                    borderColor: ['#d43f3a'],
                },
                data: [data],
                // tree 位置
                top: 100,
                bottom: '1%',
                left: '10%',
                right: '60%',
                symbolSize: 7,
                label: {
                    normal: {
                        position: 'left',
                        verticalAlign: 'bottom',  // 'middle',
                        align: 'right',
                        fontSize: 12,
                        // 显示 value 值
                        // formatter: function (params) {
                        //     if (params.value > 0)
                        //         return params.name + ': ' + params.value;
                        //     else
                        //         return params.name
                        // }
                    }
                },
                leaves: {
                    label: {
                        normal: {
                            position: 'right',
                            verticalAlign: 'middle',
                            align: 'left',
                        },
                    }
                },
                expandAndCollapse: true,
                animationDuration: 550,
                animationDurationUpdate: 750
            },
            {
                name: '数量统计图',
                type: 'bar',
                itemStyle: {
                    color: ['#5BC49F'],
                    borderColor: ['#5BC49F'],
                },
                // barWidth: 5,
                data: cigar_data_ordered['nums'],
                label: {
                    normal: {
                        position: 'right',
                        fontSize: 12, // 右侧数字大小
                        show: true,
                    }
                },
            },
        ]
    });
}

$(window).resize(function () {
    if (myChart !== null) {
        myChart.resize();
    }
});
