from app import app

app.run(
    host='0.0.0.0',
    port=5066,
    debug=True,
    threaded=True,  # 开启 flask 多线程，不然无法顾及辅助函数
)
