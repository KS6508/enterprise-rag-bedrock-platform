resource "datadog_monitor" "llm_high_latency" {
  count   = var.enable_datadog ? 1 : 0
  name    = "[${var.project_name}] High Bedrock RAG Latency (p95 > 4s)"
  type    = "metric alert"
  message = "Bedrock RAG endpoint p95 latency exceeded 4000ms."
  query   = "avg(last_5m):p95:llm.latency.ms{env:${var.environment}} > 4000"
  monitor_thresholds { critical = 4000; warning = 2500 }
  notify_no_data = false
}

resource "datadog_dashboard" "ai_observability" {
  count       = var.enable_datadog ? 1 : 0
  title       = "Enterprise Bedrock RAG - AI & Infra Observability (${var.environment})"
  layout_type = "ordered"
  widget {
    timeseries_definition {
      title = "LLM Token Usage (Input vs Output)"
      request { q = "sum:llm.tokens.input{env:${var.environment}} by {model}.as_count()"; display_type = "bars" }
      request { q = "sum:llm.tokens.output{env:${var.environment}} by {model}.as_count()"; display_type = "bars" }
    }
  }
}
