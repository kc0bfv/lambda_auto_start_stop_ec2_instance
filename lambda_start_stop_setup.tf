terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.70"
    }
  }
}

provider "aws" {
  region  = var.region
}

# Create the function role and policy, and attach them
resource "aws_iam_role" "role" {
  name               = join("_", [var.environ_tag, "starter_role"])
  description        = "Lambda role allows it to start an inst and log"
  assume_role_policy = templatefile("templates/role", {})

  tags = { Environment = var.environ_tag }
}
resource "aws_iam_policy" "policy" {
  name        = join("_", [var.environ_tag, "starter_policy"])
  description = "This policy gives the function permission to send logs"
  path        = "/"
  policy = templatefile("templates/policy",
    {
      region        = var.region,
      instance      = var.instance,
      loggroup_name = join("_", [var.environ_tag, "starter"])
    }
  )

  tags = { Environment = var.environ_tag }
}
resource "aws_iam_role_policy_attachment" "policy_atch" {
  role       = aws_iam_role.role.name
  policy_arn = aws_iam_policy.policy.arn
}

resource "aws_lambda_function" "function" {
  description   = "Start the server"
  function_name = join("_", [var.environ_tag, "function"])
  role          = aws_iam_role.role.arn
  handler       = "manage_instance.main"
  runtime       = "python3.9"

  filename         = "manage_instance.zip"
  source_code_hash = filebase64sha256("manage_instance.zip")

  environment {
    variables = {
      REGION          = var.region
      INSTANCE        = var.instance
      BASE_START_TIME = var.base_start_time
      RUN_TIME        = var.run_time
      RATE            = var.rate
    }
  }

  tags = { Environment = var.environ_tag }
}

# Setup the EventBridge rule and attach it to the function
resource "aws_cloudwatch_event_rule" "event_rule" {
  name                = join("_", [var.environ_tag, "_event_rule"])
  description         = "Run and stop a server"
  schedule_expression = var.eventbridge_expression

  tags = { Environment = var.environ_tag }
}
resource "aws_cloudwatch_event_target" "event_target" {
  # Associate the event rule with the function
  rule = aws_cloudwatch_event_rule.event_rule.name
  arn  = aws_lambda_function.function.arn
}
resource "aws_lambda_permission" "monitor_perms" {
  # This permission lets EventBridge run the lambda
  statement_id  = "AllowEventBridgeExecution"
  action        = "lambda:InvokeFunction"
  principal     = "events.amazonaws.com"
  function_name = aws_lambda_function.function.function_name
  source_arn    = aws_cloudwatch_event_rule.event_rule.arn
}
