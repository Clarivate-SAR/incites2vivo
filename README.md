## incites2vivo

Mapping publications from the Web of Science InCites platform via the [InCites Document Level Metrics API](https://developer.clarivate.com/apis/incites) to [VIVO](http://vivoweb.org)

This tool requires a subscription to the InCites API. If you do not already have a username and password for the API, please reach out to your Web of Science Group account manager.

### installation

Python 2.7+ is required. Compatible with Python 3. 

Clone the repository and install requirements.

```
$ git clone https://github.com/Clarivate-SAR/incites2vivo.git
$ cd incites2vivo
$ pip install -r requirements.txt
```

### usage

If you wish to post RDF directly to VIVO, the following environment variables are required to configure incites2vivo. 

* VIVO_URL - the actual URL for your VIVO instance
* VIVO_EMAIL - username with SPARQL query privileges 
* VIVO_PASSWORD - password for above username

An example environment file is included in this repository as local.env. Running Linux or macOS you can edit this file, then load by executing:
```
$ source local.env
```

Important note: The InCites API is queried using Web of Science IDs (aka accession numbers), e.g. WOS:000188396500010. The IDs must already be in your VIVO database. The IDs should be indicated following this example triple:  
```<http://publication.uri> <http://webofscience.com/ontology/wos#wosId> "WOS:000188396500010"```

##### run a harvest 

```
$ python incites2vivo.py --help

usage: incites2vivo.py [-h] [-f {xml,n3,turtle,nt,pretty-xml,trix}] [--debug]
                       [--api] [--extended]

optional arguments:
  -h, --help            show this help message and exit
  -f {xml,n3,turtle,nt,pretty-xml,trix}, --format {xml,n3,turtle,nt,pretty-xml,trix}
                        The RDF format for serializing. Default is turtle.
  --debug               Set logging level to DEBUG.
  --api                 Post triples to VIVO.
  --extended            Create RDF for additional InCites fields. *NOTE* These
                        fields may NOT be shown publicly.
```

##### example
Query VIVO for documents with Web of Science IDs (accession numbers) and retreive data from the InCites API for those IDs.

```
$ python incites2vivo.py 
```

### data mapping

The publication metadata is mapped using custom data properties for the InCites fields. The included wos.n3 file can loaded into VIVO by including it in your home/rdf/tbox/filegraph directory or by directly uploading it using the VIVO admin interface.

Example output:
```
d:n1683 wos:avgExpectedRate "74.598" ;
    wos:impactFactor "5.763" ;
    wos:institutionCollaboration true ;
    wos:journalActExpCitations "0.37" ;
    wos:journalExpectedCitations "131.480603" ;
    wos:nci "0.6434" ;
    wos:percentile "40.5992" ;
    wos:totalCites "48" .

d:n5527 wos:avgExpectedRate "62.8659" ;
    wos:impactFactor "43.07" ;
    wos:institutionCollaboration true ;
    wos:journalActExpCitations "0.29" ;
    wos:journalExpectedCitations "348.723866" ;
    wos:nci "1.6225" ;
    wos:percentile "16.7297" ;
    wos:totalCites "102" .

d:n5990 wos:avgExpectedRate "96.4054" ;
    wos:impactFactor "1.946" ;
    wos:journalActExpCitations "68.5" ;
    wos:journalExpectedCitations "48.542056" ;
    wos:nci "34.4898" ;
    wos:percentile "0.2034" ;
    wos:totalCites "3325" .

```


