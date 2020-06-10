from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import torch
import os

app = Flask(__name__)
app.config.from_object('config')

# db
db = SQLAlchemy(app)
db_session = db.session

# gpu
os.environ['CUDA_VISIBLE_DEVICES'] = app.config['GPU']
device = torch.device('cuda:{}'.format(app.config['GPU'])) if torch.cuda.is_available() else torch.device('cpu')

from app import views
