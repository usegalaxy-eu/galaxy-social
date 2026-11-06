---
media:
  - linkedin-galaxyproject
---
Day one of CSHL Biological Data Science 2026 wraps up tonight with Poster Session I (8:00-10:00pm) — five posters from our Galaxy Project group are up:

HighGen (Poster 52)
Richard Burhans & Anton Nekrutenko (Penn State) built a 218-assembly comparative genomics resource for cannabis on the cs10 reference, with a live UCSC track hub across the CBD/THC synthase gene clusters. Along the way they fixed real bugs in decades-old alignment tools: a 32-bit score overflow in MULTIZ (now 33.8x faster) and a masking-bias problem that was hiding real sequence.
Poster PDF: https://github.com/nekrut/cshl-meetings/blob/main/2026/biological-data-science/burhans/cannabis-poster.pdf

Orbit + Galaxy User-Defined Tools (Poster 54)
Dannon Baker, Scott Cain and colleagues paired an AI analysis agent (Orbit) with Galaxy's User-Defined Tools to reproduce five published genomics studies from raw reads, building 67+ custom tools as versioned, containerized Galaxy jobs instead of one-off notebook scripts. Nothing runs, and nothing enters the record, until the researcher approves it — twice.
Poster PDF: https://github.com/nekrut/cshl-meetings/blob/main/2026/biological-data-science/cain/orbit-poster.pdf

From research code to reproducible infrastructure with Galaxy user-defined tools (Poster 61)
Marius van den Beek, John Chilton and Dannon Baker show how a Galaxy UDT turns a script into a reusable tool — interface, environment, data, compute, provenance and sharing, in about 40 lines, in your own account, with no admin install queue. Safe by construction: sandboxed expressions, a mandatory container, typed and validated inputs before a job exists.
Poster PDF: https://github.com/nekrut/cshl-meetings/blob/main/2026/biological-data-science/vandenbeek/udt-poster.pdf

Build better skills. Build better workflows. Keep the receipts. (Poster 62)
John Chilton and colleagues built the Galaxy Workflow Foundry, a reviewable knowledge base compiled into agent skills so coding agents can turn a paper into a native, tested Galaxy workflow — programs, not the model, decide when it's right. In a real test on the DengueSeq paper, all seven pinned tool steps validated cleanly and all seven jobs passed real testing.
Poster PDF: https://github.com/nekrut/cshl-meetings/blob/main/2026/biological-data-science/chilton/poster.pdf

Resolving both haplotypes of vertebrate genomes through diploid curation with VGP Galaxy workflows (Poster 105)
Delphine Larivière and the Vertebrate Genomes Project team show that dual-haplotype curation in Galaxy, run across 817 curated vertebrate genomes so far, raises median chromosome assignment from 95% to 97% vs. single-haplotype curation, while recovering phased pseudoautosomal regions single curation mostly misses.
Poster PDF: https://github.com/nekrut/cshl-meetings/blob/main/2026/biological-data-science/dlariviere/poster.pdf

Come find us at Poster Session I tonight.

#CSHLdata26 #BiologicalDataScience #Galaxy #OpenScience #Bioinformatics #ReproducibleResearch
