# Notes on creating a LinkedIn token

## Create an app

Go to https://www.linkedin.com/developers/apps/new and fill out the form. I think you have to provide a logo image and if you have to provide a privacy policy and don't have one available, you can use the Galaxy one: https://usegalaxy.org/static/terms.html

## Here it gets a little fuzzy

(Adding notes here about the process would be good, since I'm retroactively looking at mine.)

You connect the app you created to your company account, then you have to request the `Community Management API`. My recollection is that this is manually reviewed, so it will likely take some time to be approved. You probably have to provide a reason why you want it, which can be as easy as "To allow my group to automate posting low frequency content."

## Generate a token

Once you get API approval, you generate a token by going to this page: 
 https://www.linkedin.com/developers/tools/oauth/token-generator
and then this token has to be added to the repo secrets.

