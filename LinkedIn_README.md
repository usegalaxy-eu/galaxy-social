# LinkedIn API Token Setup
You need to [set up a company](https://www.linkedin.com/company/setup/new/) before get started.

## 1. Create a LinkedIn Developer App  

- Go to [Create a LinkedIn App](https://www.linkedin.com/developers/apps/new) and fill in the required fields.  
- Upload a logo. If a privacy policy is needed, use [this one](https://usegalaxy.org/static/terms.html).  
- In **Settings**, click **Verify** next to your company name and complete the verification.  

## 2. Request API Access  

- In **Products**, find **Community Management API** and click **Request Access**.  
- Provide a reason (e.g., "Automate low-frequency posting on our company page").  
- Wait for manual approval.  

## 3. Generate & Secure the Token  

- After approval, visit the [Token Generator](https://www.linkedin.com/developers/tools/oauth/token-generator).  
- Select your app, choose the required scopes (w_organization_social, w_organization_social_feed), and generate the token.  
- Store the Access token securely in repo secrets.

**Note**: Tokens expire every 2 months

## 4. Get Your LinkedIn Company ID  

- Go to your **LinkedIn Company Page**.  
- Look at the URL: `https://www.linkedin.com/company/{YOUR_COMPANY_ID}`.  
- Copy the number after `/company/`—this is your **Company ID**.
- Add this into the [plugins file](https://github.com/usegalaxy-eu/galaxy-social/blob/main/plugins.yml) as the `org_id`.

