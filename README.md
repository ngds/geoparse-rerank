# geoparse-rerank
Using custom-trained spaCy NER for toponym identification, the UArizona CLU NLP lab's geonorm for toponym disambiguation, and a custom domain specific re-ranking algorithm to choose a polygon from the top options

# Usage
First, download this [scala jar](https://arizona.box.com/s/yqjn0999casxdo3m0b63szwbhlgg5pr6) and place it in the same directory as runGeoParse.sh. This jar includes code from [this project in the Bethard lab](https://github.com/clulab/geonorm). Make sure Scala is installed as well.

Also, make sure to have spaCy 3.0 or greater installed, as well as the `en_core_web_trf` model. Instructions for installing both of these can be found at https://spacy.io/usage

To run the ranking, navigate to the top-level directory and run 
```./runGeoParse.sh "Entity1" "Entity2" "Entity3"```
where "Entity1", "Entity2", "Entity3" are location names, in quotes. Any number of location names can be used. The script will output, in spaced out blocks, each entity name followed by a list of Name: GeoNames ID entries, each on its own line, in order of relevance. An example output is below:
```
./runGeoParse.sh "Tucson" "London" "Rhine"
Tucson
Tucson: 5318313
Tucson: 8800953
Tucson: 8597493
Tucson: 3980957
Tucson: 9504274
Tucson: 4526648


London
London: 2643743
London: 11591955
London: 6058560
City of London: 2643744
London: 4298960
London: 4517009
City of London: 2643741
London Village: 4030939
London: 5367815
London: 4119617
London: 4707414
London: 982316
London: 6058559
London: 2729913
London: 9499471
London: 982301
London: 982302
London: 982303
London: 982304
London: 982305
London: 982306
London: 982307
London: 982308
London: 982309
London: 982310
London: 982311
London: 982312
London: 982313
London: 982314
London: 982315
London: 888390
London: 11876643
London: 6474424
London: 9611218
London: 9955284
London: 10293491
London: 8610073
London: 8610441
London: 8610604
London: 2661811
London: 5035440
London: 3581797
Ban Sarkāri: 10304286
London: 11546715
London: 2308696
London: 2331921
Lonton: 1313003
London: 5737562
London: 4999913
London: 5035439
London: 5035441
London: 5056033
London: 5260737
London: 5161176
London: 5198788
London: 1705729
Tel’manskiy: 1489797
London: 2406961
London: 9876172
London: 10009591
London: 4637795
London: 4260673
Londonderry: 4517025
London: 4707415
Old London: 4716381
London: 4812926
London: 4073570
London: 4073571
London: 11281530
London: 982298
London: 982299
London: 982300
London: 3803838


Rhine
Rhine: 4218611
Rhine: 3488843
Rhine: 5268718

```

# Accuracy of geonorm
The geonorm ranking works better for single-word entities than for phrases; e.g. "Rhine" returns better results than "Rhine River." In a small test sample, the precision at 1 for single-word entities was 0.89, meaning that the top result returned was correct 89% of the time. In this sample, we did not distinguish between administrative districts and cities; e.g., Tucson the city and Tucson the administrative district that encompasses the entire city were treated as the same entity for the precision calculation. The recall across the entity list for single-word entities was 1, suggesting that a reranking system could be applied to further improve performance.

# Accuracy of named entity recognition
Precision and recall were measured for the model on a research paper focused primarily on the Thur River that the model had never seen before. The results are shown below:
|**True Positives** | 75 |
| ------------------| ---|
| **False Positives** | **12** |
| **False Negatives** | **10** |

Which gives a Precision of 0.862 and a Recall of 0.882, or an F1 score of 0.869


# Reranking algorithm
The reranking algorithm takes the GeoNames list of results for each named entity and performs a series of operations to choose one of the potential locations for each entity. 

As a first step, the algorithm considers each entity with its list of options. We compute the Levenshtein distance between each location's canonical name and the entity, eliminating potential locations whose names differ too much from the entity name identified. This is determined by a threshold Levenshtein distance that location names cannot exceed; the threshold is a hyperparameter.

With these reduced lists, we perform an clustering of locations across all entities using the "PCLI" code for each location, which generally denotes the country name. Because of a US-centric bias in the GeoNames data, we treat each state in the US as its own country for the purposes of this clustering.

For each cluster, the total number of unique entities represented by the locations is tabulated. The clusters are ranked from the one with the highest fraction of all entities to the one with the lowest fraction of entities, and the clusters with a fraction below a minimum threshold (a hyperparamter) are eliminated. Then, entities are assigned locations. An entity is assigned the location from its list of options that appears in the largest cluster; if there are multiple options in the same cluster, they are sorted by the original geonorms ranking.

Thus, if a document discusses primarily locations in Germany and a few in France, Germany should be the largest cluster and France the second largest. If an entity has three locations on its list: Germany Location A, Spain Location A, Germany Location B,  it will be assigned Germany Location A. If the entity does not have any Germany options on its list of locations, it will be assigned a location off its list in France, if any such location exists. If not, the algorithm continues searching through the clusters, choosing the location off the entity's list that appears in the largest cluster.

### Example reranking
For instance, say a document has 4 entities, with original ranked lists as follows:

Toronto:
* Toronto, Canada
* Toronto, South Africa

Chicago:
* Chicago, USA (Illinois)

Illinois
* Illinois, USA (Illinois)
* Illinois State University, USA (Illinois)
* Illinois, Australia

Scarborough
* Scarborough, UK
* Scarborough, USA (New York)
* Scarborough, Canada

The clusters would be as follows:

CANADA: 
* Toronto, Canada
* Scarborough, Canada

ILLINOIS: 
* Chicago, USA
* Illinois, USA
* Illinois State University, USA

SOUTH AFRICA:
* Toronto, South Africa

AUSTRALIA:
* Illinois, Australia

NEW YORK:
* Scarborough, USA

The largest cluster is Illinois, followed by Canada. The entities would be assigned locations as follows:

Toronto has no location options in the Illinois cluster, so it will be assigned the location from the next largest cluster: Toronto, Canada

Chicago has one option in the Illinois cluster: Chicago, Illinois

Illinois has two options in the Illinois cluster, so it will be assigned the one that was originally ranked first: Illinois, USA

Scarborough has no location options in the Illinois cluster, so it will be assigned the location from the Canada cluster: Scarborourgh, Canada

In this small example, the location assigned to the entity "Scarborough" is changed to reflect that the document only mentions locations in North America, and specifically that the document mentions another location in Canada. 

## Performance of reranking
Unfortunately, the performance of the reranking algorithm was poor. After tuning, the algorithm achieved an accuracy at 1 of 1/76, 
down from the 6/76 identified correctly by geonorm. It appears that the algorithm's weaknesses include
 correctly identifying countries mentioned in passing, as the clusters containing these locations are 
 eliminated because there are few unique entities in them. However, it is difficult to evaluate the algorithm fairly, as
 geonorm's low performance on this data means that many of the entities did not have the correct location in the list of
 options returned, making the reranking useless. 


# Future work

This represents a logical approach to identifying geolocations that nevertheless suffers from poor performance. Future work on this or similar issues could leverage the approaches below to possibly improve model accuracy.

Because of the poor relative performance of geonorm on this corpus, we believe the best future approaches will leverage GeoNames directly. While the reranking performed poorly with geonorm, it is possible that the approach will work better with GeoNames directly. Other approaches are detailed below.

## Choosing the correct search term
An error analysis reveals that, when querying GeoNames directly, the specific term chosen has a large impact on the search results. For instance, searching "Thur River" yields the correct location as the second result, while searching "Thur River basin" yields the correct location as the first result; however, "upper Thur River basin" does not return any results at all. Reranking would help in the case of "Thur River" but not "upper Thur River basin;" thus, it is important to choose the entity names queried carefully, to avoid situations where no results are returned.

### Performance of correct search term 
On the Thur River paper, 76 individual mentions of entities occur (these comprise 19 unique entities, representing 13 unique locations). When searching each entity name naiively, using the full entity name highlighted in manual annotation, GeoNames identifies the correct location as the first search result in 28 out of 76 searches (36.84% accuracy). However, if the absolute best search term for each entity is chosen (computed here by trial and error, using only terms in the entities found), 74 of the 76 entities would be identified correctly (97.37% accuracy). It appears the problem of matching entity to location can be reduced to the problem of matching entity to an appropriate search term. Important to note is that these search terms can be either shorter or longer than the entity name (e.g. "Thur River basin" returns better results than "Thur River," but "Ill" returns better results than "Ill River").


## Splitting multiword entities 

When using geonorm, and to a lesser extent when using GeoNames directly, multiword queries can produce less meaningful results. Future research could explore splitting entities into individual words, searching for each word, and then combining the results in some form of merge-ranking. Alternatively, some words such as "River" or "the" can be discarded, or incorporated in different ways, as proposed below.

## Using feature clues 
Each GeoNames location has a feature code identifying the "type" of location it is-- for instance, code "FRST" represents a forest, and code "SCHC" represents a college or university. A set of hard-coded rules could be written and tuned so that results are narrowed by feature code-- for instance, instead of searching for "Minamata Bay," the algorithm might search for "Minamata" and filter results to only those representing bodies of water, or only those with the feature code "BAY". This approach appears promising, but further investigation is necessary to determine if this has a positive effect on overall accuracy for multiword entities. 