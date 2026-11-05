---
media:
  - mastodon-galaxyproject
---
Six posters from the Galaxy Project team are up this week at CSHL Biological Data Science 2026 (Nov 4–7) in Cold Spring Harbor, NY. Topics range from AI-agent-driven reanalysis and Galaxy user-defined tools to workflow automation, cannabis comparative genomics, diploid vertebrate genome assembly, and planetary-scale sequence mining from the SRA. We'll post each one with its poster PDF over the next few days — follow along with #CSHLdata26.


HighGen (Poster 52): comparative genomics resources for cannabis. Richard Burhans & Anton Nekrutenko (Penn State) built a 218-assembly comparative genomics resource for Cannabis sativa on the cs10 reference, with a live UCSC track hub across the CBD/THC synthase gene clusters. Along the way: a real 32-bit score overflow fixed in MULTIZ (33.8x faster) and a masking-bias fix that recovered hidden sequence. https://github.com/nekrut/cshl-meetings/blob/main/2026/biological-data-science/burhans/cannabis-poster.pdf #CSHLdata26 #BiologicalDataScience


Orbit + Galaxy User-Defined Tools (Poster 54) for reproducible, auditable computational biology. Dannon Baker, Scott Cain, et al. paired an AI analysis agent (Orbit) with Galaxy UDTs to reproduce 5 published genomics studies from raw reads — building 67+ custom tools as containerized, versioned Galaxy jobs instead of one-off notebook scripts. Nothing runs, and nothing enters the record, until the researcher approves it twice. https://github.com/nekrut/cshl-meetings/blob/main/2026/biological-data-science/cain/orbit-poster.pdf #CSHLdata26 #BiologicalDataScience


Build better skills. Build better workflows. Keep the receipts. (Poster 62) John Chilton et al. built the Galaxy Workflow Foundry: a reviewable wiki of notes compiled into agent skills, so coding agents turn a paper into a native, tested Galaxy workflow — programs, not the model, decide when it's right. DengueSeq test run: all 7 pinned tool steps validated clean, all 7 jobs passed real Planemo testing. https://github.com/nekrut/cshl-meetings/blob/main/2026/biological-data-science/chilton/poster.pdf #CSHLdata26


Resolving both haplotypes of vertebrate genomes with VGP Galaxy workflows (Poster 105). Delphine Larivière et al. (Vertebrate Genomes Project) show that dual-haplotype curation in Galaxy, run across 817 curated vertebrate genomes so far, raises median chromosome assignment from 95% to 97% vs. single-haplotype curation, while recovering phased pseudoautosomal regions single curation mostly misses (54/64 vs 1/107). https://github.com/nekrut/cshl-meetings/blob/main/2026/biological-data-science/dlariviere/poster.pdf #CSHLdata26 #BiologicalDataScience


disassembler: planetary-scale sequence extraction from Logan (Poster 159). Andrew Seacord et al. built two complementary tools — a graph path-walker and a streaming contig assembler — to pull target sequences out of Logan's petabase SRA index, no reference pipeline needed. On SARS-CoV-2 spike: 4.99M Logan runs scanned, contamination cut from 0.555% to 0%, and a selection scan across 161 haplotypes flagged escape site E484K in 29.5s. https://github.com/nekrut/cshl-meetings/blob/main/2026/biological-data-science/seacord/poster.pdf #CSHLdata26


From research code to reproducible infrastructure with Galaxy user-defined tools (Poster 61). Marius van den Beek, John Chilton & Dannon Baker show how a Galaxy UDT covers interface, environment, data, compute, provenance and sharing in ~40 lines, in your own account, no admin queue. Safe by construction: sandboxed expressions, a mandatory container, typed and validated inputs before a job exists. https://github.com/nekrut/cshl-meetings/blob/main/2026/biological-data-science/vandenbeek/udt-poster.pdf #CSHLdata26


Orbit: Reproducible Agentic Workflow Development with Cloud Execution Included (Poster 126, live demo). Anton Nekrutenko, Scott Cain & Dannon Baker demo Orbit itself: a desktop app that plans, runs and publishes full analyses, integrated with Galaxy and NCBI Datasets via MCP servers, running workflows on TACC, Jetstream2 and ACCESS-CI, provider-agnostic across models. Come watch it plan and run a real analysis live. #CSHLdata26
