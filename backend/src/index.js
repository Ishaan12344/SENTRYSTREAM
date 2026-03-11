// Entry point for the backend
const express = require('express');
const app = express();
const PORT = process.env.PORT || 5000;

app.use(express.json());

// Example route
app.get('/api', (req, res) => {
    res.send('Hello from SentryStream API!');
});

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});