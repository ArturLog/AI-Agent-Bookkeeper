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
    project = var.project_id

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

# Service Account
resource "google_service_account" "agent_sa" {
  account_id   = "agent-sa"
  display_name = "AI Agent Service Account"
}

# Secret Manager
resource "google_secret_manager_secret" "agent_email_password" {
  secret_id = "agent_email_password"

  replication {
    auto {}
  }

  depends_on = [google_project_service.default]
}

resource "google_secret_manager_secret_version" "agent_email_password_version" {
  secret        = google_secret_manager_secret.agent_email_password.id
  secret_data   = var.agent_email_password
}

resource "google_secret_manager_secret_iam_member" "agent_secret_access" {
  secret_id = google_secret_manager_secret.agent_email_password.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent_sa.email}"
}

# Cloud Bucket
resource "google_storage_bucket" "source_bucket" {
  name                        = "${var.project_id}-source"
  location                    = "US"
  uniform_bucket_level_access = true
}

data "archive_file" "source_zip" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/function.zip"
}

resource "google_storage_bucket_object" "zip_object" {
  name   = "source-${data.archive_file.source_zip.output_md5}.zip"
  bucket = google_storage_bucket.source_bucket.name
  source = data.archive_file.source_zip.output_path
}

# Cloud Function
resource "google_cloudfunctions2_function" "reminder_function" {
  name        = "monthly-reminder"
  location    = var.region
  description = "Sends monthly email reminder to the user"

  build_config {
    runtime     = "python311"
    entry_point = "send_monthly_reminder"
    source {
      storage_source {
        bucket = google_storage_bucket.source_bucket.name
        object = google_storage_bucket_object.zip_object.name
      }
    }
  }

  service_config {
    max_instance_count = 1
    available_memory   = "256M"
    timeout_seconds    = 60
    service_account_email = google_service_account.agent_sa.email

    environment_variables = {
      SMTP_SERVER    = var.smtp_server
      SMTP_PORT      = var.smtp_port
      SENDER_EMAIL   = var.email_sender
      RECEIVER_EMAIL = var.email_receiver
    }

    secret_environment_variables {
      key        = "EMAIL_PASSWORD"
      project_id = var.project_id
      secret     = google_secret_manager_secret.agent_email_password.secret_id
      version    = "latest"
    }
  }
  depends_on = [google_project_service.default]
}

# Cloud Scheduler
resource "google_cloud_scheduler_job" "monthly_trigger" {
  name             = "monthly-reminder-trigger"
  description      = "Triggers monthly reminder on 1st of month at 9am"
  schedule         = "0 9 1 * *"
  time_zone        = "America/Central"
  attempt_deadline = "320s"

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.reminder_function.service_config[0].uri

    oidc_token {
      service_account_email = google_service_account.agent_sa.email
    }
  }
}
