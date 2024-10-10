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
https://galaxyproject.org/news/2024-10-09-esg-w-p5-nobug-s2024/

*Patrick Austin* from Science and Technology Facilities Council (STFC, UKRI) and *Leandro Liborio* from Scientific Computing Department, STFC, UKRI, UK presented the Galaxy platform and the analysis of X\-ray Absorption Spectroscopy (XAS) at the NOBUGS 2024 conference at the ILL \& ESRF conference in Grenoble, 23\-24 September 2024

[Link to the video with the NOBUGS presentation](https://vimeo.com/1016435799/e892312d63)

[Link to the site with synopsis](https://indico.esrf.fr/event/114/contributions/775/)

*Primary Authors*

Leandro Liborio (Scientific Computing Department, STFC, UKRI, UK)

Patrick Austin (Science and Technology Facilities Council (STFC, UKRI))

Mr Subindev Devadasan (Science and Technology Facilities Council (STFC, UKRI))

*Co\-authors*

Dr Abraham Nieva de la Hidalga (Cardiff University)

Mr Alexander Belozerov (Science and Technology Facilities Council (STFC, UKRI))

Mr Tom Underwood (Science and Technology Facilities Council (STFC, UKRI))

With FAIR principles increasing in importance within many fields, the challenge of ensuring that these principles are fully embedded in research outputs applies not just to the (meta)data itself, but also to the methods used to process and analyse it. If metadata associated with the raw data is lost in the analysis process, the Findability (which relies on this metadata) may be compromised. If the parameters used in the analysis of the data, and the information about data provenance, are not recorded, then Reusability can be seriously compromised.

To address these challenges, at the Science and Technologies Facilities Council (STFC) in the UK, we have begun using the open source Galaxy web platform for workflow management. Galaxy offers a number of features that directly relate to ensuring that outputs retain all metadata needed for them to be reproduced: histories store the data and parameter inputs associated with all output data, software tools are strictly versioned and run in containers, and executions of workflows can be exported as Research Object Crates. Beyond this it also offers advantages, such as a supportive community of developers and users, a platform for hosting associated training materials and a system for job execution which supports multiple scalable options for compute resources whilst not requiring users to have any knowledge of the underlying submission system.

In particular, we have been developing Galaxy tool interfaces for the Larch library of tools for analysis of X\-ray Absorption Spectroscopy (XAS) data, which enable the creation of workflows for performing near edge and extended fine structure analysis of data gathered at the Diamond Light Source in the UK. To direct development and provide a trial use case, in collaboration with the UK Catalysis Hub, we have attempted to reproduce results from papers published in this field. This example has helped us expose the challenges of reusing data when a system such as Galaxy is not employed to standardise analysis and capture all the required parameters. We are aiming to lower the barrier to entry for this kind of workflow to encourage more users to do it for their own data, where again the Galaxy platform can offer an advantage.

In this talk we will present the results of this effort, aiming to show the work required to bring Galaxy to a new domain and what the challenges and benefits of this are.