resource "random_password" "db" {
  length  = 24
  special = false
}

resource "aws_security_group" "postgres" {
  name        = "${var.project_name}-postgres"
  description = "PostgreSQL access from EKS nodes"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "PostgreSQL from VPC"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["192.168.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-postgres", Project = var.project_name }
}

resource "aws_db_subnet_group" "postgres" {
  name       = "${var.project_name}-postgres"
  subnet_ids = module.vpc.public_subnet_ids

  tags = { Name = "${var.project_name}-postgres", Project = var.project_name }
}

resource "aws_db_instance" "postgres" {
  identifier                 = "${var.project_name}-postgres"
  engine                     = "postgres"
  engine_version             = "16"
  instance_class             = var.db_instance_class
  allocated_storage          = 20
  storage_type               = "gp3"
  db_name                    = "debugpilot"
  username                   = "debugpilot"
  password                   = random_password.db.result
  db_subnet_group_name       = aws_db_subnet_group.postgres.name
  vpc_security_group_ids     = [aws_security_group.postgres.id]
  publicly_accessible        = false
  skip_final_snapshot        = var.db_skip_final_snapshot
  backup_retention_period    = 1
  deletion_protection        = var.db_deletion_protection
  auto_minor_version_upgrade = true

  tags = { Name = "${var.project_name}-postgres", Project = var.project_name }

  lifecycle {
    prevent_destroy = true
  }
}

locals {
  database_url = "postgresql+psycopg2://${aws_db_instance.postgres.username}:${urlencode(random_password.db.result)}@${aws_db_instance.postgres.address}:${aws_db_instance.postgres.port}/${aws_db_instance.postgres.db_name}"
}

output "database_host" {
  value = aws_db_instance.postgres.address
}

output "database_url" {
  value     = local.database_url
  sensitive = true
}
