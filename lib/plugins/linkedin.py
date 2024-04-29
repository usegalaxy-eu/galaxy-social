# this file is not working! It is just a template for the final implementation...
import requests


class linkedin_client:
    def __init__(
        self, access_token=None, api_base_url="https://api.linkedin.com/rest/"
    ):
        self.api_base_url = api_base_url
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202403",
        }

    def linkedin_post(self, content):
        url = self.api_base_url + "posts"
        data = {
            "author": "urn:li:organization:5515715",
            "commentary": content,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        response = requests.post(url, headers=self.headers, json=data)
        return response.json()

    def get_profile(self):
        url = self.api_base_url + "people/~"
        response = requests.get(url, headers=self.headers)
        return response.json()

    # This method is not implemented
    def create_post(self, content):
        self.linkedin_post(content)
        return True
        linkedin_posts = self.get_profile()
        for post in linkedin_posts["posts"]["values"]:
            if content in post["commentary"]:
                return True
        return False
