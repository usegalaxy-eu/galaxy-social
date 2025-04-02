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
https://galaxyproject.org/news/2025-04-02-elabftw-integration/

[eLabFTW](https://www.elabftw.net/) is a free and open source electronic lab notebook from
[Deltablot](https://www.deltablot.com/about/). It can keep track of experiments, equipment and materials from a research
lab. Each lab can either [host their own installation](https://doc.elabftw.net/#introduction) or go for Deltablot's
[hosted solution](https://www.deltablot.com/elabftw/). A live demo showcasing its features is available [here](https://demo.elabftw.net/).

And from now on, it is integrated with Galaxy! eLabFTW support has been deployed to
[usegalaxy.eu](https://usegalaxy.eu), and the file source will be brought onboard to upstream Galaxy in release 25.0.
This means that files attached to eLabFTW [experiments](https://doc.elabftw.net/user-guide.html#experiments) and
[resources](https://doc.elabftw.net/user-guide.html#resources) can be imported to
[histories](https://training.galaxyproject.org/training-material/topics/galaxy-interface/tutorials/history/tutorial.html)
with just a few clicks. After the analysis is complete, datasets and histories can be exported back as attachments to an
experiment or resource.

Getting started
---------------

Before it can be used, the feature *must be enabled by a Galaxy administrator*. Once enabled, navigate to the *Settings*
page on your eLabFTW server and go to the *API Keys* tab.

![eLabFTW API Keys tab on settings page](https://galaxyproject.org/news/2025-04-02-elabftw-integration/elabftw_api_keys.png)

Generate a new API key and copy it. Choose "Read/Write" permissions to enable both importing and exporting data. "Read
Only" API keys work for importing data to Galaxy, but not for exporting data to eLabFTW.

![Creating a new API key](https://galaxyproject.org/news/2025-04-02-elabftw-integration/elabftw_api_keys_generate.png)

On Galaxy, configure a new eLabFTW file source under user preferences *Manage Your Repositories* > *Create* > *eLabFTW*.

![User preferences](https://galaxyproject.org/news/2025-04-02-elabftw-integration/user_preferences.png)

![Manage Your Repositories](https://galaxyproject.org/news/2025-04-02-elabftw-integration/manage_your_repositories.png)

![Select eLabFTW](https://galaxyproject.org/news/2025-04-02-elabftw-integration/manage_your_repositories_create.png)

Assign a name to your eLabFTW file source, enter the URL to your eLabFTW instance, and enter the API key you just
generated. If you are using a "Read Only" API key, disable the toggle "Allow Galaxy to export data to eLabFTW?".
Click *Create*.

![eLabFTW file source setup on Galaxy](https://galaxyproject.org/news/2025-04-02-elabftw-integration/elabftw_file_source.png)

Importing files to a Galaxy history
-----------------------------------

To import files from eLabFTW to a Galaxy history, click *Upload* on the sidebar and then *Choose remote files*.

![Galay upload tool](https://galaxyproject.org/news/2025-04-02-elabftw-integration/upload_tool.png)

![Remote file sources](https://galaxyproject.org/news/2025-04-02-elabftw-integration/file_sources.png)

After selecting *eLabFTW*, Galaxy shows two folders, one that contains all experiments and another that contains all
resources.

![eLabFTW experiments and resources listed by Galaxy](https://galaxyproject.org/news/2025-04-02-elabftw-integration/elabftw_experiments_and_resources.png)

Inside each, all experiments or resources are listed as folders. Attached files are located within each of the folders.

![Experiments listed by Galaxy](https://galaxyproject.org/news/2025-04-02-elabftw-integration/elabftw_experiments.png)

![Files attached to the microscopy experiment](https://galaxyproject.org/news/2025-04-02-elabftw-integration/elabftw_experiment_microscopy.png)

Exporting histories to eLabFTW
------------------------------

Clicking *Export History to File* under *History options* opens the history export screen. There, select *to remote
file*, choose a name, and finally use the box *Click to select directory* to open the remote file source browser. The
same screen displayed when importing files will be shown, from where you can select a target experiment or resource.

![History export screen](https://galaxyproject.org/news/2025-04-02-elabftw-integration/history_export.png)

Keep in mind that you have to create the experiments and resources themselves on eLabFTW beforehand.

Exporting datasets to eLabFTW
-----------------------------

Individual datasets may also be exported with the help of the
[dataset export](https://usegalaxy.eu/?tool_id=export_remote&version=latest) tool. First, choose the datasets to export
under the *What would you like to export?* section. Then click *Select* under *Directory URI* to open the remote file
source browser, which allows to select the target experiment or resource.

![Dataset export tool](https://galaxyproject.org/news/2025-04-02-elabftw-integration/dataset_export.png)