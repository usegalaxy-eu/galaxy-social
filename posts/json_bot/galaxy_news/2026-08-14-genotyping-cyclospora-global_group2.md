---
media:
- bluesky-galaxyproject
- mastodon-galaxyproject
- bluesky-brc
- mastodon-brc
hashtags:
  bluesky-galaxyproject:
  - UseGalaxy
  - GalaxyProject
  bluesky-brc:
  - UseGalaxy
  - GalaxyProject
  mastodon-brc:
  - UseGalaxy
  - GalaxyProject
  mastodon-galaxyproject:
  - UseGalaxy
  - GalaxyProject
---
1st in a 4-part BRC-Analytics series on Cyclospora outbreak analysis: what genomes, genotyping panels and sequencing data exist, and how an independent open implementation of the 8-marker method is built and validated in Galaxy.
https://galaxyproject.org/news/2026-08-14-genotyping-cyclospora/
![Assembly quality across the 49 public C. cayetanensis assemblies. None is chromosome-level and the median assembly is in 1,391 pieces.](https://galaxyproject.org/images/news/2026-08-14-genotyping-cyclospora/figures/genome_quality.png)
![The CDC Cyclospora eight-marker genotyping panel: each amplicon with its primers, SNP count and haplotype-calling windows.](https://galaxyproject.org/images/news/2026-08-14-genotyping-cyclospora/figures/panel_tracks.png)
![Stage-by-stage comparison of the legacy R implementation and PyEuk.](https://galaxyproject.org/images/news/2026-08-14-genotyping-cyclospora/figures/pipeline_compare.png)
![PyEuk's distance and clustering path, from haplotype sheet to outbreak clusters.](https://galaxyproject.org/images/news/2026-08-14-genotyping-cyclospora/figures/distance_path.png)
![The workflow in the Galaxy editor: reads and the reference trio enter on the left, fan out through map_reads, filter_bam, sort_bam and the two callers, then converge through merge_calls and build_sheet into pyeuk, which emits the distance matrix and clusters.](https://galaxyproject.org/images/news/2026-08-14-genotyping-cyclospora/figures/galaxy_workflow_editor.png)
