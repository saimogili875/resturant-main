/**
 * Order Tracker — live updates + chat over the order WebSocket room.
 *
 * Connects to ws/orders/<orderId>/ and updates #order-status-display
 * and appends chat bubbles to #message-thread.
 *
 * CSP-safe: loaded as an external file via {% static %} + defer, using
 * standard DOM event listeners (no eval or inline handlers).
 */
(function() {
  function initOrderTracker() {
    var container = document.getElementById("order-tracker-container");
    if (!container) return;

    var orderId = container.getAttribute("data-order-id");
    var status = container.getAttribute("data-initial-status");
    var labelsEl = document.getElementById("status-labels");
    var labels = labelsEl ? JSON.parse(labelsEl.textContent) : {};

    var statusDisplay = document.getElementById("order-status-display");
    var offlineWarning = document.getElementById("offline-warning");

    function updateStatusDisplay(newStatus) {
      status = newStatus;
      if (statusDisplay) {
        statusDisplay.textContent = labels[status] || status;
      }
    }

    function setConnected(isConnected) {
      if (offlineWarning) {
        offlineWarning.style.display = isConnected ? "none" : "block";
      }
    }

    // Set initial state
    setConnected(false);

    var chatForm = document.getElementById("chat-form");
    if (chatForm) {
      chatForm.addEventListener("htmx:afterRequest", function(event) {
        if (event.detail.successful) {
          chatForm.reset();
        }
      });
    }

    var scheme = window.location.protocol === "https:" ? "wss" : "ws";
    var url = scheme + "://" + window.location.host + "/ws/orders/" + orderId + "/";
    var socket;

    try {
      socket = new WebSocket(url);
    } catch (err) {
      return; // Socket unavailable; server-rendered status stands.
    }

    socket.onopen = function() {
      setConnected(true);
    };

    socket.onclose = function() {
      setConnected(false);
    };

    socket.onmessage = function(event) {
      var data = JSON.parse(event.data);
      if (data.type === "order.status" && data.status) {
        updateStatusDisplay(data.status);
      } else if (data.type === "order.message") {
        appendMessage(data);
      }
    };

    function appendMessage(data) {
      var thread = document.getElementById("message-thread");
      if (!thread || document.getElementById("msg-" + data.message_id)) return;
      var li = document.createElement("li");
      li.id = "msg-" + data.message_id;
      li.className = "msg";
      li.textContent = data.body;
      thread.appendChild(li);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initOrderTracker);
  } else {
    initOrderTracker();
  }
})();
