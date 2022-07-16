import os
import sys
import time

import boto3
import usb.core
import usb.util
import json

from botocore.exceptions import ClientError

VENDORS = [
        2655,
        8401,
    ]


with open('configgw.json', 'r') as config:
    CONFIG = json.loads(config.read())


def processar(printer, command):
    if not isinstance(command, bytes):
        command = command.encode('utf-8')
    try:
        printer.write(command, 300000)
    except usb.core.USBError:
        return False
    return True


def receive_messages(queue, max_number=10, wait_time=20):
    """
    Receive a batch of messages in a single request from an SQS queue.

    :param queue: The queue from which to receive messages.
    :param max_number: The maximum number of messages to receive. The actual number
                       of messages received might be less.
    :param wait_time: The maximum time to wait (in seconds) before returning. When
                      this number is greater than zero, long polling is used. This
                      can result in reduced costs and fewer false empty responses.
    :return: The list of Message objects received. These each contain the body
             of the message and metadata and custom attributes.
    """
    try:
        messages = queue.receive_messages(
            MessageAttributeNames=['All'],
            MaxNumberOfMessages=max_number,
            WaitTimeSeconds=wait_time
        )
        for message in messages:
            yield message
    except ClientError as error:
        raise error
    else:
        return messages


def setup_printer():
    prt = None
    for dev in usb.core.find(find_all=True):
        if dev.idVendor == 7531:
            continue
        print(dev.idVendor)
        if dev.idVendor in VENDORS:
            device = dev
            device.reset()
            if device.is_kernel_driver_active(0):
                device.detach_kernel_driver(0)
            device.set_configuration()
            cfg = device.get_active_configuration()
            intf = cfg[(0, 0)]
            prt = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            )
            break
    cmd = '^XA'
    if CONFIG['direct-termal']:
        cmd += '^MTd'
    else:
        cmd += '^MTd'
    time.sleep(1)
    if CONFIG['peel-off']:
        cmd += '^MMP'
    else:
        cmd += '^MMT'
    cmd += '^JUS^XZ'
    ok = processar(prt, cmd)
    if not ok:
        prt = None
        time.sleep(5)
    else:
        time.sleep(1)
    return prt

try:
    p = None
    while not p:
        p = setup_printer()

    session = boto3.Session(
        aws_access_key_id=CONFIG['aws_access_key_id'],
        aws_secret_access_key=CONFIG['aws_secret_access_key'],
        region_name=CONFIG['region_name'],
    )
    sqs = session.resource('sqs')
    queue = sqs.get_queue_by_name(QueueName=CONFIG['queue'])
    while True:
        try:
            processar(p, "~HS")
            for msg in receive_messages(queue):
                r = processar(p, msg.body)
                if bool(r):
                    try:
                        msg.delete()
                    except ClientError:
                        pass
        except usb.core.USBError:
            p = None
            while not p:
                p = setup_printer()

except KeyboardInterrupt:
    print('Interrupted')
    try:
        sys.exit(0)
    except SystemExit:
        os._exit(0)
