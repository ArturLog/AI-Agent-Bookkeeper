terraform {
    backend "gcs" {
        bucket = "tf-state-ai-agent-bookkeeper"
        prefix = "terraform"
    }

    required_providers {
        google = {
            source  = "hashicorp/google"
            version = "~> 6.0"
        }
    }
}

provider "google" {
    project                 = var.projectId
    billing_project         = var.projectId
    region                  = var.region
    user_project_override   = true
}