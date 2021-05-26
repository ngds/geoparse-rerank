import subprocess
import requests
import spacy
import sys
import json
import os
import geocoder
from fuzzywuzzy import process, fuzz
from sklearn.cluster import AgglomerativeClustering
import numpy as np

ACCEPTED_TAGS = ["GPE", "LOC"]
CMD_TEMPLATE = "./runGeoParse.sh"
GEONAME_URL = "http://api.geonames.org/hierarchyJSON?geonameId={}&username=ngds_adept&style=full"
FUZZY_SIMILARITY_THRESHOLD = 0.85
NUM_CLUSTERS_PERCENT = 0.2
LOCATION_SIZE_THRESHOLD = 0.2

"""
TEMPORARY NOTES:

Currently: given the entities in a document:
    1. will fuzzy string match the geoparse results and filter out the strings 
        that aren't close to the original term. 
    2. requests hierarchy of each remaining location (results from geoparse)
    3. clusters the locations based on their continent and filters all but the
        largest continents (hit based, not size)
    4. clusters the locations based on their country and filters all but the 
        largest countries (hit based, not size)
    5. clusters remaining results based on physical location
    6. for each (remaining) entity that was found in the document, choose 
        geoparse result that belongs to the largest cluster, then remove
        all other occurances before checking for the next result


TODO:
    1. speed up hierarchy fetching by running in parallel
    2. if the endpoint for fetching the heirarchy changes, change GEONAME_URL and, if necessary,
        get_geoname_hierarchy() should be modified to match
    3. For thhe US, bring filtering down to the state level
"""


class NER:

    def debug(self, msg):
        print(f"[DEBUG] {msg}\n")

    def __init__(self, files_location: str):
        self.nlp = spacy.load("en_core_web_trf")
        self.files_location = files_location
        self.load_docs()
        document_entities = self.tag_entities()
        self.run_geonorm(document_entities)

    def load_docs(self):
        print("Loading docs...")
        self.txt_docs = {}
        for file in os.listdir(self.files_location):
            if file.endswith(".txt"):
                f = open(self.files_location + file, "r", encoding="utf8")
                self.txt_docs[file] = '\n'.join(f.readlines())
                f.close()
        print("Docs loaded.")

    """
    Collects all of the entities for each doc and stores in a dictionary
    returns: a dictionary mapping the document name to a list of strings (the entities)
    """
    def tag_entities(self):
        # {doc1: [ent11, ent12, ...], doc2: [ent21, ent22, ..], ...}
        documents = {}
        for docname in self.txt_docs.keys():
            print(f"Tagging {docname}...")
            doc = self.txt_docs[docname]
            spacy_doc = self.nlp(doc)
            # Entities for the current document
            entities = []
            for ent in spacy_doc.ents:
                if ent.label_ not in ACCEPTED_TAGS:
                    continue
                entities.append(ent.text)
            documents[docname] = entities
            self.debug(f"\tFound {len(entities)} entities in the document")
        print("Done tagging documents")
        return documents
            
    def run_geonorm(self, documents):
        self.debug("Running geoparse")
        for docname in documents.keys():
            if len(documents[docname]) == 0:
                continue
            multiword = {}
            cmd = [CMD_TEMPLATE]
            # Creats the cmd so it is ./runGeoParse.sh "ent1" "ent2" ...
            for ent in documents[docname]:
                cmd.append(f"\"{ent}\"")
                """
                if len(ent.split()) > 1:
                    multiword[ent] = geocoder.geonames(ent, key="geonorm_rerank")
                    print(multiword)
                else:
                    cmd.append(f"\"{ent}\"")
                """
            self.debug(f"{' '.join(cmd)[:40]}...")
            pipe = subprocess.run(" ".join(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

            with open("./debug/geoparse_output.txt", 'w+', encoding='utf8') as f:
                f.write(pipe.stdout.decode('utf-8'))

            reranked = self.rerank_results(pipe.stdout.decode('utf-8'))

            self.debug("Saving reranked_results - (location, geoname_id)")
            with open("./debug/reranked_results.txt", "w+", encoding="utf8") as f:
                f.write(str(reranked))

            results_dict = {}
            document_results = []
            ent_idx = 0
            for location in reranked.keys():
                geoparse_results = reranked[location]
                for result in geoparse_results:
                    self.debug(f"Getting hierarchy of {result[0]} which was returned for {location} - {result[1]}")
                    # TODO: speed up runtime by running this in multiple threads, this is mainly just lots of
                    #       external IO waiting
                    result_dict = self.get_geoname_hierarchy(result[1])
                    if result_dict is not None:
                        result_dict["NAME"] = result[0]
                        result_dict["ENTITY"] = location
                        result_dict["GROUP"] = ent_idx
                        # result_dict has ID,CONT,PCLI,LAT,LNG,NAME,GROUP of the geoparse result
                        document_results.append(result_dict)
                ent_idx += 1

            self.debug("Saving result_dict - [{{ID:~,CONT:~...}},...]")
            with open("./debug/result_dict.txt", "w+", encoding="utf8") as f:
                f.write(str(results_dict))

            # document_results = [{ID:~,CONT:~,PCLI:~,LAT:~,:LNG:~,NAME:~,GROUP:~}, {ID:~,...}, ...]
            document_results = self.remove_region_outliers(document_results, "CONT")
            document_results = self.remove_region_outliers(document_results, "PCLI")

            X = []
            for result in document_results:
                coord = [float(result["LAT"]), float(result["LNG"])]
                X.append(coord)

            clusters = self.cluster_locations(np.array(X))
            self.decide_final_results(document_results, clusters, ent_idx)
        
    """
    n_groups: the number of entities found in document that are remaining
    """
    def decide_final_results(self, document_results, clusters, n_groups):
        self.debug("Filtering final clusters")
        cluster_sizes = self.get_cluster_sizes(clusters)
        self.debug(f"cluster_sizes: {str(cluster_sizes)}")
        max_groups = [None] * n_groups
        # add the cluster to the document results
        for i in range(len(document_results)):
            document_results[i]["CLUSTER"] = clusters.labels_[i]

        for group in range(n_groups):
            self.debug(f"filtering group {group}...")
            max_cluster_size = -1
            max_cluster_result = None
            for result in document_results:
                if result["GROUP"] != group:
                    continue
                self.debug(f"checking result {str(result)}")
                cluster = clusters.labels_[result["CLUSTER"]]
                if cluster_sizes[cluster] > max_cluster_size:
                    max_cluster_size = cluster_sizes[cluster]
                    max_cluster_result = result

            if max_cluster_result is not None:
                self.debug(f'max result for group {group} was from cluster {max_cluster_result["CLUSTER"]}')
            document_results = list(filter(lambda r: r["GROUP"] != group or r is max_cluster_result, document_results))
        self.debug("finished finalizing results...")
        self.debug(f"{str(document_results)}")

    def get_cluster_sizes(self, clusters):
        cluster_sizes = [0]*clusters.n_clusters
        for label in clusters.labels_:
            cluster_sizes[label] += 1
        return cluster_sizes
        
    """
    Given a list of results in the format returned by 'get_geoname_hierarchy', will find the region 
    where the most entities reside and filter out entities not in that region. Level is the key for the
    dictionary that indicates the regional level to filter. Works with "CONT" and "PCLI"
    """
    def remove_region_outliers(self, doc_results, level):
        self.debug(f"Removing {level} outliers")
        cont_counts = {}
        num_results = len(doc_results)
        for result in doc_results:
            if result[level] in cont_counts.keys():
                cont_counts[result[level]] += 1
            else:
                cont_counts[result[level]] = 0

        self.debug(f"counts: {cont_counts}")
        filtered_results = []
        for result in doc_results:
            if cont_counts[result[level]] >= num_results*LOCATION_SIZE_THRESHOLD:
                filtered_results.append(result)
        return filtered_results

    """
    Given the geoname id of a location, will construct a dictionary that contains the ID, CONT, PCLI, LAT, and LONG
    of the location from geonames and return the dictionary. If any of those fields aren't available from geonames,
    then None is returned
    """
    def get_geoname_hierarchy(self, id):
        result = {"ID":id, "CONT":None, "PCLI":None, "LAT":-1, "LNG":-1}
        r = requests.get(GEONAME_URL.format(id))
        if r.status_code != 200:
            print(f"Invalid status code returned! {r.status_code}")
            exit()

        data = json.loads(r.text)["geonames"]
        if len(data) == 0:
            return None
        result["LAT"] = data[-1]["lat"]
        result["LNG"] = data[-1]["lng"]
        for name in data:
            if "fcode" in name.keys() and name["fcode"] == "CONT":
                result["CONT"] = name["name"]
            elif "fcode" in name.keys() and name["fcode"] == "PCLI":
                result["PCLI"] = name["name"]
        
        if result["CONT"] == None or result["PCLI"] == None:
            return None
        else:
            return result

    def cluster_locations(self, X):
        # X is a 2xN (np) matrix of points
        self.debug(f"Fitting points: {X}")
        n_clusters = int(X.shape[0]*NUM_CLUSTERS_PERCENT)
        ward = AgglomerativeClustering(n_clusters=n_clusters, linkage='ward')
        clusters = ward.fit(X)
        return clusters

    # reranked is a dictionary mapping locations to lists of reranked tuples of locations
    # only keeps the closest matches
    #"location": [(loc1, geonorm_id), ...]
    def rerank_results(self, output):
        locations = output.split("\n\n")
        reranked = {}
        for loc in locations:
            reranked.update(self.rerank_location(loc.strip()))
        return reranked

    def rerank_location(self, output):
        lines = output.split("\n")
        selected_locs = [(loc.split(":")[0].strip(), loc.split(":")[1].strip()) for loc in lines[1:]]

        results = []
        for loc in selected_locs:
            similarity = fuzz.ratio(lines[0].strip(), loc[0])
            # Ignore results that are too different from the parsed entity
            if similarity >= FUZZY_SIMILARITY_THRESHOLD:
                results.append( (loc[0], loc[1]) )
        
        results.sort(key = lambda x: x[1], reverse=True)
        result_dict = {lines[0].strip(): results}
        return result_dict

        
        


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("Too few arguments given!")
        ner = NER("./")
    else:
        path = sys.argv[1]
        if path.startswith('/'):
            path = path[1:]
        ner = NER(path)

