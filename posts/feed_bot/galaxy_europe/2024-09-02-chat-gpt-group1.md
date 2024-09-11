---
media:
- mastodon-eu-freiburg
- matrix-eu-announce
- linkedin-galaxyproject
mentions:
  mastodon-eu-freiburg:
  - galaxyproject@mstdn.science
hashtags:
  mastodon-eu-freiburg:
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
https://galaxyproject.org/news/2024-09-02-chat-gpt/

Using Large Language Models in complex workflows
------------------------------------------------

The amount of data researchers face is growing daily. Finding ways of tackling the information overflow to get and analyse relevant data effectively is more critical than ever. Large Language Models (LLMs) like GPT can help in this endeavour and (with good prompting) analyse text data flexibly and effectively.
To help do so, [GPT](https://usegalaxy.eu/root?tool_id=chatgpt_openai_api) is now available on [Galaxy](https://usegalaxy.eu/), an open\-source platform for FAIR data analysis. This enables users to incorporate the LLM into more complex, automatable workflows and analyses. Galaxy contains several thousand tools that users can combine in workflows to cover digital analysis without programming skills or expensive hardware. Users can share all steps and results of the analysis according to the FAIR principles, facilitating high reproducibility, transparency and efficient research data management.

Setting up GPT
--------------

To access GPT in Galaxy, create an OpenAI account [here](https://platform.openai.com/signup). If needed, [add API credits](https://platform.openai.com/settings/organization/billing) according to your usage. Go to https://platform.openai.com/api\-keys to “\+Create new secret key”, name it “Galaxy”, and click the green button “create secret key”. Copy this key to add the API into Galaxy.

![OpenAI API key](https://github.com/user-attachments/assets/9424a44d-11e3-4594-bca9-d759c67956bd)

Back in Galaxy, click “User” and then click on “Manage Information”. In the opened window, scroll down to “Your OpenAI API key”. Paste the API key you created on [OpenAI](https://platform.openai.com/api-keys) here and click “save”.

Using GPT in Galaxy
-------------------

Now you are set to use ChatGPT in Galaxy and can choose from different models:

\| Model \| Description \|
\| \-\-\-\-\-\-\-\-\-\-\-\-\- \| \-\-\-\-\-\-\-\-\-\-\-\-\- \|
\| GPT\-4o \| For complex, multi\-step tasks, model with vision capabilities \|
\| GPT\-4o mini \| Affordable and intelligent small model for fast, lightweight tasks, with vision capabilities \|
\| GPT\-4 Turbo and GPT\-4 \| The previous set of high\-intelligence models, Turbo with vision capabilities \|
\| GPT\-3\.5 Turbo \| A fast, inexpensive model for simple tasks \|

You can also combine the ChatGPT tool in Galaxy with the other tools within a more complex workflow:

You could, for example, upload audio and video files from various sources to be automatically converted into text in Galaxy using [Whisper](https://usegalaxy.eu/?tool_id=whisper). After a short cleaning, ChatGPT can summarise the text, as visualised below.

![ChatGPT tool](https://github.com/user-attachments/assets/bd1a82d5-be79-464f-8f57-9fe5487e2abf)

The screenshot shows the integration of ChatGPT as a tool in Galaxy. The panel on the right side, the ‘History’, shows an example workflow. Here, a mp3\-recording from Martin Luther King’s ‘I have a dream’ was converted into text, cleaned, and translated using ChatGPT. The prompt was adapted from [Prompting ChatGPT for Translation](https://doi.org/10.48550/arXiv.2403.00127).

Alternatively, the transcribed audio file could undergo Named Entity Recognition (NER), and the results could be visualised in the next step by other tools, such as [QGIS](https://usegalaxy.eu/root?tool_id=interactive_tool_qgis) directly in Galaxy.

Another application example is the direct retrieval of research data from Zenodo in Galaxy. For example, published interviews can be imported directly and prepared for ChatGPT. Using sentiment analysis, the LLM analyses the interviewees' attitudes, groups them and extracts suitable passages from the material. The output can then be cleaned up with Galaxy’s other text processing tools or in the interactive environment of [Jupyter Notebooks](https://usegalaxy.eu/?tool_id=interactive_tool_jupyter_notebook), which is another tool in Galaxy.

Sharing your analysis and data
------------------------------

The compiled workflow, the individual analysis steps and the data of each sub\-step can be shared and repeated at any time for good scientific practice, simplifying research data management and reinforcing FAIR analysis. With the help of the [Galaxy Training Network](https://training.galaxyproject.org/), users can create an open\-source tutorial generated out of their workflow to explain and share their analysis with other users. For an example, see here:

Curious? What is your use case with GPT in Galaxy going to be?