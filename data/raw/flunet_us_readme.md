# Weekly share of influenza tests that were positive - Data package

This data package contains the data that powers the chart ["Weekly share of influenza tests that were positive"](https://ourworldindata.org/explorers/influenza?Confirmed+cases+or+Symptoms=Confirmed+cases&Metric=Share+of+positive+tests+%28%25%29&Interval=Weekly&Surveillance+type=All+types&country=OWID_NH~OWID_SH) on the Our World in Data website. It was downloaded on October 17, 2026.

### Active Filters

A filtered subset of the full data was downloaded. The following filters were applied:

## CSV structure

Each row is an observation for an entity (usually a country or region) at a timepoint.

- "Entity" — the name of the entity, e.g. "United States".
- "Code" — our internal entity code. For most countries this is the [ISO alpha-3](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-3) code, e.g. "USA"; historical and other non-standard entities get a custom code.
- "Year" or "Day" — the timepoint. Annual data has a "Year" column holding an integer year; otherwise a "Day" column holds a date string in the form "YYYY-MM-DD".
- The final column is the data column — the time series that powers the chart. Downloaded with the "full data" option it corresponds to the time series below; with "only selected data visible in the chart" it is transformed depending on the chart type, so the correspondence may be less direct.


## Metadata.json structure

The .metadata.json file contains metadata about the data package. The "charts" key contains information to recreate the chart, like the title, subtitle etc. The "columns" key contains information about each of the columns in the csv, like the unit, timespan covered, citation for the data etc.

## How we process data at Our World in Data

Our World in Data is almost never the original producer of the data - almost all of the data we use has been compiled by others. If you want to re-use data, it is your responsibility to ensure that you adhere to the sources' license and to credit them correctly. Please note that a single time series may have more than one source - e.g. when we stitch together data from different time periods by different producers or when we calculate per capita metrics using population data from a second source.

Preparing this data involves several processing steps. Depending on the data, this can include standardizing country names and world region definitions, converting units, calculating derived indicators such as per capita measures, as well as adding or adapting metadata such as the name or the description given to an indicator.
[Read about our data pipeline](https://docs.owid.io/projects/etl/).

## Detailed information about the data


### Share of positive tests - All types of surveillance
Last updated: October 17, 2026  
Unit: %  
Source: World Health Organization (2023) – processed by Our World in Data  

#### How to cite this data

World Health Organization (2023) – processed by Our World in Data

#### Additional information about this data
**Dataset Description:**
- FluNET is a human influenza surveillance dataset that aggregates data from (1) the Global Influenza Surveillance and Response System (GISRS), (2) other national influenza reference laboratories that collaborate with the GISRS, and (3) other influenza surveillance data uploaded from WHO regional databases.
- Some of these samples are tested to determine whether they are influenza and whether they are influenza A or influenza B. Some surveillance centers also test the samples to identify their subtype. These are described as strains for influenza A (e.g., A H7N9) and lineages for influenza B (e.g., B Yamagata). This testing can use molecular detection, virus culture, or immunological methods.

**Surveillance types:**
- Surveillance data from each country may come from sentinel sites or non-sentinel sites.
- Sentinel sites are health centers in a country that are selected to perform high-quality testing of cases: they test for flu subtypes and lineages in a routine and timely manner.
- They are also selected in a way that is aimed to be representative of the population. For example, they include health centers in both urban and rural areas, are general hospitals rather than specialist centers, and cater to a wide range of demographics.
- The WHO provides guidelines to countries for selecting centers which will be sentinel sites, using these criteria. The selection also depends on which centers have the resources for data collection, testing and reporting.
- Sentinel data can give a representative picture of trends across time in the country. But, since not all health centers and clinics are included, the data does not tell us about the total number of infections across the country. See also: World Health Organization. (1999). WHO Recommended Surveillance Standards. Second edition. https://web.archive.org/web/20220121021824/http://www.who.int/csr/resources/publications/surveillance/whocdscsrisr992.pdf
- Data on flu can also come from 'non-sentinel' sites. This includes other kinds of testing, which may be done at point of care, in universal testing, or during outbreak investigation.
-Some samples are not categorized as either sentinel or non-sentinel surveillance. These are included in the data for 'all types' of surveillance.

**Data preparation steps:**
-  Remove rows where confirmed cases by influenza strain do not sum as expected. Specifically:
· Where all the influenza A strains do not sum to the total value given for influenza A
· Where all the influenza B strains do not sum to the total value given for influenza B
· Where influenza A + influenza B does not equal total influenza confirmed cases
- We follow the WHO’s method to calculate the ‘Share of tests that test positive (%).’ They suggest using three possible denominators, in order of preference:
· Number of negative influenza tests + number of positive tests
· Number of specimens processed
· Number of specimens received
-  We follow the above approach at the country level. At the regional level, we do not consider the number of negative influenza tests as, historically, there is not much data available for this variable.
· For example, there are many weeks where only one country has a value for negative influenza tests. Instead, we use specimens processed as the primary denominator as data for this is much more plentiful.
-  We set the negative tests to NA where the sum of negative tests is 0, and the sum of the negative and positive tests does not equal the number of processed tests.
-  We calculate an aggregate for the UK by summing data for England, N.Ireland, Scotland, and Wales.
-  We calculate global and hemisphere aggregates by summing count variables and averaging rate variables.
-  We calculate monthly from weekly variables by aggregating all weeks commencing in a particular month to that month.
-  We remove all values for years with less than 10 data points.
-  We remove all values for time series where the only values are 0 or NA.
-  We do not show data for the most recent 21 days. Data covering the most recent 21 days is often adjusted and updated in the weeks following its release.


## Sources

These are the sources behind the data in this package. Each time series above names the ones it draws on in its citation.

### World Health Organization – FluNet

FluNet is a global web-based tool for influenza virological surveillance first launched in 1997. The virological data entered into FluNet, e.g. number of influenza viruses detected by subtype, are critical for tracking the movement of viruses globally and interpreting the epidemiological data. The data at country level are publicly available and updated weekly. The results are presented in various formats including tables, maps and graphs.

The data are provided remotely by National Influenza Centres (NICs) of the Global Influenza Surveillance and Response System (GISRS) and other national influenza reference laboratories collaborating actively with GISRS, or are uploaded from WHO regional databases.

Producer: World Health Organization  
Published: 2023-02-16  
Retrieved on: 2026-10-17  
Retrieved from: https://www.who.int/tools/flunet  
Direct download: https://xmart-api-public.who.int/FLUMART/VIW_FNT?&$format=csv  
License: CC BY-NC-SA 3.0 IGO (https://www.who.int/about/policies/publishing/copyright)  

Citation: Global Influenza Surveillance and Response System, World Health Organization (2023). FluNet.

    