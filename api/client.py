import argparse
import os
import requests
import urllib.parse

from cloudevents.http import CloudEvent, to_structured, from_json

DEFAULT_URL = 'http://localhost:8000'

TOKEN = os.getenv('TOKEN')


def publish(args):
    attributes = {
        "type": "api.kernelci.org",
        "source": "https://api.kernelci.org/",
    }
    data = {"message": args.message}
    event = CloudEvent(attributes, data)
    headers, body = to_structured(event)
    headers['Authorization'] = f"Bearer {TOKEN}"
    path = '/'.join(['publish', args.channel])
    url = urllib.parse.urljoin(args.url, path)
    res = requests.post(url, data=body, headers=headers)
    res.raise_for_status()


def listen(args):
    headers = {
        'Authorization': f"Bearer {TOKEN}",
    }
    path = '/'.join(['subscribe', args.channel])
    url = urllib.parse.urljoin(args.url, path)
    res = requests.post(url, headers=headers)
    res.raise_for_status()

    print(f"Listening for events on channel {args.channel}.")
    print("Press Ctrl-C to stop.")

    try:
        while True:
            path = '/'.join(['listen', args.channel])
            url = urllib.parse.urljoin(args.url, path)
            res = requests.get(url, headers=headers)
            res.raise_for_status()
            json_data = res.json().get('data')
            event = from_json(json_data)
            print(f"Message: {event.data.get('message')}")
    except Exception as e:
        print(f"Error: {e}")
    except KeyboardInterrupt as e:
        print(f"Stopping.")
    finally:
        path = '/'.join(['unsubscribe', args.channel])
        url = urllib.parse.urljoin(args.url, path)
        res = requests.post(url, headers=headers)
        res.raise_for_status()


if __name__ == '__main__':
    parser = argparse.ArgumentParser("KernelCI API Client")
    sub_parsers = parser.add_subparsers(title="Commands")

    def _add_args(sub_parser):
        sub_parser.add_argument('channel', help="Channel name")
        sub_parser.add_argument('--url', default=DEFAULT_URL, help="Base URL")

    parser_listen = sub_parsers.add_parser('listen', help="Listen to events")
    parser_listen.set_defaults(func=listen)
    _add_args(parser_listen)

    parser_publish = sub_parsers.add_parser('publish', help="Publish events")
    parser_publish.set_defaults(func=publish)
    _add_args(parser_publish)
    parser_publish.add_argument('message', help="Message to send")

    args = parser.parse_args()
    args.func(args)
