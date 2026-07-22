(function() {
  const dataElement = document.getElementById('table-data');
  if (!dataElement) return;
  const data = JSON.parse(dataElement.textContent);
  
  const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
  const wsUrl = `${wsScheme}://${window.location.host}/ws/tables/${data.qrToken}/`;
  const socket = new WebSocket(wsUrl);

  socket.onmessage = function(event) {
    const msgData = JSON.parse(event.data);
    if (msgData.type === "order.status" || msgData.type === "table.paid") {
      window.location.reload();
    }
  };

  socket.onclose = function() {
    console.log("Realtime connection closed.");
  };
})();
