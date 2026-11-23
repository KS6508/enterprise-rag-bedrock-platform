variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "enterprise-rag-bedrock"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "bedrock_chat_model_id" {
  type    = string
  default = "us.anthropic.claude-sonnet-4-6"
}

variable "bedrock_embed_model_id" {
  type    = string
  default = "amazon.titan-embed-text-v2:0"
}

variable "enable_datadog" {
  type    = bool
  default = false
}
