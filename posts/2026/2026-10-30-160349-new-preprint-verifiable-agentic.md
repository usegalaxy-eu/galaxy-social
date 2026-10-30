---
media:
- linkedin-galaxyproject
---

New preprint: Verifiable Agentic Science on Public Infrastructure

Every analysis run on Galaxy records its tools, parameters, and data. Now we extend that reproducibility trail to AI coding agents, making agent-driven science accessible, transparent, and reproducible for the entire community.

We connected coding agents and the Orbit workbench to public infrastructure—UseGalaxy.org, UseGalaxy.eu, and BRC-Analytics. Agents plan the analysis, Galaxy runs it on free public compute, and every step lands in a history that anyone can open, inspect, and rerun.

What the trail provides:

• Consistency: 30 agents working locally on one Bacillus cereus RNA-seq study produced 18 different pipelines. On Galaxy, a single validated workflow replaced all 26 of their unversioned scripts.
• Early error detection: Pre-execution validation caught an input mismatch and a misapplied aligner before any job launched.
• Auditable findings: Across seven investigations and an eight-model benchmark, full provenance revealed silent subsampling in a published agent benchmark and gene identifiers silently renumbered between genome annotations.

Every workflow, history, and dataset from the study is public. Start with the preprint, then open the histories and inspect them yourself.

Read the preprint on bioRxiv: https://www.biorxiv.org/content/10.64898/2026.10.26.761864v1

#UseGalaxy #OpenScience #Bioinformatics #Reproducibility #AgenticAI

![Architecture diagram: an Agent (Orbit, OpenCode, Claude Code, Codex, Agy) links via MCP Server and Skills to public cyberinfrastructure (storage, CPUs, GPUs), which connects to Tools/Data and a UI for validation and provenance.](https://raw.githubusercontent.com/usegalaxy-eu/galaxy-social/46c92d3e1221e82c9e32443c4c1026fe3909f5c6/posts/images/2026-10-30-160349-new-preprint-verifiable-agentic-screenshot-2026-10-30-at-11.56.38-am.png)
![Sankey diagram of 30 RNA-seq analysis plans from Claude Opus 5.5, Codex (GPT-6 Astra) and Gemini 3.8 Flash, showing plans diverging at every step from reference genome to LFC shrinkage, with major forks in genome choice and DE model scope.](https://raw.githubusercontent.com/usegalaxy-eu/galaxy-social/06c276028fed298992dc86d93b80d0d234154090/posts/images/2026-10-30-160349-new-preprint-verifiable-agentic-screenshot-2026-10-30-at-11.56.08-am.png)
