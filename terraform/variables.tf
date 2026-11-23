variable "aws_region" {
  description = "AWS region for Bedrock and application infrastructure"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project prefix for resource naming"
  type        = string
  default     = "enterprise-rag-bedrock"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "bedrock_chat_model_id" {
  description = "AWS Bedrock cross-region inference profile ID for Claude"
  type        = string
  default     = "us.anthropic.claude-sonnet-4-6"
}

variable "bedrock_embed_model_id" {
  description = "AWS Bedrock embedding model ID"
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "enable_datadog" {
  description = "Set to true when DD_API_KEY and DD_APP_KEY are configured to provision Datadog resources"
  type        = bool
  default     = false
}

variable "enable_rds" {
  description = "Set to true to provision AWS RDS PostgreSQL (db.t4g.micro) for pgvector"
  type        = bool
  default     = false
}
