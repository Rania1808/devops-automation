# DevOps Automation with Prometheus, Ansible & Slack

<img width="1112" height="556" alt="projet-2" src="https://github.com/user-attachments/assets/fe0db1c4-780c-4ff4-8085-c4354c637873" />


[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ansible](https://img.shields.io/badge/Ansible-2.14+-red.svg)](https://www.ansible.com/)
[![Prometheus](https://img.shields.io/badge/Prometheus-2.40+-orange.svg)](https://prometheus.io/)

## 📋 Overview

This project implements a complete DevOps automation architecture that allows you to:
- **Monitor** production servers via Prometheus
- **Detect** performance issues automatically (CPU > 90%)
- **Alert** the team via Slack in real-time
- **Remediate** issues automatically via Ansible

## 🏗️ Architecture

<img width="1300" height="605" alt="prom" src="https://github.com/user-attachments/assets/57a46a39-dc39-402a-98ab-86f616ba1f19" />

### Components

1. **Production Server**: Monitored server with Prometheus exporter
2. **Prometheus Server**: Collects metrics and triggers alerts
3. **Alert Manager**: Manages and groups alerts
4. **Flask Webhook**: Receives alerts and triggers Ansible
5. **Ansible Server**: Executes remediation playbooks
6. **Slack**: Team notifications

## 🚀 Installation

### Prerequisites

- Python 3.8+
- Ansible 2.14+
- Prometheus 2.40+
- AlertManager 0.25+
- SSH access to production servers
- Slack webhook

### 1. Clone the repository

```bash
git clone https://github.com/Rania1808/devops-automation.git
cd devops-automation
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
ANSIBLE_SSH_KEY_PATH=/path/to/ssh/key
PRODUCTION_SERVER_IP=192.168.1.100
FLASK_PORT=5000
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Prometheus

```bash
cp prometheus/prometheus.yml.example prometheus/prometheus.yml
# Edit prometheus.yml with your servers
```

### 5. Configure AlertManager

```bash
cp alertmanager/alertmanager.yml.example alertmanager/alertmanager.yml
# Edit alertmanager.yml with your Flask webhook URL
```

### 6. Configure Ansible

```bash
cp ansible/inventory.example ansible/inventory
# Add your production servers
```

## 📦 Project Structure

```
.
├── README.md
├── .env.example
├── requirements.txt
├── docker-compose.yml
├── prometheus/
│   ├── prometheus.yml
│   ├── rules/
│   │   └── alerts.yml
│   └── Dockerfile
├── alertmanager/
│   ├── alertmanager.yml
│   └── Dockerfile
├── flask-webhook/
│   ├── app.py
│   ├── config.py
│   ├── requirements.txt
│   └── Dockerfile
├── ansible/
│   ├── inventory
│   ├── ansible.cfg
│   ├── playbooks/
│   │   ├── high-cpu-remediation.yml
│   │   ├── restart-services.yml
│   │   └── scale-resources.yml
│   └── roles/
│       ├── monitoring/
│       ├── remediation/
│       └── notification/
└── scripts/
    ├── deploy.sh
    ├── test-alert.sh
    └── backup.sh
```

## 🔧 Detailed Configuration

### Prometheus - Alert Rules

File `prometheus/rules/alerts.yml`:

```yaml
groups:
  - name: production_alerts
    interval: 30s
    rules:
      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 90
        for: 2m
        labels:
          severity: critical
          component: cpu
        annotations:
          summary: "CPU usage is above 90% on {{ $labels.instance }}"
          description: "CPU usage is {{ $value }}% on {{ $labels.instance }}"
```

### AlertManager - Configuration

File `alertmanager/alertmanager.yml`:

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'instance']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'flask-webhook'

receivers:
  - name: 'flask-webhook'
    webhook_configs:
      - url: 'http://flask-webhook:5000/webhook/alert'
        send_resolved: true
```

### Flask Webhook - Application

File `flask-webhook/app.py`:

```python
from flask import Flask, request, jsonify
import subprocess
import requests
import os
from datetime import datetime

app = Flask(__name__)

SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
ANSIBLE_PLAYBOOK_PATH = '/ansible/playbooks'

@app.route('/webhook/alert', methods=['POST'])
def receive_alert():
    data = request.json
    
    # Process alert
    for alert in data.get('alerts', []):
        if alert['status'] == 'firing':
            handle_firing_alert(alert)
        elif alert['status'] == 'resolved':
            handle_resolved_alert(alert)
    
    return jsonify({'status': 'success'}), 200

def handle_firing_alert(alert):
    alert_name = alert['labels'].get('alertname')
    instance = alert['labels'].get('instance')
    
    # Send Slack notification
    send_slack_notification(
        f"🚨 ALERT: {alert_name}",
        f"Instance: {instance}\n{alert['annotations'].get('description')}"
    )
    
    # Trigger Ansible
    if alert_name == 'HighCPUUsage':
        run_ansible_playbook('high-cpu-remediation.yml', instance)

def run_ansible_playbook(playbook, target):
    cmd = [
        'ansible-playbook',
        f'{ANSIBLE_PLAYBOOK_PATH}/{playbook}',
        '-i', '/ansible/inventory',
        '--limit', target,
        '-v'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        send_slack_notification(
            "✅ Ansible Remediation",
            f"Playbook: {playbook}\nTarget: {target}\nStatus: {'Success' if result.returncode == 0 else 'Failed'}"
        )
    except Exception as e:
        send_slack_notification(
            "❌ Ansible Error",
            f"Failed to run {playbook}: {str(e)}"
        )

def send_slack_notification(title, message):
    payload = {
        'text': f"*{title}*\n{message}",
        'username': 'DevOps Bot',
        'icon_emoji': ':robot_face:'
    }
    
    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"Failed to send Slack notification: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### Ansible - Remediation Playbook

File `ansible/playbooks/high-cpu-remediation.yml`:

```yaml
---
- name: High CPU Remediation
  hosts: all
  become: yes
  gather_facts: yes
  
  tasks:
    - name: Identify CPU-intensive processes
      shell: ps aux --sort=-%cpu | head -10
      register: top_processes
      
    - name: Display processes
      debug:
        msg: "{{ top_processes.stdout_lines }}"
    
    - name: Check for failed services
      shell: systemctl list-units --state=failed
      register: failed_services
      
    - name: Restart failed services
      systemd:
        name: "{{ item.split()[1] }}"
        state: restarted
      loop: "{{ failed_services.stdout_lines[1:] }}"
      when: failed_services.stdout_lines | length > 1
      ignore_errors: yes
    
    - name: Clean temporary files
      shell: |
        find /tmp -type f -atime +7 -delete
        find /var/tmp -type f -atime +7 -delete
      ignore_errors: yes
    
    - name: Check disk space
      shell: df -h
      register: disk_space
      
    - name: Restart resource-intensive services if needed
      systemd:
        name: "{{ item }}"
        state: restarted
      loop:
        - apache2
        - nginx
      when: "'apache2' in top_processes.stdout or 'nginx' in top_processes.stdout"
      ignore_errors: yes
    
    - name: Collect post-remediation metrics
      shell: |
        uptime
        free -m
        iostat
      register: post_metrics
      
    - name: Display metrics
      debug:
        msg: "{{ post_metrics.stdout_lines }}"
```

## 🐳 Deployment with Docker

```bash
# Build and start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop services
docker-compose down
```

File `docker-compose.yml`:

```yaml
version: '3.8'

services:
  prometheus:
    build: ./prometheus
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./prometheus/rules:/etc/prometheus/rules
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - monitoring

  alertmanager:
    build: ./alertmanager
    container_name: alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
    networks:
      - monitoring

  flask-webhook:
    build: ./flask-webhook
    container_name: flask-webhook
    ports:
      - "5000:5000"
    volumes:
      - ./ansible:/ansible
      - ~/.ssh:/root/.ssh:ro
    environment:
      - SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL}
    networks:
      - monitoring
    depends_on:
      - alertmanager

volumes:
  prometheus-data:

networks:
  monitoring:
    driver: bridge
```

## 🧪 Testing

### Test an alert manually

```bash
./scripts/test-alert.sh
```

### Verify Prometheus configuration

```bash
docker exec prometheus promtool check config /etc/prometheus/prometheus.yml
```

### Test an Ansible playbook

```bash
ansible-playbook ansible/playbooks/high-cpu-remediation.yml --check
```

## 📊 Monitoring and Dashboards

Access the interfaces:

- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093
- **Flask Webhook**: http://localhost:5000/health

## 🔐 Security

- Use SSH keys with passphrase
- Store secrets in a vault (Ansible Vault, HashiCorp Vault)
- Limit network access with firewall rules
- Use HTTPS for webhooks in production
- Regularly audit access logs

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md)

1. Fork the project
2. Create a branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## 👥 Authors

- **Rania Brahmi** - *Initial work*


---

⭐ If this project helps you, don't forget to give it a star on GitHub!
