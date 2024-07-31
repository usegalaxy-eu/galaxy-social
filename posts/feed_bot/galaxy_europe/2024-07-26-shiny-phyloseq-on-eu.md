---
media:
- mastodon-eu-freiburg
- matrix-eu-announce
- bluesky-galaxyproject
- linkedin-galaxyproject
mentions:
  mastodon-eu-freiburg:
  - galaxyproject@mstdn.science
  bluesky-galaxyproject:
  - galaxyproject.bsky.social
  matrix-eu-announce:
  - bgruening:matrix.org
hashtags:
  mastodon-eu-freiburg:
  - UseGalaxy
  - GalaxyProject
  - UniFreiburg
  - EOSC
  - EuroScienceGateway
  bluesky-galaxyproject:
  - UseGalaxy
  - GalaxyProject
  - UniFreiburg
  - EOSC
  - EuroScienceGateway
  linkedin-galaxyproject:
  - UseGalaxy
  - GalaxyProject
  - UniFreiburg
  - EOSC
  - EuroScienceGateway
---
📝 New blog post Released!
https://galaxyproject.org/news/2024-07-26-shiny-phyloseq-on-eu/


Shiny phyloseq interactive tool (IT)
====================================

![Demo of the new shiny phyloseq interactive tool running on Galaxy Europe](https://galaxyproject.org/news/2024-07-26-shiny-phyloseq-on-eu/alpha-div.gif)
[Shiny apps](https://shiny.posit.co/) are web apps using R functionality, that give easy responsive access to R packages.
Interactive tools are a great way to work with data interactively and responsive using Galaxy.


In theory all shiny apps could become ITs, but so far the wrapping and deployment of shiny apps as ITs was technically challenging. To facilitate the integration of Shiny apps as ITs, the Freiburg Galaxy team conducted a two-day hackathon in February, collaborating with members from the Bioconductor community, including Charlotte Soneson, Hans-Rudolf Hotz, and Federico Marini.


During the event, best practices for developing ITs using Shiny apps were established, with a primary focus on creating a Docker image that can serve as a starting point for adding any Shiny app.
As a proof-of-concept the [shiny-phyloseq app](https://github.com/joey711/shiny-phyloseq) has been wrapped as IT.


A fork of this Docker image tailored for the shiny app is available here: https://github.com/paulzierep/docker-phyloseq.
The image can be run locally to test the app and then must be deployed to [quay.io](https://quay.io) or any other Docker registry.


This app allows to perform dynamic analysis of
metabarcoding/amplicon data such as:

* filter data based on metadata and taxonomy
* plot alpha diversity
* plot distance networks
![Network](https://galaxyproject.org/news/2024-07-26-shiny-phyloseq-on-eu/Network.png)

* ordination plots
![Ordination](https://galaxyproject.org/news/2024-07-26-shiny-phyloseq-on-eu/Ordination.png)

* heatmaps
![Heatmap](https://galaxyproject.org/news/2024-07-26-shiny-phyloseq-on-eu/Heatmap.png)

* trees
![Tree](https://galaxyproject.org/news/2024-07-26-shiny-phyloseq-on-eu/Tree.png)

* scatter plots
* bar charts
![Barplot](https://galaxyproject.org/news/2024-07-26-shiny-phyloseq-on-eu/Barplot.png)


The tool is available on usegalaxy.eu (https://usegalaxy.eu/?tool\_id\=interactive\_tool\_phyloseq\&version\=latest) and was integrated into a [dada2 based GTN tutorial](https://training.galaxyproject.org/training-material/topics/microbiome/tutorials/dada-16S/tutorial.html) by Bérénice Batut.


Data upload from Galaxy
-----------------------

The IT worked with the original shiny\-phyloseq app, but the app did not allow to upload amplicon data via CLI arguments making data input from Galaxy incovenient (requiring users to download data from their Galaxy History, then upload it to the IT via the web frontend).


Therefore, the tool was forked and modified to allow for additional data input. This functional adaptation of shiny\-apps to allow for non\-web based data upload is the only requirement to make any shiny app compatible with Galaxy based data upload.


The changes made to the original app can be found in this [git diff](https://github.com/joey711/shiny-phyloseq/compare/master...paulzierep:shiny-phyloseq:master).


Outlook
-------

To improve the usability and Galaxy\-interaction of the phyloseq\-shiny app we are working on the possibility to export data (figures, modified phyloseq objects) to the Galaxy history.


This could be done either by collecting the data as outputs of the IT or by using utility functions such as put / get, that are used in other ITs like [RStudio](https://usegalaxy.eu/?tool_id=interactive_tool_rstudio&version=latest).
