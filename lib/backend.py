"""
Helper code for connecting to VIVO's SPARQL Update API.
"""


import os
import hashlib
from datetime import datetime

from rdflib import Graph, URIRef
from rdflib.query import ResultException
from rdflib.compare import graph_diff

from vstore import VIVOUpdateStore

from namespaces import ns_mgr

import logging
logger = logging.getLogger('backend')

BATCH_SIZE=500
CACHE_PATH = 'data/'


class SyncVStore(VIVOUpdateStore):
    """
    Extending VIVOUpdateStore with utilities
    for syncing data to named graphs.
    """

    def ng_construct(self, named_graph, rq):
        """
        Run construct query against a named graph.
        """
        ng = URIRef(named_graph)
        query = rq
        try:
            rsp = self.query(
                query,
                initBindings=dict(g=ng),
            )
            return rsp.graph
        except ResultException:
            return Graph()

    def get_existing(self, named_graph):
        """
        Get existing triples from a named graph.
        """
        # SPARQL query to fetch existing data.
        rq = """
        CONSTRUCT {?s ?p ?o }
        WHERE { GRAPH ?g {?s ?p ?o } }
        """
        return self.ng_construct(named_graph, rq)

    def sync_named_graph(self, name, incoming, size=BATCH_SIZE):
        """
        Pass in incoming data and sync with existing data in
        named graph.
        """
        existing = self.get_existing(name)
        both, adds, deletes = graph_diff(incoming, existing)
        del both
        added = self.bulk_add(name, adds, size=size)
        logger.info("Adding {} triples to {}.".format(added, name))
        removed = self.bulk_remove(name, deletes, size=size)
        logger.info("Removed {} triples from {}.".format(removed, name))
        return added, removed

    def ng_select(self, named_graph, rq):
        """
        Run a select query
        """
        query = rq
        try:
            rsp = self.query(query)
            logger.debug("Response from API: {}".format(rsp.serialize(format="json")))
            return rsp.serialize(format="json")
        except ResultException:
            return Graph()


def post_updates(named_graph, graph, gout=None, delay=20):
    """
    Function for posting the data.
    """
    vstore = get_store()

    existing = vstore.get_existing(named_graph)

    # Get the URIs for statements that will be additions.
    changed_uris = set([u for u in graph.subjects()])

    # Get the statements from the deletes that apply to this
    # incremental update. This will be the posted deletes.
    remove_graph = Graph()
    # Remove all triples related to the changed uris.
    for curi in changed_uris:
        for pred, obj in existing.predicate_objects(subject=curi):
            remove_graph.add((curi, pred, obj))

    # Diff
    both, adds, deletes = graph_diff(graph, remove_graph)

    if gout:
        deletes+=gout

    num_additions = len(adds)
    num_remove = len(deletes)

    if (num_additions == 0) and (num_remove == 0):
        logger.info("No updates to {}.".format(named_graph))
    else:
        if num_additions > 0:
            logger.info("Will add {} triples to {}.".format(num_additions, named_graph))
            vstore.bulk_add(named_graph, adds, size=BATCH_SIZE)

        if num_remove > 0:
            logger.info("Will remove {} triples from {}.".format(num_remove, named_graph))
            vstore.bulk_remove(named_graph, deletes, size=BATCH_SIZE)

    return num_additions, num_remove


def sync_updates(named_graph, graph, size=BATCH_SIZE):
    """
    Function for posting the data.
    """
    logger.info("Syncing {}.".format(named_graph))
    vstore = get_store()
    add, remove = vstore.sync_named_graph(named_graph, graph, size=size)
    return add, remove


def get_store():
    """
    Connect to the raw store.
    """

    # Define the VIVO store
    query_endpoint = os.environ['VIVO_URL'] + '/api/sparqlQuery'
    update_endpoint = os.environ['VIVO_URL'] + '/api/sparqlUpdate'
    vstore = SyncVStore(
                os.environ['VIVO_EMAIL'],
                os.environ['VIVO_PASSWORD']
            )
    vstore.open((query_endpoint, update_endpoint))
    vstore.namespace_manager = ns_mgr
    return vstore


def srlz(g, format="turtle"):
    ng = Graph()
    ng.namespace_manager = ns_mgr
    ng += g
    return(ng.serialize(format=format))


def write_out(content, prefix='rdf-'):
    timestamp = str(datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))
    path = os.path.normpath(CACHE_PATH + prefix + "-" + timestamp + "-in.ttl")
    logger.info(path)
    try:
        with open(path, "wb") as f:
            f.write(content)
            logger.info('Wrote RDF to ' + path)
    except IOError:
        # Handle the error.
        logger.error("Failed to write RDF file. "
              "Does a directory named 'data' exist?")
        logger.warning("The following RDF was not saved: \n" +
             content)
    except:
        logger.error("Failed to write RDF file. ")
        logger.warning("The following RDF was not saved: \n" +
             content)


def to_nt(g, path):
    g.serialize(path, format="nt")
    return True


def hash_local_name(prefix, value):
    return prefix + '-' + hashlib.md5(value.encode('utf-8')).hexdigest()
