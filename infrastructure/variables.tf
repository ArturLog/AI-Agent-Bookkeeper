variable "project_id" {
    type        = string
}

variable "region" {
    type        = string
    default     = "us-central1"
}

variable "agent_email" {
  type          = string
}

variable "agent_email_password" {
  type          = string
  sensitive     = true
}

variable "agent_smtp_server" {
  type          = string
}

variable "agent_smtp_port" {
  type          = string
}

variable "email_receiver" {
  type          = string
}

variable "google_drive_folder_id" {
  type          = string
}

variable "spreadsheet_id" {
  type          = string
}

variable "gemini_api_key" {
  type          = string
  sensitive     = true
  description   = "Google Gemini API key for LLM analysis"
}