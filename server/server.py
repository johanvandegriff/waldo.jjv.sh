from flask import Flask, render_template, send_file, jsonify, abort, request #, Response, url_for
import xmpp
import phonenumbers
import json
import os
import shutil
import base64

ORDER_STATUSES = [
    'PLACED',
    'PRINTED',
    'GIVEN',
]

ORDERS_DIR = 'data/orders'
os.makedirs(ORDERS_DIR, exist_ok=True)

with open('secrets.json', 'r') as f:
    secrets = json.load(f)


ALLOWED_SMS_CHARS = '''abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 !@#$%&*()-_=+;:'",./<>?''' #there are more but they are unicode. notably disallowed are ^|\
def sanitize_sms(text):
    result = ''
    for char in text.replace('\n', ' '):
        if char in ALLOWED_SMS_CHARS:
            result += char
    return result

#may throw an exception
def standardize_phone_number(number):
    # convert phone number to +12345678900 format
    return phonenumbers.format_number(phonenumbers.parse(number, 'US'), phonenumbers.PhoneNumberFormat.E164)

#may throw a variety of exceptions (phone # format, failed to send sms, etc.)
def send_sms(number, message):
    number = standardize_phone_number(number)
    print('send_sms', number, message)

    jabberid = secrets['xmpp_user'] #"user@chatterboxtown.us"
    password = secrets['xmpp_pass']
    receiver = f'{number}@cheogram.com' #"+12345678900@cheogram.com"

    jid = xmpp.protocol.JID(jabberid)
    connection = xmpp.Client(server=jid.getDomain()) #, debug=debug)
    connection.connect()
    connection.auth(user=jid.getNode(), password=password, resource=jid.getResource())
    connection.send(xmpp.protocol.Message(to=receiver, body=message))


app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
    return send_file('static/favicon.ico')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check-phone-number')
def check_phone_number():
    try:
        return standardize_phone_number(request.args.get('num'))
    except:
        return ''

def set_order(order_id, order):
    os.makedirs(f'{ORDERS_DIR}/{order_id}', exist_ok=True)
    with open(f'{ORDERS_DIR}/{order_id}/info.json', 'w') as f:
        json.dump(order, f, indent=2)

def get_order(order_id):
    order_id = order_id.replace('..', '').replace('/', '')
    with open(f'{ORDERS_DIR}/{order_id}/info.json', 'r') as f:
        info = json.load(f)
    info['id'] = order_id
    info['num_stickers'] = get_num_stickers(info)
    return info

def get_queue():
    queue = []
    for order_id in sorted(os.listdir(ORDERS_DIR)):
        order = get_order(order_id)
        if order['status'] != 'GIVEN': #orders which are not fully done are considered to be in the queue
            queue.append(order)
    return queue

def new_order_id():
    order_ids = [int(i) for i in os.listdir(ORDERS_DIR)]
    if len(order_ids) == 0:
        order_ids.append(0)
    order_id = max(order_ids) + 1
    return str(order_id).zfill(8)

def get_num_stickers(order):
    num_stickers = 0
    for item in order['cart']:
        num_stickers += item ['imgQty']
        num_stickers += item ['img90Qty']
    return num_stickers

@app.route('/order', methods=['POST'])
def order_endpoint():
    data = request.get_json()
    try:
        phone_number = standardize_phone_number(data['phoneNumber'])
    except:
        return 'invalid phone number'
    address = data['address']
    queue = get_queue()
    phone_numbers = [item['phoneNumber'] for item in queue]
    if phone_number in phone_numbers: #check if this phone number has an order in queue already
        return 'you already have an order in the queue'
    if len(queue) >= secrets['queue_limit']:
        return 'the order queue is full, try again later'
    order_id = new_order_id()
    num_stickers = get_num_stickers(data)
    data['status'] = 'PLACED'
    set_order(order_id, data)
    if secrets.get('send_admin_sms_on_order', False):
        send_sms(secrets['admin_phone_number'], f'order of {num_stickers} stickers placed for {phone_number} at address: {sanitize_sms(address)}')
    return 'ok'


@app.route('/get-queue', methods=['POST'])
def get_queue_endpoint():
    data = request.get_json()
    if not data or data.get("password") != secrets['admin_pass']:
        return 'unauthorized', 401
    q = get_queue()
    for item in q:
        del item['cart']
    return json.dumps(q)

@app.route('/get-queue-data', methods=['POST'])
def get_queue_data_endpoint():
    data = request.get_json()
    if not data or data.get("password") != secrets['admin_pass']:
        return 'unauthorized', 401
    q = get_queue()
    return json.dumps(q)

@app.route('/get-order', methods=['POST'])
def get_order_endpoint():
    data = request.get_json()
    if not data or data.get("password") != secrets['admin_pass']:
        return 'unauthorized', 401
    order_id = data['order_id']
    order = get_order(order_id)
    return json.dumps(order)

@app.route('/mark-printed', methods=['POST'])
def mark_printed():
    data = request.get_json()
    if not data or data.get("password") != secrets['admin_pass']:
        return 'unauthorized', 401
    order_id = data['order_id']
    order = get_order(order_id)
    phone_number = order['phoneNumber']
    order['status'] = 'PRINTED'
    send_sms(phone_number, secrets['printed_message'])
    set_order(order_id, order)
    return 'ok'

@app.route('/mark-given', methods=['POST'])
def mark_given():
    data = request.get_json()
    if not data or data.get("password") != secrets['admin_pass']:
        return 'unauthorized', 401
    order_id = data['order_id']
    order = get_order(order_id)
    order['status'] = 'GIVEN'
    set_order(order_id, order)
    return 'ok'

@app.route('/delete-order', methods=['POST'])
def delete_order():
    data = request.get_json()
    if not data or data.get("password") != secrets['admin_pass']:
        return 'unauthorized', 401
    order_id = data['order_id']
    order_id = int(order_id)
    order_id = str(order_id).zfill(8)
    order_id = order_id.replace('..', '').replace('/', '')
    shutil.rmtree(f'{ORDERS_DIR}/{order_id}')
    return 'ok'

# @app.route('/admin')
# def admin():
#     return render_template('admin.html')

HOST = '0.0.0.0'
PORT = int(os.environ.get('PORT', '8080'))

if __name__ == "__main__":
    app.run(host=HOST, port=PORT)
