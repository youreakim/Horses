# Horses

A bunch of web scrapers written with Scrapy and Splash to get results, entries and pedigree information about standardbred horses.
Divided by country

Norway
======
horsecollector takes a ueln / registration number or a name of a horse as startpoint, gets the pedigree, if they have started the starts and a career summary and if it has any offspring. If the horse is a mare and has offspring, it will collect all this information for those also. All information is collected from www.travsport.no.

resultcollector collects the results available between a start_date and an end_date, these default to yesterday.

startlistcollector collects the startlists that are available for the coming week.

Results and entries are collected from https://www.rikstoto.no. These does not collect results and entries for qualifiers, those are found on www.rikstoto.no.

France
======
Right now all information is collected from https://www.letrot.com/fr/

horsecollector takes the unique part of a horses url, gets the pedigree, if they have started the starts and a career summary and if it has any offspring, in addition siblings. If the offspring or sibling is a mare the offspring of these will also be collected.

resultcollector collects the results available between a start_date and an end_date, these default to yesterday.

startlistcollector collects the startlists that are available for the coming week.

Later more information will be collected from https://infochevaux.ifce.fr/fr/info-chevaux and https://www.pmu.fr/

