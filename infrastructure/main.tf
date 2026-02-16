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

resource "google_project_service" "default" {
    project = var.projectId

    for_each = toset([
        "cloudscheduler.googleapis.com",
        "cloudfunctions.googleapis.com",
        "run.googleapis.com",
        "secretmanager.googleapis.com",
        "cloudbuild.googleapis.com"
    ])

    service = each.key
    disable_on_destroy = false
}