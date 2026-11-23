terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
    datadog = {
      source  = "DataDog/datadog"
      version = "~> 3.45"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

provider "datadog" {
  validate = var.enable_datadog
}

data "aws_caller_identity" "current" {}

resource "aws_secretsmanager_secret" "datadog_api_key" {
  name                    = "${var.project_name}-${var.environment}-dd-api-key"
  recovery_window_in_days = 0
}

resource "aws_ecr_repository" "rag_api" {
  name                 = "${var.project_name}-api"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  image_scanning_configuration { scan_on_push = true }
}

resource "aws_iam_role" "rag_service_role" {
  name = "${var.project_name}-${var.environment}-service-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = ["ecs-tasks.amazonaws.com", "tasks.apprunner.amazonaws.com"] }
    }]
  })
}

resource "aws_iam_role_policy" "bedrock_least_privilege" {
  name = "${var.project_name}-bedrock-access"
  role = aws_iam_role.rag_service_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowBedrockInference"
        Effect = "Allow"
        Action = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
        Resource = [
          "arn:aws:bedrock:*::foundation-model/anthropic.*",
          "arn:aws:bedrock:*:${data.aws_caller_identity.current.account_id}:inference-profile/*",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/${var.bedrock_embed_model_id}"
        ]
      },
      {
        Sid      = "AllowReadDatadogSecret"
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [aws_secretsmanager_secret.datadog_api_key.arn]
      }
    ]
  })
}
