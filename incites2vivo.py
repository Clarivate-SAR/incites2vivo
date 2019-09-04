"""
Query VIVO for UTs, query InCites for metadata, and convert to RDF
"""

import sys
import os
import time
from os import environ, path

import json
from rdflib import RDF, RDFS, Graph, Literal
from lib import backend
from lib.backend import SyncVStore
import requests
import argparse
from log_setup import get_logger

from namespaces import (
    TMP,
    D,
    WOS,
    BIBO,
    rq_prefixes
)

try:
    # Python 3
    from itertools import zip_longest
except ImportError:
    # Python 2
    from itertools import izip_longest as zip_longest

INCITES_GRAPH = "http://localhost/data/incites"

def grouper(iterable, n, fillvalue=None):
    """
    Group iterable into n sized chunks.
    See: http://stackoverflow.com/a/312644/758157
    """
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def ln(uri):
    return uri.toPython().split('/')[-1]


def get_incites(batch):
    uts = (",".join([b for b in batch if b is not None]))
    rsp = requests.get('https://api.clarivate.com/api/incites/DocumentLevelMetricsByUT/json',
            headers = {'X-ApiKey': environ['INCITES_KEY']},
            params = {'UT': uts})
    logger.debug(batch)
    logger.debug(uts)
    logger.debug(rsp.text)
    if rsp.status_code != 200:
        logger.error("Batch failed with", len(batch), "items.")
        logger.error(rsp)
        #import ipdb; ipdb.set_trace()
        return []
    data = [item for item in rsp.json()['api'][0]['rval']]
    if data == [None]:
        data = []
    return data


def get_wos_pubs():
    vstore = backend.get_store()
    rq = rq_prefixes + """
            select ?pub ?wosId
            where {
                ?pub wos:wosId ?wosId .
            }
    """
    d = {}
    logger.debug(rq)
    for row in vstore.query(rq):
        logger.debug(row)
        d[row.wosId.toPython().replace('WOS:', '')] = row.pub
    return d

def make_bool(doc, key):
    val = doc.get(key)
    if val == u"1":
        return True
    else:
        return False


def process_incites(data, pubs):
    g = Graph()
    flags = [
        ('ESI_MOST_CITED_ARTICLE', WOS.esiMostCited),
        ('HOT_PAPER', WOS.hotPaper),
        ('IS_INDUSTRY_COLLAB', WOS.industryCollaboration),
        ('IS_INTERNATIONAL_COLLAB', WOS.internationalCollaboration),
        ('OA_FLAG', WOS.openAccess),
        ('IS_INSTITUTION_COLLAB', WOS.institutionCollaboration)
    ]
    extended_fields = [
        ('TOT_CITES', WOS.totalCitations),
        ('JOURNAL_EXPECTED_CITATIONS', WOS.journalExpectedCitations),
        ('JOURNAL_ACT_EXP_CITATIONS', WOS.journalACTExpectedCitations),
        ('IMPACT_FACTOR', WOS.impactFactor),
        ('AVG_EXPECTED_RATE', WOS.averageExpectedRate),
        ('PERCENTILE', WOS.percentile),
        ('NCI', WOS.normalizedCitationImpact)
    ]

    for doc in data:
        for k, prop in flags:
            if make_bool(doc, k) is True:
                pub_uri = pubs[doc['ISI_LOC']]
                g.add((pub_uri, prop, Literal(True)))

    return g


def process_extended(data, pubs):
    g = Graph()
    extended_fields = [
        ('TOT_CITES', WOS.totalCites),
        ('JOURNAL_EXPECTED_CITATIONS', WOS.journalExpectedCitations),
        ('JOURNAL_ACT_EXP_CITATIONS', WOS.journalActExpCitations),
        ('IMPACT_FACTOR', WOS.impactFactor),
        ('AVG_EXPECTED_RATE', WOS.avgExpectedRate),
        ('PERCENTILE', WOS.percentile),
        ('NCI', WOS.nci)
    ]

    for doc in data:
        for k, prop in extended_fields:
            if k in doc:
                pub_uri = pubs[doc['ISI_LOC']]
                g.add((pub_uri, prop, Literal(doc[k])))

    return g


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--format", default="turtle", choices=["xml",
                        "n3", "turtle", "nt", "pretty-xml", "trix"], help="The"
                        " RDF format for serializing. Default is turtle.")
    parser.add_argument("--debug", action="store_true", help="Set logging "
                        "level to DEBUG.")
    parser.add_argument("--api", action="store_true", help="Post triples "
                        "to VIVO.")
    parser.add_argument("--extended", action="store_true", help="Create RDF "
                        "for additional InCites fields. *NOTE* These fields "
                        "may NOT be shown publicly.")
    return parser.parse_args(args)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    logger = get_logger(args.debug)
    filename = path.basename(__file__).replace('.py', '')

    pubs = get_wos_pubs()
    if len(pubs) == 0:
        print('Error getting publications from VIVO.')
    incites_data = []
    for batch in grouper(pubs.keys(), 100):
        idata = get_incites(batch)
        incites_data += idata

    g = process_incites(incites_data, pubs)
    if args.extended:
        g += process_extended(incites_data, pubs)
    if len(g) > 0:
        logger.info("Writing file as {}".format(filename))
        backend.write_out(backend.srlz(g, args.format), filename)

    if args.api and len(g) > 0:
        try:
            backend.post_updates(INCITES_GRAPH, g)
        except:
            logger.error("Failed to post update to VIVO")
    else:
        logger.info('No INCITES triples to INSERT or DELETE or API flag unset.')
