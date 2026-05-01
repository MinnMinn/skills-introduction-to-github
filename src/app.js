const express = require('express');

const app = express();

app.use(express.json());

/**
 * GET /health
 * Returns a simple status check response.
 */
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok' });
});

module.exports = app;
