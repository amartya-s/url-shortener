from django.shortcuts import render
import hashlib
import threading
from django.db import transaction
from django.db.utils import OperationalError, IntegrityError, DatabaseError
# Create your views here.
import logging
from url_shortener.models import UrlShortener
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django_mysql.locks import TableLock
from django.views.decorators.cache import cache_page
from django.core.cache import cache

SHORT_URL_LEN = 5
READ_CTR = 0
WRITE_CTR = 0
TOTAL_CTR = 0


def index(request):
    return render(request, "url_shortener/index.html", {})


def generate_hash(text):
    hash = hashlib.md5(text.encode('utf-8')).hexdigest()[:SHORT_URL_LEN]
    if UrlShortener.objects.filter(short_url=hash).exists():
        return generate_hash(text + 'blah')
    else:
        return hash


def db_op(long_url):
    queryset = UrlShortener.objects.filter(long_url=long_url)
    if queryset.exists():
        logging.debug("Read ctr {}/{}".format(str(READ_CTR), str(TOTAL_CTR)))
        return queryset.first().short_url
    else:
        # generate short url
        short_url = generate_hash(long_url)
        UrlShortener.objects.create(long_url=long_url, short_url=short_url)

        return short_url



def short_url(request):


    global READ_CTR
    global WRITE_CTR
    global TOTAL_CTR

    long_url = request.GET['url']
    logging.info("Got long url " + long_url)

    if cache.get(long_url):
        logging.info("Returning from cache")
        return JsonResponse(data={'short_url': cache.get(long_url), 'cache': 0}, status=200)

    TOTAL_CTR += 1
    retries = 0
    while retries <= 3:
        # with TableLock(write=[UrlShortener]):
        try:
            short_url = db_op(long_url)
            cache.set(long_url,short_url)
            return JsonResponse(data={'short_url': short_url, 'retries': retries}, status=200)
        except IntegrityError as e:
            retries += 1
            logging.debug("Retrying for %s , retry count %s" % (long_url, retries))
        except OperationalError as e:
            return JsonResponse(data={'error': str(e)}, status=429)
    else:
        return JsonResponse({"error": "Integrity error, max retries done"}, status=409)



def long_url(request):
    short_url = request.GET['url']
    logging.info("Got short url " + short_url)

    if cache.get(short_url):
        logging.info("Returning from cache")
        return JsonResponse(data={'short_url': cache.get(short_url), 'cache': 0}, status=200)

    try:
        long_url = UrlShortener.objects.get(short_url=short_url).long_url
        cache.set(short_url, long_url)
        return JsonResponse({"long_url": long_url}, status=200)
    except UrlShortener.DoesNotExist:
        return JsonResponse({"data": "Not found"}, status=404)
    except OperationalError as e:
        return JsonResponse({"error": str(e)}, status=429)
