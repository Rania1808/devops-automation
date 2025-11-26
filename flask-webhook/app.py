from flask import Flask, request, jsonify
import subprocess
import requests
import os
import json
import logging
from datetime import datetime

app = Flask(__name__)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
ANSIBLE_PLAYBOOK_PATH = '/ansible/playbooks'

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/webhook/alert', methods=['POST'])
def receive_alert():
    try:
        data = request.json
        logger.info(f"Received alert: {json.dumps(data, indent=2)}")
        
        # Traiter chaque alerte
        for alert in data.get('alerts', []):
            logger.info(f"Processing alert: {alert['labels'].get('alertname')}")
            
            if alert['status'] == 'firing':
                handle_firing_alert(alert)
            elif alert['status'] == 'resolved':
                handle_resolved_alert(alert)
        
        return jsonify({'status': 'success'}), 200
    
    except Exception as e:
        logger.error(f"Error processing alert: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def handle_firing_alert(alert):
    alert_name = alert['labels'].get('alertname')
    instance = alert['labels'].get('instance')
    severity = alert['labels'].get('severity', 'unknown')
    
    # Déterminer l'emoji selon la sévérité
    emoji = '🚨' if severity == 'critical' else '⚠️'
    
    # Envoyer notification Slack
    message = f"{emoji} *ALERT FIRING: {alert_name}*\n"
    message += f"Instance: `{instance}`\n"
    message += f"Severity: `{severity}`\n"
    message += f"Description: {alert['annotations'].get('description', 'N/A')}\n"
    message += f"Time: {alert.get('startsAt', 'N/A')}"
    
    send_slack_notification(alert_name, message, severity)
    
    # Déclencher Ansible selon le type d'alerte
    playbook_mapping = {
        'HighCPUUsage': 'high-cpu-remediation.yml',
        'HighMemoryUsage': 'memory-cleanup.yml',
        'DiskSpaceLow': 'disk-cleanup.yml'
    }
    
    playbook = playbook_mapping.get(alert_name)
    if playbook:
        logger.info(f"Triggering Ansible playbook: {playbook}")
        run_ansible_playbook(playbook, instance, alert_name)
    else:
        logger.warning(f"No playbook defined for alert: {alert_name}")

def handle_resolved_alert(alert):
    alert_name = alert['labels'].get('alertname')
    instance = alert['labels'].get('instance')
    
    message = f"✅ *ALERT RESOLVED: {alert_name}*\n"
    message += f"Instance: `{instance}`\n"
    message += f"Duration: {alert.get('endsAt', 'N/A')}"
    
    send_slack_notification(alert_name, message, 'info')

def run_ansible_playbook(playbook, target, alert_name):
    # Extraire l'IP du target (format: ip:port)
    target_ip = target.split(':')[0]
    
    cmd = [
        'ansible-playbook',
        f'{ANSIBLE_PLAYBOOK_PATH}/{playbook}',
        '-i', f'{target_ip},',
        '-e', f'alert_name={alert_name}',
        '-v'
    ]
    
    try:
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=300
        )
        
        success = result.returncode == 0
        status_emoji = '✅' if success else '❌'
        
        message = f"{status_emoji} *Ansible Remediation*\n"
        message += f"Playbook: `{playbook}`\n"
        message += f"Target: `{target_ip}`\n"
        message += f"Status: `{'Success' if success else 'Failed'}`\n"
        
        if not success:
            message += f"Error: ```{result.stderr[:500]}```"
        
        send_slack_notification("Ansible Execution", message, 'info')
        
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout running playbook {playbook}")
        send_slack_notification(
            "Ansible Timeout",
            f"❌ Playbook `{playbook}` timed out after 5 minutes",
            'error'
        )
    except Exception as e:
        logger.error(f"Error running playbook: {str(e)}")
        send_slack_notification(
            "Ansible Error",
            f"❌ Failed to run `{playbook}`: {str(e)}",
            'error'
        )

def send_slack_notification(title, message, severity='info'):
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL not configured")
        return
    
    color_mapping = {
        'critical': '#FF0000',
        'warning': '#FFA500',
        'info': '#36A64F',
        'error': '#FF0000'
    }
    
    payload = {
        'username': 'DevOps Automation Bot',
        'icon_emoji': ':robot_face:',
        'attachments': [{
            'color': color_mapping.get(severity, '#808080'),
            'title': title,
            'text': message,
            'footer': 'DevOps Automation',
            'footer_icon': 'https://platform.slack-edge.com/img/default_application_icon.png',
            'ts': int(datetime.now().timestamp())
        }]
    }
    
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Slack notification sent successfully")
    except Exception as e:
        logger.error(f"Failed to send Slack notification: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
