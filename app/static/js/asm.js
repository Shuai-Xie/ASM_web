function update(data) {
    $('#progress_bar').attr('aria-valuenow', data['progress']).css('width', data['progress'] + '%');
    $('#progress_val').text(data['progress'] + '%');
    $('#cur_idx').text(data['cur_idx']);
    $('#total_num').text(data['total_num']);
    $('#sl_num').text(data['sl_num']);
    $('#al_num').text(data['al_num']);
    if (data['sl_img_src'].length > 0)
        $('#sl_img').attr('src', data['sl_img_src']).css('width', '100%');
    if (data['al_img_src'].length > 0)
        $('#al_img').attr('src', data['al_img_src']).css('width', '100%');
}

function auto_label(dataset) {
    if (dataset === 'None') { // cus we add '' around jinja variable
        alert('You mush choose a Dataset first!')
    }
    else {
        console.log('start asm..');
        let update_progress = setInterval(function () {
            $.ajax({
                type: "post",
                url: "progress",
                async: true,
                success: function (data) {
                    update(data);
                }
            })
        }, 1000);
        let model = $('#asm_model_picker option:selected').text();
        let asm_params = {
            'model': model,
            'dataset': dataset
        };
        console.log(asm_params);
        $.ajax({
            type: "post",
            url: "auto_label",
            data: asm_params,
            async: true,
            success: function (data) {
                clearInterval(update_progress);
                update(data);
                $('#progress_bar').attr("class", "progress-bar progress-bar-success active");
                $('#progress_val').text('done!');
            }
        });
    }
}

function clear_auto(dataset) {
    if (dataset === 'None') { // cus we add '' around jinja variable
        alert('You mush choose a Dataset first!')
    }
    else {
        console.log('clear auto label..');
        $.ajax({
            type: "post",
            url: "clear_auto",
            data: {
                'dataset': dataset
            },
            async: true,
            success: function (data) {
                // asm.abort();
                update(data);
                $('#progress_bar').attr("class", "progress-bar progress-bar-info progress-bar-striped active");
                $('#sl_img').attr('src', '../static/imgs/machine.png').css('width', '200px');
                $('#al_img').attr('src', '../static/imgs/human.png').css('width', '200px');
            }
        });
    }
}