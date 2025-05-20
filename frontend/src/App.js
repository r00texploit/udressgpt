import React, { useState } from 'react';
import {
  Container,
  Paper,
  Typography,
  TextField,
  Button,
  Box,
  FormControlLabel,
  Switch,
  CircularProgress,
  Alert,
  Snackbar,
  Grid,
} from '@mui/material';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

function App() {
  const [formData, setFormData] = useState({
    idea: '',
    investment: 3.0,
    n_round: 5,
    code_review: true,
    run_tests: false,
    implement: true,
    project_name: '',
    inc: false,
    project_path: '',
    reqa_file: '',
    max_auto_summarize_code: 0,
    ui_framework: 'react',
    enable_ui_review: true,
  });

  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const result = await axios.post(`${API_URL}/project`, formData);
      setResponse(result.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred while generating the project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          MetaGPT Project Generator
        </Typography>
        
        <form onSubmit={handleSubmit}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                required
                label="Project Idea"
                name="idea"
                value={formData.idea}
                onChange={handleInputChange}
                placeholder="Enter your project idea (e.g., 'Create a 2048 game')"
                multiline
                rows={2}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Project Name"
                name="project_name"
                value={formData.project_name}
                onChange={handleInputChange}
                placeholder="e.g., game_2048"
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Investment Amount"
                name="investment"
                value={formData.investment}
                onChange={handleInputChange}
                inputProps={{ min: 0, step: 0.1 }}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Number of Rounds"
                name="n_round"
                value={formData.n_round}
                onChange={handleInputChange}
                inputProps={{ min: 1 }}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="UI Framework"
                name="ui_framework"
                value={formData.ui_framework}
                onChange={handleInputChange}
                select
                SelectProps={{ native: true }}
              >
                <option value="react">React</option>
                <option value="vue">Vue</option>
                <option value="angular">Angular</option>
                <option value="flutter">Flutter</option>
              </TextField>
            </Grid>

            <Grid item xs={12}>
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.code_review}
                      onChange={handleInputChange}
                      name="code_review"
                    />
                  }
                  label="Enable Code Review"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.run_tests}
                      onChange={handleInputChange}
                      name="run_tests"
                    />
                  }
                  label="Run Tests"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.implement}
                      onChange={handleInputChange}
                      name="implement"
                    />
                  }
                  label="Implement Code"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.enable_ui_review}
                      onChange={handleInputChange}
                      name="enable_ui_review"
                    />
                  }
                  label="Enable UI Review"
                />
              </Box>
            </Grid>

            <Grid item xs={12}>
              <Button
                type="submit"
                variant="contained"
                color="primary"
                size="large"
                disabled={loading}
                sx={{ minWidth: 200 }}
              >
                {loading ? <CircularProgress size={24} /> : 'Generate Project'}
              </Button>
            </Grid>
          </Grid>
        </form>

        {error && (
          <Snackbar open={!!error} autoHideDuration={6000} onClose={() => setError(null)}>
            <Alert severity="error" onClose={() => setError(null)}>
              {error}
            </Alert>
          </Snackbar>
        )}

        {response && (
          <Box sx={{ mt: 4 }}>
            <Alert severity="success">
              Project generated successfully!
            </Alert>
            <Typography variant="body1" sx={{ mt: 2 }}>
              Project Path: {response.project_path}
            </Typography>
          </Box>
        )}
      </Paper>
    </Container>
  );
}

export default App; 