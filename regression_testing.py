import json
import math

import requests
import time
import threading
import hashlib
import random
import string
import queue

host1='13.233.83.250:8080/'
host2='65.2.129.63:8080'
elb_eip='43.205.184.138'
alb_dns='MyALB-300151900.ap-south-1.elb.amazonaws.com:8080'
localhost='127.0.0.1:8000/'

hosts = [localhost]

dataset_size = 10000
req_per_sec = 50
read_write_ratio = 0.3
duration = 600  # in seconds'
write_cardinality = 0.3

queue = queue.Queue()


def generate_hash(text, data):
    hash = hashlib.md5(text.encode('utf-8')).hexdigest()[:5]
    if hash in data:
        print("collision occurred")
        return generate_hash(text + 'blah', data)
    else:
        return hash


def make_request(url, param):
    try:
        response = requests.get(url, params={'url': param})
        if 'retries' in response.json() and response.json()['retries'] != 0:
            print(param, "Integrity error retry %s" % (response.json()['retries']))
        if 'cache' in response.json():
            print(url, param, 'cache hit')
    except Exception as e:
        # print(e)
        queue.put((url, str(e), 500))
        return
    if response.status_code not in (200, 404):
        if 'retries' in response.json():
            print((url, response.json()['retries'], response.json()))
        queue.put((url, url[-10:]+response.json()['error'] if 'error' in response.json() else response.json(), response.status_code))
    return response


def foo(random_urls, read_write_ratio, write_cardinality):
    short_url = "http://{host}/short_url/"
    long_url = "http://{host}/long_url/"

    num_reqs = len(random_urls)
    reads = int(read_write_ratio * num_reqs)
    writes = int((1 - read_write_ratio) * num_reqs)
    time_between_2_reqs = 0  # num_reqs/100000 # spread the requests
    threads = []

    # long url to short url
    long_urls_param = [random_urls[i]['long_url'] for i in range(writes)]
    same = int(write_cardinality * len(long_urls_param))
    long_urls_param = long_urls_param[:len(long_urls_param) - same] + random.sample(
        long_urls_param[:len(long_urls_param) - same], same)

    cardinality = len(long_urls_param) - len(set(long_urls_param))
    for long_url_param in long_urls_param:
        t = threading.Thread(target=make_request, args=(short_url.format(host=hosts[random.randint(0,len(hosts)-1)]), long_url_param))
        t.start()
        time.sleep(time_between_2_reqs)
        threads.append(t)

    # short url to long url
    short_urls_param = [random_urls[writes + i]['short_url'] for i in range(reads)]
    for short_url_param in short_urls_param:
        t = threading.Thread(target=make_request, args=(long_url.format(host=hosts[random.randint(0,len(hosts)-1)]), short_url_param))
        t.start()
        time.sleep(time_between_2_reqs)
        threads.append(t)

    for t in threads:
        t.join()

    fails = dict()
    for url, error, status_code in queue.queue:
        if status_code == 500 and 'Failed to establish a new connection: [Errno 60] Operation timed out' in str(error):
            error='Failed to establish a new connection: [Errno 60] Operation timed out'
        if status_code == 500 and 'Failed to establish a new connection: [Errno 61] Connection refused' in str(error):
            error='Failed to establish a new connection: [Errno 61] Connection refused'

        try:
            if (status_code, error) not in fails:
                fails[(status_code, error)] = 0
        except Exception as e:
            print(e)
        fails[(status_code, error)] += 1

    queue.queue.clear()

    return reads, writes, fails, cardinality


def run(new_dataset=False):
    testing_data = []
    total_reqs, reads, writes, fails, integrity_errors, db_too_many_reqs = 0, 0, 0, 0, 0, 0

    if new_dataset:
        print("Generating dataset")
        for i in range(dataset_size):
            long_url = ''.join(random.choices(string.ascii_uppercase +
                                              string.digits + string.ascii_lowercase, k=random.randint(30, 49)))
            short_url = generate_hash(long_url, testing_data)

            testing_data.append({'long_url': long_url, 'short_url': short_url})

        with open("regression_testing.csv", 'w') as f:
            f.write(json.dumps(testing_data))
    else:
        print("Using dataset regression_testing.csv")
        testing_data = json.load(open("regression_testing.csv"))[:dataset_size]
    print("Dataset size %s"%len(testing_data))

    start_time = time.time()

    while time.time() - start_time < duration:
        s = time.time()

        random_urls = random.sample(testing_data, req_per_sec)
        reads, writes, fail, actual_write_cardinality = foo(random_urls, read_write_ratio, write_cardinality)

        total_reqs += len(random_urls)
        time_diff = time.time() - s

        print("Total requests %s, Current reads/writes (%s/%s); Write cardinality %s ; Fails "
              "%s; %s sec" % (
                  total_reqs, reads, writes, actual_write_cardinality, fail,
                  time_diff))

        time.sleep(1 - time_diff if time_diff < 1 else 0)


run(new_dataset=False)
