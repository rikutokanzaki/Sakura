let logs = [];

function renderLogs(logCount) {
  const table = document.querySelector('.honeypotLogs .logTable');
  if (logs.length === 0) return;

  const allKeysSet = new Set();
  logs.forEach(log => {
    Object.keys(log).forEach(key => allKeysSet.add(key));
  });

  const preferredOrder = ['timestamp', 'src_ip', 'src_port', 'protocol', 'message', 'duration', 'username', 'password'];
  const otherKeys = [...allKeysSet].filter(key => !preferredOrder.includes(key)).sort();
  const resultKeys = [...preferredOrder, ...otherKeys];

  let headerRow = '<tr>';
  resultKeys.forEach(key => {
    headerRow += `<th>${key}</th>`;
  });
  headerRow += '</tr>';
  table.innerHTML = headerRow;

  let displayLogs;
  if (logCount === 'all') {
    displayLogs = logs;
  } else {
    const n = parseInt(logCount);
    displayLogs = logs.slice(-n);
  }

  displayLogs.forEach(log => {
    const row = document.createElement('tr');
    row.innerHTML = resultKeys.map(key => `<td>${log[key] ?? ''}</td>`).join('');
    table.appendChild(row);
  });
}

window.addEventListener('DOMContentLoaded', () => {
  fetch('api/logs/cowrie')
    .then(response => response.json())
    .then(data => {
      logs = data;

      renderLogs('10');

      const logCountSelect = document.getElementById('logCountSelect');
      logCountSelect.addEventListener('change', (e) => {
        renderLogs(e.target.value);
      });
    })
    .catch(error => {
      console.error('Failed to load logs:', error);
    });

  const launchButton = document.querySelector('.launchButton');
  const honeypotSelect = document.getElementById('honeypotSelect');

  launchButton.addEventListener('click', () => {
    const selectedHoneypot = honeypotSelect.value;

    fetch(`/trigger/${selectedHoneypot}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ honeypot: selectedHoneypot })
    })
    .then(response => {
      if (!response.ok) {
        throw new Error('Failed to launch honeypot');
      }
      return response.text();
    })
    .then(data => {
      console.log('Succeed to launch honeypot:', data);
      alert(`Request to launch ${selectedHoneypot} has been sent.`);
    })
    .catch(error => {
      console.error('Launch error:', error);
      alert(`Error: ${error.message}`);
    });
  });
});