# AI-Agent-Bookkeeper

## Objective of the project:

Automate monthly bookkeeping for a local business by processing ~30 images of daily sales reports and handwritten employee hour sheets received via Google Drive. Uses AI-powered OCR to digitize data, extract financial metrics and hours worked, aggregate into a structured Google Sheet, and send email notifications with results.

## Initial Project Setup

1. [Create Terraform GCP Project](https://cloud.google.com/resource-manager/docs/creating-managing-projects)

2. [Create Billing Account](https://cloud.google.com/billing/docs/how-to/create-billing-account#create-new-billing-account)

3. [Link Billing Account to the Project](https://cloud.google.com/billing/docs/how-to/modify-project#how-to-enable-billing)

4. [Create Terraform state bucket](https://cloud.google.com/storage/docs/creating-buckets#create-bucket)

```bash
gcloud storage buckets create gs://tf-state-ai-agent-bookkeeper --location=US --project=ai-agent-bookkeeper --uniform-bucket-level-access
```

5. [Enable Cloud Resource Manager API](https://docs.cloud.google.com/service-usage/docs/enable-disable)

```bash
gcloud services enable cloudresourcemanager.googleapis.com --project=ai-agent-bookkeeper
```

## Infrastructure Setup

1. Copy ```example.tfvars``` file and set environment variables

```bash
cp example.tfvars terraform.tfvars
```

2. Init terraform

```bash
terraform init
```

3. Create an execution plan

```bash
terraform plan
```

4. Apply terraform

```bash
terraform apply
```

## Local Testing

1. Grant permission to impersonate as service account

```bash
gcloud iam service-accounts add-iam-policy-binding agent-sa@ai-agent-bookkeeper.iam.gserviceaccount.com 
--member="user:YOUR_EMAIL@gmail.com" 
--role="roles/iam.serviceAccountTokenCreator"
```

2. Login as a service account (wait a while after granting permissions)

```bash
gcloud auth application-default login --impersonate-service-account agent-sa@ai-agent-bookkeeper.iam.gserviceaccount.com
```

3. Create .env file based on example.env file

```bash
cp example.env .env
```

4. Create a virtual environment

```bash
python -m venv .venv
```

5. Activate the virtual environment

```bash
.venv\Scripts\activate
```

6. Install dependencies

```bash
pip install -r requirements.txt
```

7. Run the pipeline

```bash
python main.py
```
