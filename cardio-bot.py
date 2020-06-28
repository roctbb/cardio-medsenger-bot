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
    scenario = db.Column(db.Integer, default=0)

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
            contract.last_push = int(time.time())

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
            contract.scenario = int(request.form.get('scenario', 0))
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
            "text": "Пожалуйста, заполните анкету кардиомониторинга.",
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

def save_report(contract_id, report):
    data = {
        "contract_id": contract_id,
        "api_key": APP_KEY,
        "values": report
    }
    print(data)
    try:
        requests.post(MAIN_HOST + '/api/agents/records/add', json=data)
    except Exception as e:
        print('connection error', e)

def get_category(contract_id, category_name, time_from=None, time_to=None, limit=None, offset=None):

    data = {
        "contract_id": contract_id,
        "api_key": APP_KEY,
        "category_name": category_name,
    }
    
    if limit:
        data['limit'] = limit
    if offset:
        data['offset'] = offset
    if time_from:
        data['from'] = time_from
    if time_to:
        data['to'] = time_to

    try:
        result = requests.post(MAIN_HOST + '/api/agents/records/get', json=data)
        return result.json()
    except Exception as e:
        print('connection error', e)
        return []

def send_warning(contract_id, a, scenario):
    data1 = {
        "contract_id": contract_id,
        "api_key": APP_KEY,
        "message": {
            "text": "Мы направили уведомление о симптомах вашему лечащему врачу, он свяжется с вами в ближайшее время.",
            "is_urgent": True,
            "only_patient": True,
        }
    }

    diagnosis = "сердечной недостаточности"
    if scenario == 1:
        diagnosis = "стенокардии"
    elif scenario == 2:
        diagnosis = "фибрилляции предсердий"

    data2 = {
        "contract_id": contract_id,
        "api_key": APP_KEY,
        "message": {
            "text": "У пациента наблюдаются симптомы {} ({}).".format(scenario, ' / '.join(a)),
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

        return render_template('measurement{}.html'.format(query.first().scenario))

    except:
        return "error"

def check_params(contract, data):
    report = []
    
    contract_id = contract.id

    if contract.scenario == 0:
        big_warnings = []
        small_warnings = []

        warning_names = ['одышка при ранее привычной физической нагрузке', 'жалобы на одышку в положение лежа',
                         'приступы ночной одышки',
                         'физическая нагрузка дается тяжелее, чем ранее',
                         'слабость, повышенная утомляемость, необходимость в более продолжительном отдыхе',
                         'отечность голеней, увеличение в объеме лодыжек', 'ночной кашель', 'подавленность или апатия',
                         'сердцебиение',
                         'не получается задержать дыхание на 30 секунд']
        criteria = [0 for i in range(10)]

        for i in range(1, 7):
            criteria[i - 1] = data.get('big{}'.format(i), False) == 'warning'
            if criteria[i - 1]:
                big_warnings.append(warning_names[i - 1])

        for i in range(1, 5):
            criteria[i + 5] = data.get('small{}'.format(i), False) == 'warning'
            if criteria[i + 5]:
                small_warnings.append(warning_names[i + 5])

        # control weight
        time_to = int(time.time()) - 60 * 60 * 24 * 4
        time_from = int(time.time()) - 60 * 60 * 24 * 11

        try:
            last_weight = get_category(contract_id, 'weight', limit=1)[0]
            week_weight = get_category(contract_id, 'weight', time_from=time_from, time_to=time_to)

            delta = last_weight - sum(week_weight) / len(week_weight)
            if delta >= 2:
                small_warnings.append('увеличение веса на {} кг'.format(round(delta, 1)))
            if delta <= -1:
                small_warnings.append('уменьшение веса на {} кг'.format(round(-delta, 1)))

        except Exception as e:
            print(e)

        # control waist_circumference
        try:
            last_value = get_category(contract_id, 'waist_circumference', limit=1)[0]
            week_value = get_category(contract_id, 'waist_circumference', time_from=time_from, time_to=time_to)

            delta = last_value - sum(week_value) / len(week_value)
            if delta >= 5:
                big_warnings.append('увеличение окружности талии на {} см'.format(round(delta, 1)))

        except Exception as e:
            print(e)

        # control leg_circumference
        try:
            last_value_left = get_category(contract_id, 'leg_circumference_left', limit=1)[0]
            last_value_right = get_category(contract_id, 'leg_circumference_right', limit=1)[0]
            week_values_left = get_category(contract_id, 'leg_circumference_left', time_from=time_from, time_to=time_to)
            week_values_right = get_category(contract_id, 'leg_circumference_right', time_from=time_from, time_to=time_to)

            delta_left = last_value_left - sum(week_values_left) / len(week_values_left)
            delta_right = last_value_right - sum(week_values_right) / len(week_values_right)
            if delta_left >= 3:
                big_warnings.append('увеличение обхвата левой голени на {} см'.format(round(delta_left, 1)))
            if delta_right >= 3:
                big_warnings.append('увеличение обхвата правой голени на {} см'.format(round(delta_right, 1)))

            change = abs(last_value_left - last_value_right)
            if change >= 3:
                big_warnings.append('разница между обхватом голени с разных сторон - {} см'.format(round(change, 1)))

        except Exception as e:
            print(e)

        # send report
        for i in range(10):
            report.append({
                "category_name": "heartfailure_claim_{}".format(i + 1),
                "value": int(criteria[i])
            })

        # send warning
        if len(big_warnings) > 0 or len(small_warnings) > 1:
            warnings = big_warnings + small_warnings
            delayed(1, send_warning, [contract_id, warnings, contract.scenario])

    elif contract.scenario == 1:
        criteria = int(data.get('stenocardia', 1))
        if criteria == 2:
            delayed(1, send_warning,
                    [contract_id, ["стенокардия при небольшой физической нагрузке"], contract.scenario])

        report.append({
            "category_name": "stenocardia_claim_1",
            "value": criteria
        })

    else:
        warnings = []
        criteria1 = int(data.get('fibrillation1', 1))
        if criteria1 == 2:
            warnings.append("выраженные симптомы")
        if criteria1 == 3:
            warnings.append("выраженные симптомы c нарушением нормальной жизнедеятельности")

        criteria2 = int(data.get('fibrillation2', 1))
        if criteria2 == 2:
            warnings.append("тяжелые кровотечения")

        report.append({
            "category_name": "fibrillation_claim_1",
            "value": criteria1
        })

        report.append({
            "category_name": "fibrillation_claim_2",
            "value": criteria2
        })

        if len(warnings) > 0:
            delayed(1, send_warning, [contract_id, warnings, contract.scenario])

    delayed(1, save_report, [contract_id, report])



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

    contract = query.first()

    delayed(1, check_params, (contract, request.form))

    print("{}: Form from {}".format(gts(), contract_id))

    return """
            <strong>Спасибо, окно можно закрыть</strong><script>window.parent.postMessage('close-modal-success','*');</script>
            """


t = Thread(target=sender)
t.start()

app.run(port=PORT, host=HOST)
