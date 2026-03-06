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
    project                 = var.project_id
    billing_project         = var.project_id
    region                  = var.region
    user_project_override   = true
}

resource "google_project_service" "default" {
    project = var.project_id

    for_each = toset([
        "cloudresourcemanager.googleapis.com",
        "serviceusage.googleapis.com",
        "cloudscheduler.googleapis.com",
        "cloudfunctions.googleapis.com",
        "run.googleapis.com",
        "secretmanager.googleapis.com",
        "cloudbuild.googleapis.com",
        "drive.googleapis.com",
        "vision.googleapis.com",
        "storage.googleapis.com",
        "sheets.googleapis.com"
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

# Data Storage Bucket
resource "google_storage_bucket" "data_bucket" {
  name                        = "${var.project_id}-data"
  location                    = var.region
  uniform_bucket_level_access = true
  depends_on                  = [google_project_service.default]
}

# IAM Permissions for Vision and Storage
resource "google_project_iam_member" "agent_vision" {
  project = var.project_id
  role    = "roles/visionai.admin"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
  depends_on = [google_project_service.default]
}

resource "google_storage_bucket_iam_member" "agent_storage_data" {
  bucket = google_storage_bucket.data_bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.agent_sa.email}"
}

# Source Storage Bucket
resource "google_storage_bucket" "source_bucket" {
  name                        = "${var.project_id}-source"
  location                    = var.region
  uniform_bucket_level_access = true
  depends_on                  = [google_project_service.default]
}

data "archive_file" "source_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/function.zip"
}

resource "google_storage_bucket_object" "zip_object" {
  name   = "source-${data.archive_file.source_zip.output_md5}.zip"
  bucket = google_storage_bucket.source_bucket.name
  source = data.archive_file.source_zip.output_path
  depends_on = [google_storage_bucket.source_bucket]
}

# Cloud Function
resource "google_cloudfunctions2_function" "reminder_function" {
  name        = "monthly-ingestion"
  location    = var.region
  description = "Monthly ingestion pipeline"

  build_config {
    runtime     = "python311"
    entry_point = "main_handler"
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
      SMTP_SERVER            = var.agent_smtp_server
      SMTP_PORT              = var.agent_smtp_port
      SENDER_EMAIL           = var.agent_email
      RECEIVER_EMAIL         = var.email_receiver
      DATA_BUCKET            = google_storage_bucket.data_bucket.name
      GOOGLE_DRIVE_FOLDER_ID = var.google_drive_folder_id
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

resource "google_cloud_run_service_iam_member" "invoker_permission" {
  location = google_cloudfunctions2_function.reminder_function.location
  service  = google_cloudfunctions2_function.reminder_function.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.agent_sa.email}"
}

# Cloud Scheduler
resource "google_cloud_scheduler_job" "monthly_trigger" {
  name             = "monthly-reminder-trigger"
  description      = "Triggers monthly reminder on 1st of month at 9am"
  schedule         = "0 9 1 * *"
  time_zone        = "America/Chicago"
  attempt_deadline = "320s"

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.reminder_function.service_config[0].uri

    oidc_token {
      service_account_email = google_service_account.agent_sa.email
    }
  }
}
