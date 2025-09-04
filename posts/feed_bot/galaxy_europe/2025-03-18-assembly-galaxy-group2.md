---
media:
- bluesky-galaxyproject
mentions:
  bluesky-galaxyproject:
  - galaxyproject.bsky.social
hashtags:
  bluesky-galaxyproject:
  - UseGalaxy
  - GalaxyProject
  - UniFreiburg
  - EOSC
  - EuroScienceGateway
---
📝 New blog post Released!
https://galaxyproject.org/news/2025-03-18-assembly-galaxy/

The field of genomics has been transformed by high-throughput sequencing and computational platforms, with Galaxy emerging as a pivotal resource for genome assembly and annotation. Developed as an open-source, web-based platform, Galaxy facilitates reproducible, scalable, and accessible genomic analyses. Its contributions span tailored tools, involvement in landmark biodiversity projects, innovative quality control developments, and extensive training initiatives.

  

**Tailored tools and workflows for Genome Assembly and Annotation
---------------------------------------------------------------**

Galaxy provides an extensive suite of specialized tools and workflows designed to address the complexities of genome assembly and annotation. For assembly, it integrates state-of-the-art tools such as HiFiasm and Flye for long-read assembly, Canu for error-prone read correction,purge\_dups for haplotype purging and YaHS for Hi-C scaffolding exemplified in workflows developed for Vertebrate Genomes Project (VGP) and ERGA-BGE. These tools support diverse sequencing technologies, including PacBio HiFi and Hi-C, enabling the generation of contiguous, high-quality assemblies with minimal user intervention. Annotation workflows are equally sophisticated, incorporating BRAKER and AUGUSTUS for structural gene prediction, MAKER for evidence-based gene model integration, and InterProScan and eggNOG-mapper for functional annotation. These workflows adhere to community best practices, ensuring comprehensive and reliable genome characterization.

As of March 2025, the Galaxy platform offers approximately 108 distinct tools for genome assembly and 104 tools dedicated to genome annotation related work. All of the tools are consistently updated to align with their latest version releases, ensuring that researchers using Galaxy have access to the most current and optimized versions for their genome assembly and annotation work.

A key strength of Galaxy is its deployment on public servers, eliminating computational barriers and providing computational infrastructure to researchers worldwide. This accessibility empowers institutions with constrained resources to conduct advanced analyses, promoting equity in genomic research. By offering standardized workflows and ensuring reproducibility, Galaxy bolsters the consistency and trustworthiness of genome assemblies and annotations across diverse studies. Furthermore, Galaxy’s proactive allocation of substantial storage capacity supports researchers working on genome assembly and annotation, accommodating datasets that frequently surpass terabytes. As of March 2025, Galaxy has approved additional storage request for 65 applicants working on genome assembly and 32 requests for annotation-related analyses. This dedication not only enhances reproducibility but also broadens participation, enabling diverse institutions to advance genomic science effectively.

  

**Contributions to major genomic initiatives: VGP and ERGA-BGE
------------------------------------------------------------**

Galaxy has played a role in contributing significantly to large-scale biodiversity genomics projects, notably the [Vertebrate Genomes Project (VGP)](https://vertebrategenomesproject.org/) and the [European Reference Genome Atlas (ERGA)](https://www.erga-biodiversity.eu/) within the [Biodiversity Genomics Europe (BGE)](https://biodiversitygenomics.eu/) framework. The VGP leverages Galaxy to produce reference-quality genomes for 74,963 vertebrate species. Its standardized workflows ensure consistency and transparency, with all data and methods openly accessible via public repositories. To cater the demand for generating and curating a large number of genome assemblies, the Galaxy project has created [VGP-Galaxy](https://vgp.usegalaxy.org/), a dedicated Galaxy instance equipped with tailored tools and robust computational resources. As of January 2025, the Vertebrate Genomes Project (VGP) has successfully produced 315 genome assemblies representing 188 species through the VGP-Galaxy platform. All generated genome assemblies have been submitted to [Genome Ark](https://www.genomeark.org/) and are publicly accessible.

Similarly, ERGA, under the BGE initiative, utilizes Galaxy to support the ambitious goal of sequencing approximately 200,000 European eukaryotic species. Aligned with the [Earth BioGenome Project (EBP)](https://www.earthbiogenome.org/) standards, Galaxy’s infrastructure enables the generation of high-quality reference genomes, facilitating biodiversity monitoring and conservation efforts. Additionally, ERGA-BGE researchers have developed specialized workflows using Galaxy, such as the ONT+Illumina & HiC pipeline (NextDenovo-HyPo + Purge\_Dups + YaHS), which are deposited in [WorkflowHub](https://workflowhub.eu/workflows?filter%5Btag%5D=ERGA&filter%5Bworkflow_type%5D=galaxy). These workflows combine Oxford Nanopore long reads, Illumina short reads, and Hi-C data to produce robust assemblies, enhancing the toolkit available to the global research community. These workflows are deposited in WorkflowHub and are planned to be submitted to [IWC Galaxy](https://iwc.galaxyproject.org/) (Intergalactic Workflow Commission Galaxy) for long-term maintenance, updates, and support, ensuring their availability and adaptability for future research.

  

**Development of ERGA EAR and ERGA Bot for the BGE Project
--------------------------------------------------------**

Within the ERGA-BGE collaboration, Galaxy along with its project partners from IZW, have facilitated the development of ERGA EAR and ERGA Bot. The [ERGA Assembly Report (EAR)](https://galaxyproject.org/news/2024-09-19-erga-ear/) is a standardized, community-developed document implemented in Galaxy to evaluate genome assemblies. It incorporates metrics such as contiguity (e.g., N50), gene content completeness via BUSCO analysis, and contamination screening, providing a comprehensive assessment aligned with EBP quality thresholds. This tool enhances transparency and ensures that assemblies meet rigorous scientific standards.

Complementing EAR, the [ERGA Bot](https://galaxyproject.org/news/2026-03-07-erga-bot/) is an automated validation system built using GitHub actions for the BGE project. Designed to streamline quality assurance, it processes assembly reports, identifies anomalies, and enforces consistency across the diverse datasets generated by ERGA’s distributed network. Together, EAR and ERGA Bot represent significant advancements in automating and standardizing genome assembly evaluation, critical for large-scale genomic initiatives.

  

**Training and Workshops: Building capacity in Genomics
-----------------------------------------------------**

Galaxy’s educational initiatives are a cornerstone of its mission to empower researchers to utilize its tools and workflows effectively. Hands-on workshops, such as those offered for the VGP and ERGA assembly pipelines, provide hands-on training in assembling genomes from long-read data and performing post-assembly quality control.
A highlight is the [Galaxy Training Academy](https://training.galaxyproject.org/training-material/events/2025-05-12-galaxy-academy-2025.html), a yearly online event spanning five days, where researchers can immerse themselves in Galaxy’s capabilities with support from trainers and helpers. Hosted by the [Galaxy Training Network](http://training.galaxyproject.org), this event enhances an extensive collection of online tutorials, fostering a proficient, worldwide community well-prepared to utilize Galaxy for advancing genomic research. To support and streamline Galaxy training events, Galaxy offers [TIaaS (Training Infrastructure as a Service)](https://usegalaxy-eu.github.io/tiaas.html) providing free and dedicated computational infrastructure for training purposes. This setup ensures that trainees’ jobs bypass the main queue, running on dedicated resources such as reserved virtual machines (VMs) to reduce wait times and enhance efficiency during workshops. As of March 2025, 75 TIaaS instances have been allocated for assembly and annotation training events.

  

**Broader Implications: FAIR Principles and Future Directions
-----------------------------------------------------------**

Galaxy’s adherence to FAIR principles ensures that its workflows, data, and tools are widely available and reusable. The submission of ERGA-BGE and VGP workflows to WorkflowHub and their preservation on IWC Galaxy exemplifies this commitment, enabling researchers to adopt and adapt these pipelines for diverse applications. Its open-source framework encourages continuous improvement, integrating emerging technologies such as Oxford Nanopore sequencing and refining pipelines as methodologies evolve.

Galaxy stands as a cornerstone in the domain of genome assembly and annotation, offering robust tools, contributing towards biodiversity projects, and fostering innovation through developments like EAR and ERGA Bot. Its training efforts further amplify its impact, building capacity across the scientific community. As genomic research scales to meet global biodiversity and conservation goals, Galaxy’s infrastructure and commitment ensure it remains at the forefront, delivering high-quality, reproducible science. Its ongoing evolution promises to shape the field for years to come.

We gratefully acknowledge the Galaxy Project’s global community—developers, researchers, trainers, and users—who advance genome assembly and annotation through innovative tools, workflows, and training. Moreover we extend our gratitude to Vertebrate Genomes Project (VGP), the European Reference Genome Atlas (ERGA) within Biodiversity Genomics Europe (BGE), the Galaxy Training Network, and countless contributors whose collective efforts drive this significant advancement in genomic science.