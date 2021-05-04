import subprocess
import spacy
import sys
import os
import geocoder
from fuzzywuzzy import process, fuzz
from typing import Text

ACCEPTED_TAGS = ["GPE", "LOC"]
CMD_TEMPLATE = "./runGeoParse.sh"


class NER:

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
        return documents
            

    def run_geonorm(self, documents):
        
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
            print(" ".join(cmd))
            pipe = subprocess.run(" ".join(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            print("pipe:")
            print(pipe.stdout)
            print(pipe.stderr)
            # call rerank_results on stdout of pipe

    def rerank_results(self, output):
        locations = output.split("\n\n")
        reranked = {}
        for loc in locations:
            reranked.update(self.rerank_location(loc.strip()))

        # reranked is a dictionary mapping locations to lists of reranked tuples of locations
        #"location": [(loc1, sim_percent, geonorm_id), ...]

    def rerank_location(self, output):
        lines = output.split("\n")
        selected_locs = [(loc.split(":")[0].strip(), loc.split(":")[1].strip()) for loc in lines[1:]]

        results = []
        for loc in selected_locs:
            results.append( (loc[0], fuzz.ratio(lines[0].strip(), loc[0]), loc[1]) )
        
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

