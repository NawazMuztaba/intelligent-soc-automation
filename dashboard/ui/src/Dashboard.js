import React, { useEffect, useState } from "react";
import axios from "axios";
import "./App.css";

function Dashboard() {
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    const timer = setInterval(fetchAlerts, 2000);
    fetchAlerts();
    return () => clearInterval(timer);
  }, []);

  const fetchAlerts = async () => {
    try {
      const response = await axios.get("http://localhost:5000/api/alerts");
      setAlerts(response.data.reverse());
    } catch (error) {
      console.error("Error fetching alerts:", error);
    }
  };

  const getIcon = (type) => {
    switch (type) {
      case "bruteforce.alert":
        return "🔐";
      case "ssh_bruteforce":
        return "🔓";
      case "portscan.alert":
        return "📡";
      case "web.attack.alert":
        return "🌐";
      default:
        return "⚠️";
    }
  };

  const severityBadge = (severity) => {
    if (severity === "high") return <span className="badge high">HIGH</span>;
    if (severity === "medium") return <span className="badge medium">MEDIUM</span>;
    return <span className="badge low">LOW</span>;
  };

  return (
    <div className="container">
      <h1>Security Alerts Dashboard</h1>

      <div className="alert-container">
        {alerts.map((alert, index) => (
          <div key={index} className="alert-card">
            
            <div className="alert-header">
              <span className="alert-icon">{getIcon(alert.type)}</span>
              <span className="alert-title">{alert.type}</span>
              {severityBadge(alert.severity)}
            </div>

            <div className="alert-content">
              <p><b>IP:</b> {alert.ip || alert.payload?.attacker_ip}</p>
              <p><b>Severity:</b> {alert.severity}</p>
              <p className="timestamp"><b>Time:</b> {alert.timestamp}</p>
            </div>

          </div>
        ))}
      </div>
    </div>
  );
}

export default Dashboard;
