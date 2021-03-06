# Horses

A bunch of web scrapers written with Scrapy and Splash to get results, entries and pedigree information about standardbred horses.

Divided by country.

These collectors are available for each country, except where specified:

horsecollector takes the unique part of a horses url, gets the pedigree, if they have started the starts and a career summary and if it has any offspring. If the offspring is a mare the offspring of these will also be collected.

resultcollector collects the results available between a start_date and an end_date, these default to yesterday.

startlistcollector collects the startlists that are available.

Belgium
=======
All information collected from https://www.trotting.be/

Denmark
=======
All information collected from DTCs site.
They do not publish startlists so there is no collection of those.

Finland
=======
All information collected from https://heppa.hippos.fi

France
======
Right now all information is collected from https://www.letrot.com/fr/
Later more information will be collected from https://infochevaux.ifce.fr/fr/info-chevaux and https://www.pmu.fr/

horsecollector: the horse also has a list of siblings to the horse, these are also collected and any offspring to a mare will also be collected.

Germany
=======
All information collected from https://www.hvtonline.de/

Holland
=======
All information collected from https://www.ndr.nl/
Somewhat limited amount of information can be collected.

Norway
======
horsecollector: information is collected from www.travsport.no.

resultcollector and startlistcollector gets all information from https://www.rikstoto.no. These does not collect results and entries for qualifiers, those are found on www.travsport.no.

Spain
=====
All information collected from https://www.federaciobaleardetrot.com

Sweden
======
All information collected from https://sportapp.travsport.se, except for resultcollector where odds is collected from https://www.atg.se.

The plan is to write a couple of additional scrapers to also collect toplists and breeding information.
