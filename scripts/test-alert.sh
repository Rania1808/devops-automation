#!/bin/bash

# Script pour tester manuellement une alerte

ALERTMANAGER_URL="http://localhost:9093"

echo "🧪 Sending test alert to AlertManager..."

curl -XPOST "$ALERTMANAGER_URL/api/v1/alerts" -d '[
  {
    "labels": {
      "alertname": "TestAlert",
      "instance": "test-instance:9100",
      "severity": "critical",
      "component": "test"
    },
    "annotations": {
      "summary": "This is a test alert",
      "description": "Testing the alert pipeline from Prometheus to Slack"
    },
    "startsAt": "'$(date -u +%Y-%m-%dT%H:%M:%S.000Z)'",
    "endsAt": "'$(date -u -d '+1 hour' +%Y-%m-%dT%H:%M:%S.000Z)'"
  }
]'

echo ""
echo "✅ Test alert sent! Check your Slack channel."
