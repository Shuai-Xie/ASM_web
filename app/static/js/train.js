// change tricks according to chosen model
$('#model_picker').on('changed.bs.select', function () {
    let options = model_tricks[$("#model_picker").val()]; // get tricks of select model
    $("#trick_picker option").remove(); // remove original
    options.map(function (op) {
        $('#trick_picker').append("<option value='" + op + "'>" + op + "</option>");
    });
    $('#trick_picker').selectpicker('refresh');
});

function start_train(dataset) {
    if (dataset === 'None') { // cus we add '' around jinja variable
        alert('You mush choose a Dataset first!')
    }
    else {
        console.log('start training..');
        let model = $('#model_picker option:selected').text();
        let tricks = [];
        let evals = [];
        $('#trick_picker option:selected').map(function () {
            tricks.push($(this).text());
        });
        $('#eval_picker option:selected').map(function () {
            evals.push($(this).text());
        });
        let model_params = {
            'model': model,
            'dataset': dataset,
            'tricks': tricks.toString(), // cvt list to str
            'evals': evals.toString()
        };
        console.log(model_params);
        $.ajax({
            type: "post",
            url: "start_train",
            data: model_params,
            async: true,
            success: function (data) {
                console.log(data)
            }
        });
    }
}

function stop_train() {
    console.log('stop training..')
}
