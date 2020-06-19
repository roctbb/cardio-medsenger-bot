import datetime
import time
from threading import Thread
from flask import Flask, request, render_template
import json
import requests
import os
from config import *
import threading
import datetime
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
db_string = "postgres://{}:{}@{}:{}/{}".format(DB_LOGIN, DB_PASSWORD, DB_HOST, DB_PORT, DB_DATABASE)
app.config['SQLALCHEMY_DATABASE_URI'] = db_string
db = SQLAlchemy(app)


class Contract(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    active = db.Column(db.Boolean, default=True)
    last_push = db.Column(db.BigInteger, default=0)
    mode = db.Column(db.Integer, default=0)


class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    big1 = db.Column(db.Boolean, default=False)
    big2 = db.Column(db.Boolean, default=False)
    big3 = db.Column(db.Boolean, default=False)
    big4 = db.Column(db.Boolean, default=False)
    big5 = db.Column(db.Boolean, default=False)
    big6 = db.Column(db.Boolean, default=False)
    big7 = db.Column(db.Boolean, default=False)
    small1 = db.Column(db.Boolean, default=False)
    small2 = db.Column(db.Boolean, default=False)
    small3 = db.Column(db.Boolean, default=False)
    small4 = db.Column(db.Boolean, default=False)
    small5 = db.Column(db.Boolean, default=False)
    small6 = db.Column(db.Boolean, default=False)
    submitted = db.Column(db.BigInteger, default=0)
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=False)
    contract = db.relationship('Contract', backref=db.backref('answers', lazy=True))


try:
    db.create_all()
except:
    print('cant create structure')


def get_delta(mode):
    day = 24 * 60 * 60
    if mode == 0:
        return day - 1
    if mode == 1:
        return 3 * day - 1
    return 7 * day - 1


def delayed(delay, f, args):
    timer = threading.Timer(delay, f, args=args)
    timer.start()


def check_digit(number):
    try:
        int(number)
        return True
    except:
        return False


def gts():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


@app.route('/init', methods=['POST'])
def init():
    data = request.json

    if data['api_key'] != APP_KEY:
        return 'invalid key'

    try:
        contract_id = int(data['contract_id'])
        query = Contract.query.filter_by(id=contract_id)
        if query.count() != 0:
            contract = query.first()
            contract.active = True

            print("{}: Reactivate contract {}".format(gts(), contract.id))
        else:
            contract = Contract(id=contract_id)
            db.session.add(contract)

            print("{}: Add contract {}".format(gts(), contract.id))

        db.session.commit()


    except Exception as e:
        print(e)
        return "error"

    print('sending ok')
    return 'ok'


@app.route('/remove', methods=['POST'])
def remove():
    data = request.json

    if data['api_key'] != APP_KEY:
        print('invalid key')
        return 'invalid key'

    try:
        contract_id = str(data['contract_id'])
        query = Contract.query.filter_by(id=contract_id)

        if query.count() != 0:
            contract = query.first()
            contract.active = False
            db.session.commit()

            print("{}: Deactivate contract {}".format(gts(), contract.id))
        else:
            print('contract not found')

    except Exception as e:
        print(e)
        return "error"

    return 'ok'


@app.route('/settings', methods=['GET'])
def settings():
    key = request.args.get('api_key', '')

    if key != APP_KEY:
        return "<strong>Некорректный ключ доступа.</strong> Свяжитесь с технической поддержкой."

    try:
        contract_id = int(request.args.get('contract_id'))
        query = Contract.query.filter_by(id=contract_id)
        if query.count() != 0:
            contract = query.first()
        else:
            return "<strong>Ошибка. Контракт не найден.</strong> Попробуйте отключить и снова подключить интеллектуальный агент к каналу консультирвоания.  Если это не сработает, свяжитесь с технической поддержкой."

    except Exception as e:
        print(e)
        return "error"

    return render_template('settings.html', contract=contract)


@app.route('/settings', methods=['POST'])
def setting_save():
    key = request.args.get('api_key', '')

    if key != APP_KEY:
        return "<strong>Некорректный ключ доступа.</strong> Свяжитесь с технической поддержкой."

    try:
        contract_id = int(request.args.get('contract_id'))
        query = Contract.query.filter_by(id=contract_id)
        if query.count() != 0:
            contract = query.first()
            contract.mode = int(request.form.get('mode', 0))
            db.session.commit()
        else:
            return "<strong>Ошибка. Контракт не найден.</strong> Попробуйте отключить и снова подключить интеллектуальный агент к каналу консультирвоания.  Если это не сработает, свяжитесь с технической поддержкой."

    except Exception as e:
        print(e)
        return "error"

    return """
        <strong>Спасибо, окно можно закрыть</strong><script>window.parent.postMessage('close-modal-success','*');</script>
        """


@app.route('/', methods=['GET'])
def index():
    return 'waiting for the thunder!'


def send(contract_id):
    data = {
        "contract_id": contract_id,
        "api_key": APP_KEY,
        "message": {
            "text": "Пожалуйста, заполните анкету по симптоматике сердечной недостаточности.",
            "action_link": "frame",
            "action_name": "Заполнить анкету",
            "action_onetime": True,
            "only_doctor": False,
            "only_patient": True,
            "action_deadline": int(time.time()) + 24 * 59 * 60
        }
    }
    try:
        requests.post(MAIN_HOST + '/api/agents/message', json=data)
    except Exception as e:
        print('connection error', e)


def send_warning(contract_id, a):
    data1 = {
        "contract_id": contract_id,
        "api_key": APP_KEY,
        "message": {
            "text": "Мы направили уведомление о симптомах вашему лечащему врачу, он свяжется с вами в ближайшее время.",
            "is_urgent": True,
            "only_patient": True,
        }
    }

    data2 = {
        "contract_id": contract_id,
        "api_key": APP_KEY,
        "message": {
            "text": "У пациента наблюдаются вероятные симптомы сердечной недостаточности ({}).".format(' / '.join(a)),
            "is_urgent": True,
            "only_doctor": True,
            "need_answer": True
        }
    }
    try:
        print('sending')
        result1 = requests.post(MAIN_HOST + '/api/agents/message', json=data1)
        result1 = requests.post(MAIN_HOST + '/api/agents/message', json=data2)
    except Exception as e:
        print('connection error', e)


def sender():
    while True:
        contracts = Contract.query.all()
        for contract in contracts:
            if time.time() - contract.last_push > get_delta(contract.mode):
                send(contract.id)
                print("{}: Sending form to {}".format(gts(), contract.id))
                contract.last_push = int(time.time())

        db.session.commit()
        time.sleep(60)


@app.route('/message', methods=['POST'])
def save_message():
    data = request.json
    key = data['api_key']

    if key != APP_KEY:
        return "<strong>Некорректный ключ доступа.</strong> Свяжитесь с технической поддержкой."

    return "ok"


@app.route('/frame', methods=['GET'])
def action():
    key = request.args.get('api_key', '')

    if key != APP_KEY:
        return "<strong>Некорректный ключ доступа.</strong> Свяжитесь с технической поддержкой."

    try:
        contract_id = int(request.args.get('contract_id', -1))
        query = Contract.query.filter_by(id=contract_id)

        if query.count() == 0:
            return "<strong>Запрашиваемый канал консультирования не найден.</strong> Попробуйте отключить и заного подключить интеллектуального агента. Если это не сработает, свяжитесь с технической поддержкой."
        return render_template('measurement.html')

    except:
        return "error"


@app.route('/frame', methods=['POST'])
def action_save():
    key = request.args.get('api_key', '')
    if key != APP_KEY:
        return "<strong>Некорректный ключ доступа.</strong> Свяжитесь с технической поддержкой."

    try:
        contract_id = int(request.args.get('contract_id', -1))
        query = Contract.query.filter_by(id=contract_id)
        if query.count() == 0:
            return "<strong>Запрашиваемый канал консультирования не найден.</strong> Попробуйте отключить и заного подключить интеллектуального агента. Если это не сработает, свяжитесь с технической поддержкой."
    except:
        return "error"

    answer = Answer()
    answer.contract_id = contract_id

    big_warnings = []
    small_warnings = []

    if request.form.get('big1', False) == 'warning':
        answer.big1 = True
        big_warnings.append('одышка при ранее привычной физической нагрузке')
    if request.form.get('big2', False) == 'warning':
        answer.big2 = True
        big_warnings.append('жалобы на одышку в положение лежа')
    if request.form.get('big3', False) == 'warning':
        answer.big3 = True
        big_warnings.append('приступы ночной одышки')
    if request.form.get('big4', False) == 'warning':
        answer.big4 = True
        big_warnings.append('физическая нагрузка дается тяжелее, чем ранее')
    if request.form.get('big5', False) == 'warning':
        answer.big5 = True
        big_warnings.append('слабость, повышенная утомляемость, необходимость в более продолжительном отдыхе')
    if request.form.get('big6', False) == 'warning':
        answer.big6 = True
        big_warnings.append('отечность голеней, увеличение в объеме лодыжек')
    if request.form.get('big7', False) == 'warning':
        answer.big7 = True
        big_warnings.append('увеличилась ли окружность талии')

    if request.form.get('small1', False) == 'warning':
        answer.small1 = True
        small_warnings.append('ночной кашель')
    if request.form.get('small2', False) == 'warning':
        answer.small2 = True
        small_warnings.append('увеличение веса на 2 кг')
    if request.form.get('small3', False) == 'warning':
        answer.small3 = True
        small_warnings.append('увеличение веса на 1 кг')
    if request.form.get('small4', False) == 'warning':
        answer.small4 = True
        small_warnings.append('подавленность или апатия')
    if request.form.get('small5', False) == 'warning':
        answer.small5 = True
        small_warnings.append('беспокоит сердцебиение')
    if request.form.get('small6', False) == 'warning':
        answer.small6 = True
        small_warnings.append('не получается задержать дыхание на 30 секунд')

    answer.submitted = int(time.time())

    db.session.add(answer)
    db.session.commit()

    if len(big_warnings) > 0 or len(small_warnings) > 1:
        warnings = big_warnings + small_warnings
        delayed(1, send_warning, [contract_id, warnings])

    print("{}: Form from {}".format(gts(), contract_id))

    return """
    <strong>Спасибо, окно можно закрыть</strong><script>window.parent.postMessage('close-modal-success','*');</script>
    """


t = Thread(target=sender)
t.start()

app.run(port=PORT, host=HOST)
