import requests
import json
import base64
import os
import sys
import shutil
import glob
import hashlib

from brother_ql.cli import cli

# SERVER_URL = 'http://localhost:8080'
SERVER_URL = 'https://waldo.jjv.sh'
HEADERS = {"Content-Type": "application/json"}

with open('secrets.json', 'r') as f:
    secrets = json.load(f)
password = secrets['admin_pass']
secret_phone_number = secrets['secret_phone_number']

def req(url, data):
    data['password'] = password
    return requests.post(SERVER_URL + url, json=data, headers=HEADERS)

queue = req('/get-queue-data', {}).json()

def dataURLToBytes(dataURL):
    return base64.b64decode(dataURL.split(',')[1])
    # return base64.b64decode(dataURL.replace('data:image/png;base64,', ''))


try:
    printer = glob.glob('/dev/usb/lp*')[0]
    os.system(f'sudo chmod 777 "{printer}"')
except:
    print('warning: printer not found')

def save_order(order):
    order_dir = f'orders/{order["id"]}'
    os.makedirs(f'{order_dir}/delete_to_print')
    os.makedirs(f'{order_dir}/images')
    with open(f'{order_dir}/info.json', 'w') as f:
        json.dump(order, f)
    for cart_item in order['cart']:
        for img, imgQty in [[cart_item['imgOriginal'], 0], [cart_item['img'], cart_item['imgQty']], [cart_item['img90'], cart_item['img90Qty']]]:
            # print(img[:30], imgQty)
            if True: #imgQty > 0:
                filename = hashlib.sha1(img.encode()).hexdigest()
                with open(f'{order_dir}/images/{imgQty}_{filename}.png', 'wb') as f:
                    f.write(dataURLToBytes(img))

def print_order(order):
    order_dir = f'orders/{order["id"]}'
    images = []
    for image in sorted(os.listdir(f'{order_dir}/images')):
        print(image.split('_'))
        qty, _ = image.split('_')
        for _ in range(int(qty)):
            images.append(f'{order_dir}/images/{image}')
    print(images)
    args = ['brother_ql', '--model', 'QL-800', '--printer', f'file://{printer}', 'print', '-l', '62', '--red']
    args.extend(images)
    os.system(' '.join(args))
    print(req('/mark-printed', {'order_id': order["id"]}).text)
    order['status'] = 'PRINTED'
    with open(f'{order_dir}/info.json', 'w') as f:
        json.dump(order, f)

def mark_given(order):
    order_dir = f'orders/{order["id"]}'
    print(req('/mark-given', {'order_id': order["id"]}).text)
    shutil.rmtree(order_dir)

for order in queue:
    order2 = json.loads(json.dumps(order))
    del order2['cart']
    print(order2)
    order_dir = f'orders/{order["id"]}'
    print(order_dir)
    if os.path.exists(order_dir):
        if not os.path.exists(f'{order_dir}/delete_to_print'):
            if order['status'] == 'PLACED':
                print_order(order)
                os.makedirs(f'{order_dir}/delete_when_given')
            elif order['status'] == 'PRINTED':
                if not os.path.exists(f'{order_dir}/delete_when_given'):
                    mark_given(order)
    else:
        save_order(order)
        if order['phoneNumber'] == secret_phone_number:
            print_order(order)
            mark_given(order)
