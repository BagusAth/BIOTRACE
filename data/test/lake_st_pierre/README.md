# eDNA metabarcoding to monitor fish communities in a large river floodplain

Dataset DOI: [10.5061/dryad.3bk3j9kzf](10.5061/dryad.3bk3j9kzf)

## Description of the data and file structure

The data were collected as part of an experimental and field-based study comparing fish community composition assessed through environmental DNA (eDNA) metabarcoding and electrofishing surveys across a large river floodplain. Sampling included the collection of water samples for eDNA extraction and sequencing, concurrent electrofishing surveys for comparison, and the recording of environmental variables to evaluate potential drivers of community variation.

### Files and variables

#### File: edna_env.csv

**Description:** Environmental variables associated with eDNA samples.

##### Variables

* station: Sampling sites code names
* year: Year of sampling
* landuse: Land use at the sampling sites
* manag: Land management at the sampling site
* region: Sector the sampling sites are located into
* Date: Sampling date
* UTM_X: UTM geographical cootdinates
* UTM_Y: UTM geographical cootdinates
* Turbidity: Water turbidity recorded at sampling site (FNU)
* Water_Level: Water level at each sampling site was modeled as the difference between GPS-derived altitude and modeled water level, with negative values indicating that water covered the site (i.e., water level above GPS altitude)
* Mean_NDVI: Mean Normalized Difference Vegetation Index (NDVI) values at each sampling site for the year preceding sampling

#### File: elec_env.csv

**Description:** Environmental variables associated with electrofishing samples.

##### Variables

* station: Sampling sites code names
* year: Year of sampling
* landuse: Land use at the sampling sites
* region: Sector the sampling sites are located into
* Date: Sampling date
* UTM_X: UTM geographical cootdinates
* UTM_Y: UTM geographical cootdinates
* Turbidity: Water turbidity recorded at sampling site (FNU)
* Water_Level: Water level at each sampling site was modeled as the difference between GPS-derived altitude and modeled water level, with negative values indicating that water covered the site (i.e., water level above GPS altitude).
* Mean_NDVI: Mean Normalized Difference Vegetation Index (NDVI) values at each sampling site for the year preceding sampling

#### File: edna_lg_clean.csv

**Description:** A long format fish abundance table derived from eDNA sampling after bioinformatic processing

##### Variables

* site: Sampling sites code names
* round: In 2022, two sampling rounds were conducted; this variable indicates the corresponding sampling round.
* region: Sector the sampling sites are located into
* landuse: Land use at the sampling sites
* year: Year of sampling
* CODE_BDRSI: Fish species codes
* count: Number of sequence
* rel_ab: Relative number of sequence at each site and dates

#### File: elec_long.csv

**Description:** A long format fish abundance table derived from electrofiching sampling

##### Variables

* station: Sampling sites code names
* year: Year of sampling
* CODE_BDRSI: Fish species codes
* count: Abundance
* rel_ab: Relative abundance at each site and dates

#### File: fish_codes.csv

**Description:** Species names associated with fish species codes

##### Variables

* Family:
* Genus:
* Species:
* CODE_BDRSI: Fish species codes

#### File: raw_seq.zip

**Description:** Raw sequences derived from Illumina sequencing. One forder for each sampling year. File names contain information as follows:

* 2019: filter-site code-year-marker_illumina ids_R1 or R2_001.fastq.gz
* 2022: marker-site code-round of samplingfilter_illumina ids_R1 or R2_001.fastq.gz

