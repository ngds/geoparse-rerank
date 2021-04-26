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

Which gives us a Precision of 0.862 and a Recall of 0.882, or an F1 score of 0.869
