function getPreferredOrder(honeypotName) {
  if (honeypotName == 'paramiko') {
    return ['timestamp', 'src_ip', 'src_port', 'eventid', 'command', 'username', 'password'];
  } else if (honeypotName == 'heralding') {
    return ['timestamp', 'source_ip', 'source_port', 'request_uri'];
  } else if (honeypotName == 'wordpot') {
    return ['timestamp','src_ip', 'src_port', 'username', 'password', 'url', 'dest_ip', 'dest_port', 'message'];
  } else if (honeypotName === 'h0neytr4p') {
    return ['timestamp', 'header_x-real-ip', 'header_x-forwarded-for', 'src_ip', 'request_method', 'request_uri'];
  } else if (honeypotName === 'snare') {
    return ['timestamp', 'headers.x-real-ip', "headers.x-forwarded-for", 'peer.ip', 'peer.port', 'method', 'path', 'status', 'uuid'];
  } else if (honeypotName === 'cowrie') {
    return ['timestamp', 'src_ip', 'src_port', 'protocol', 'message', 'duration', 'username', 'password'];
  } else {
    return [];
  }
}

function renderLogs(honeypotName, logs, logCount, tableId) {
  const table = document.getElementById(tableId);
  if (!logs || logs.length === 0) {
    table.innerHTML = "<tr><td>No logs found</td></tr>";
    return;
  }

  const allKeysSet = new Set();
  logs.forEach(log => {
    Object.keys(log).forEach(key => allKeysSet.add(key));
  });

  const preferredOrder = getPreferredOrder(honeypotName);
  const otherKeys = [...allKeysSet].filter(key => !preferredOrder.includes(key)).sort();
  const resultKeys = [...preferredOrder, ...otherKeys];

  let headerRow = '<tr>';
  resultKeys.forEach(key => {
    headerRow += `<th>${key}</th>`;
  });
  headerRow += '</tr>';
  table.innerHTML = headerRow;

  const displayLogs = logs.slice(-parseInt(logCount));

  displayLogs.forEach(log => {
    const row = document.createElement('tr');
    row.innerHTML = resultKeys.map(key => `<td>${log[key] ?? ''}</td>`).join('');
    table.appendChild(row);
  });
}

function loadAndRenderLogs(honeypotName, tableId, selectId) {
  fetch(`/api/logs/${honeypotName}`)
    .then(response =>{
      if (response.status === 404) {
        const logCount = document.getElementById(selectId).value;
        renderLogs(honeypotName, [], logCount, tableId)
        return null
      }
      return response.json()
    })
    .then(logs => {
      if (!logs) return;
      const logCount = document.getElementById(selectId).value;
      renderLogs(honeypotName, logs, logCount, tableId);

      document.getElementById(selectId).addEventListener('change', (e) => {
        renderLogs(honeypotName, logs, e.target.value, tableId);
      });
    })
    .catch(error => {
      console.error(`Failed to load ${honeypotName} logs:`, error);
      const table = document.getElementById(tableId);
      table.innerHTML = `<tr><td colspan="99">Error loading ${honeypotName} logs.</td></tr>`;
    });
}

window.addEventListener('DOMContentLoaded', () => {
  loadAndRenderLogs('paramiko', 'paramikoTable', 'logCountSelectParamiko');
  loadAndRenderLogs('heralding', 'heraldingTable', 'logCountSelectHeralding');
  loadAndRenderLogs('wordpot', 'wordpotTable', 'logCountSelectWordpot');
  loadAndRenderLogs('h0neytr4p', 'h0neytr4pTable', 'logCountSelectH0neytr4p');
  loadAndRenderLogs('snare', 'snareTable', 'logCountSelectSnare');
  loadAndRenderLogs('cowrie', 'cowrieTable', 'logCountSelectCowrie');

  const launchButton = document.querySelector('.launchButton');
  const honeypotSelect = document.getElementById('honeypotSelect');

  launchButton.addEventListener('click', () => {
    const selectedHoneypot = honeypotSelect.value;

    fetch(`/trigger/${selectedHoneypot}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ honeypotName: selectedHoneypot })
    })
    .then(response => {
      if (!response.ok) throw new Error(`Failed to launch ${selectedHoneypot}`);
      return response.text();
    })
    .then(data => {
      console.log(`Succeed to launch ${selectedHoneypot}:`, data);
      alert(`Request to launch ${selectedHoneypot} has been sent.`);
    })
    .catch(error => {
      console.error('Launch error:', error);
      alert(`Error: ${error.message}`);
    });
  });
});
