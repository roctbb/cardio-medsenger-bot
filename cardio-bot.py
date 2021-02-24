import json
import time
from threading import Thread
from flask import Flask, request, render_template
from config import *
import threading
import datetime
from flask_sqlalchemy import SQLAlchemy
from agents_api import *

app = Flask(__name__)
db_string = "postgres://{}:{}@{}:{}/{}".format(DB_LOGIN, DB_PASSWORD, DB_HOST, DB_PORT, DB_DATABASE)
app.config['SQLALCHEMY_DATABASE_URI'] = db_string
db = SQLAlchemy(app)


class Contract(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    active = db.Column(db.Boolean, default=True)
    last_push = db.Column(db.BigInteger, default=0)
    mode = db.Column(db.Integer, default=2)
    scenario = db.Column(db.Integer, default=0)
    last_task_id = db.Column(db.Integer, nullable=True)
    last_task_push = db.Column(db.BigInteger, default=0)


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

def submit_task(contract):
    if contract.last_task_id:
        make_task(contract.id, contract.last_task_id)
    contract.last_task_id = None

def drop_task(contract):
    if contract.last_task_id:
        delete_task(contract.id, contract.last_task_id)
    contract.last_task_id = None

def init_task(contract):
    drop_task(contract)
    contract.last_task_id = add_task(contract.id, "Заполнить анкету кардиомониторинга", action_link='frame')


@app.route('/status', methods=['POST'])
def status():
    data = request.json

    if data['api_key'] != APP_KEY:
        return 'invalid key'

    contract_ids = [l[0] for l in db.session.query(Contract.id).all()]

    answer = {
        "is_tracking_data": True,
        "supported_scenarios": ['heartfailure', 'stenocardia', 'fibrillation'],
        "tracked_contracts": contract_ids
    }
    print(answer)

    return json.dumps(answer)


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
            contract.last_push = 0

            print("{}: Reactivate contract {}".format(gts(), contract.id))
        else:
            contract = Contract(id=contract_id)
            db.session.add(contract)

            print("{}: Add contract {}".format(gts(), contract.id))

        if data.get('preset', None) == 'heartfailure':
            contract.scenario = 0
        if data.get('preset', None) == 'stenocardia':
            contract.scenario = 1
        if data.get('preset', None) == 'fibrillation':
            contract.scenario = 2

        init_task(contract)

        db.session.commit()


    except Exception as e:
        print(e)
        return "error"

    print('sending ok')
    delayed(1, send_iteration, [])
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

            drop_task(contract)

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
    try:
        send_message(contract_id, "Пожалуйста, заполните анкету кардиомониторинга.", action_link="frame",
                     action_name="Заполнить анкету", action_onetime=True, only_doctor=False, only_patient=True,
                     action_deadline=int(time.time()) + 24 * 59 * 60)
    except Exception as e:
        print('connection error', e)


def send_warning(contract_id, a, scenario):
    diagnosis = "сердечной недостаточности"
    if scenario == 1:
        diagnosis = "стенокардии"
    elif scenario == 2:
        diagnosis = "фибрилляции предсердий"

    try:
        send_message(contract_id,
                     text="По итогам опроса и мониторинга у вас налюдаются следующие симптомы {}:\n - {}\n\nМы направили уведомление о симптомах вашему лечащему врачу, он свяжется с вами в ближайшее время.".format(diagnosis, '\n - '.join(a)),
                     is_urgent=True, only_patient=True)
        send_message(contract_id, text="У пациента наблюдаются симптомы {} ({}).".format(diagnosis, ' / '.join(a)),
                     is_urgent=True, only_doctor=True, need_answer=True)
    except Exception as e:
        print('connection error', e)

def send_iteration():
    contracts = Contract.query.all()
    now = datetime.datetime.now()
    hour = now.hour
    for contract in contracts:
        if hour > 0 and hour < 8 and (time.time() - contract.last_task_push) > (get_delta(contract.mode) - 8 * 60 * 60):
            print("{}: Init task to {}".format(gts(), contract.id))
            init_task(contract)

        if hour > 8 and hour < 22 and (contract.last_task_id != None or (contract.last_task_push is None or contract.last_task_push == 0)) and time.time() - contract.last_push > get_delta(contract.mode):
            send(contract.id)
            print("{}: Sending form to {}".format(gts(), contract.id))
            contract.last_push = int(time.time())

    db.session.commit()
    time.sleep(60 * 5)

def sender():
    while True:
        send_iteration()


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

        return render_template('form.html', scenario=query.first().scenario)

    except:
        return "error"


def check_params(contract_id, scenario, data):
    report = []

    if scenario == 0:
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
            last_weight = get_records(contract_id, 'weight', limit=1)['values'][0]['value']
            week_weight = [record['value'] for record in
                           get_records(contract_id, 'weight', time_from=time_from, time_to=time_to)['values']]

            delta = last_weight - sum(week_weight) / len(week_weight)
            if delta >= 2:
                small_warnings.append('увеличение веса на {} кг'.format(round(delta, 1)))
            if delta <= -1:
                small_warnings.append('уменьшение веса на {} кг'.format(round(-delta, 1)))

        except Exception as e:
            print(e)

        # control waist_circumference
        try:
            last_value = get_records(contract_id, 'waist_circumference', limit=1)['values'][0]['value']
            week_value = [record['value'] for record in
                          get_records(contract_id, 'waist_circumference', time_from=time_from, time_to=time_to)[
                              'values']]

            delta = last_value - sum(week_value) / len(week_value)
            if delta >= 5:
                big_warnings.append('увеличение окружности талии на {} см'.format(round(delta, 1)))

        except Exception as e:
            print(e)

        # control leg_circumference
        try:
            last_value_left = get_records(contract_id, 'leg_circumference_left', limit=1)['values'][0]['value']
            last_value_right = get_records(contract_id, 'leg_circumference_right', limit=1)['values'][0]['value']

            change = abs(last_value_left - last_value_right)
            if change >= 3:
                big_warnings.append('разница между обхватом голени с разных сторон - {} см'.format(round(change, 1)))

            week_values_left = [record['value'] for record in
                                get_records(contract_id, 'leg_circumference_left', time_from=time_from,
                                            time_to=time_to)['values']]
            week_values_right = [record['value'] for record in
                                 get_records(contract_id, 'leg_circumference_right', time_from=time_from,
                                             time_to=time_to)['values']]

            delta_left = last_value_left - sum(week_values_left) / len(week_values_left)
            delta_right = last_value_right - sum(week_values_right) / len(week_values_right)
            if delta_left >= 3:
                big_warnings.append('увеличение обхвата левой голени на {} см'.format(round(delta_left, 1)))
            if delta_right >= 3:
                big_warnings.append('увеличение обхвата правой голени на {} см'.format(round(delta_right, 1)))

        except Exception as e:
            print(e)

        # send report
        for i in range(10):
            report.append(("heartfailure_claim_{}".format(i + 1), int(criteria[i])))

        # send warning
        if len(big_warnings) > 0 or len(small_warnings) > 1:
            warnings = big_warnings + small_warnings
            delayed(1, send_warning, [contract_id, warnings, scenario])

    elif scenario == 1:
        criteria = int(data.get('stenocardia', 1))
        if criteria == 2:
            delayed(1, send_warning,
                    [contract_id, ["стенокардия при небольшой физической нагрузке"], scenario])

        report.append(("stenocardia_claim_1", criteria))
    else:
        warnings = []
        criteria1 = int(data.get('fibrillation1', 1))
        if criteria1 == 2:
            warnings.append("выраженные симптомы без нарушения нормальной жизнедеятельности")
        if criteria1 == 3:
            warnings.append("выраженные симптомы c нарушением нормальной жизнедеятельности")

        criteria2 = int(data.get('fibrillation2', 1))
        if criteria2 == 2:
            warnings.append("тяжелые кровотечения")

        report.append(("fibrillation_claim_1", criteria1))

        report.append(("fibrillation_claim_2", criteria2))

        if len(warnings) > 0:
            delayed(1, send_warning, [contract_id, warnings, scenario])

    delayed(1, add_records, [contract_id, report])


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
    submit_task(contract)

    db.session.commit()

    delayed(1, check_params, (contract.id, contract.scenario, request.form))

    print("{}: Form from {}".format(gts(), contract_id))

    return """
            <strong>Спасибо, окно можно закрыть</strong><script>window.parent.postMessage('close-modal-success','*');</script>
            """


t = Thread(target=sender)
t.start()

app.run(port=PORT, host=HOST)
