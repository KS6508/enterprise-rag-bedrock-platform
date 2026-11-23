resource "random_password" "db_password" {
  count            = var.enable_rds ? 1 : 0
  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_secretsmanager_secret" "db_credentials" {
  count                   = var.enable_rds ? 1 : 0
  name                    = "${var.project_name}-${var.environment}-pgvector-creds"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "db_credentials_val" {
  count     = var.enable_rds ? 1 : 0
  secret_id = aws_secretsmanager_secret.db_credentials[0].id
  secret_string = jsonencode({
    username = "ragadmin"
    password = random_password.db_password[0].result
    dbname   = "ragdb"
    host     = aws_db_instance.pgvector[0].address
    port     = 5432
  })
}

resource "aws_db_instance" "pgvector" {
  count                  = var.enable_rds ? 1 : 0
  identifier             = "${var.project_name}-${var.environment}-pgvector"
  engine                 = "postgres"
  engine_version         = "16.4"
  instance_class         = "db.t4g.micro"
  allocated_storage      = 20
  storage_encrypted      = true
  db_name                = "ragdb"
  username               = "ragadmin"
  password               = random_password.db_password[0].result
  publicly_accessible    = false
  skip_final_snapshot    = true
  deletion_protection    = false

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint when enable_rds = true"
  value       = var.enable_rds ? aws_db_instance.pgvector[0].endpoint : "disabled"
}
