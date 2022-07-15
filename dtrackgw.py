import os
import sys
import boto3
import usb.core
import usb.util
import json

from botocore.exceptions import ClientError

with open('configgw.json', 'r') as config:
    CONFIG = json.loads(config.read())


def processar(p, msg):
    if not isinstance(msg, bytes):
        msg = msg.encode('utf-8')
    p.write(msg, 300000)
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
        for msg in messages:
            yield msg
    except ClientError as error:
        raise error
    else:
        return messages


try:
    vendors = [
        2655,
        8401,
    ]
    printer = None
    for dev in usb.core.find(find_all=True):
        print(dev.idVendor)
        if dev.idVendor in vendors:
            device = dev
            device.reset()
            if device.is_kernel_driver_active(0):
                device.detach_kernel_driver(0)
            device.set_configuration()
            cfg = device.get_active_configuration()
            intf = cfg[(0, 0)]
            printer = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            )
            break
    processar(printer, "^XA^MTd^JUS^XZ")

    session = boto3.Session(
        aws_access_key_id=CONFIG['aws_access_key_id'],
        aws_secret_access_key=CONFIG['aws_secret_access_key'],
        region_name=CONFIG['region_name'],
    )
    sqs = session.resource('sqs')
    queue = sqs.get_queue_by_name(QueueName=CONFIG['queue'])
    while True:
        processar(printer, "~HS")
        for msg in receive_messages(queue):
            r = processar(printer, msg.body)
            if bool(r):
                try:
                    msg.delete()
                except ClientError:
                    pass
except KeyboardInterrupt:
    print('Interrupted')
    try:
        sys.exit(0)
    except SystemExit:
        os._exit(0)
